# gen_uitjes.py - Uitjes Agenda builder
# Gebruik: python gen_uitjes.py
# Output: uitjes_agenda.html (naast dit script)
import os, sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EVENTS_JSON = os.path.join(SCRIPT_DIR, 'events_categorized.json')
HTML_OUT = os.path.join(SCRIPT_DIR, 'index.html')

import json, re as _re, math, unicodedata, itertools

def fold_diacritics(s: str) -> str:
    """Haalt accenten/diakrieten weg (bv. 'ü'->'u') voor zoek-matching --
    zonder deze fold vond een zoekopdracht 'zummerbuhne' geen 'Zummerbühne'.
    Zie decisions.md 2026-08-18 (Claude Design-review, 4e ronde)."""
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
from datetime import date
TODAY = date.today().isoformat()
from collections import defaultdict

with open(EVENTS_JSON, encoding="utf-8") as f:
    events = json.load(f)

CITY_COORDS_PATH = os.path.join(SCRIPT_DIR, 'city_coords.json')
try:
    with open(CITY_COORDS_PATH, encoding='utf-8') as f:
        CITY_COORDS = json.load(f)
except FileNotFoundError:
    CITY_COORDS = {}

SRC = {
    'spotgroningen.nl':    ('Spot',            '🔴', '#e53935'),
    'lawei':               ('De Lawei',        '🎶', '#6d4c41'),
    'atlastheater':        ('Atlas Emmen',     '🟡', '#f57f17'),
    'drenthe.nl':          ('Drenthe',         '🟢', '#2e7d32'),
    'visitgroningen':      ('Visitgroningen',  '🟣', '#6a1b9a'),
    'friesland.nl':        ('Friesland',       '🔵', '#0277bd'),
    'kielzog':             ('Kielzog',         '🎵', '#0277bd'),
    'forum.nl':            ('Forum',           '🟠', '#e65100'),
    'denieuwekolk.nl':     ('Nieuwe Kolk',     '🩵', '#00838f'),
    'vanberesteyn':        ('Van Beresteyn',   '🏛️', '#4527a0'),
    'vera':                ('Vera',            '🔊', '#d81b60'),
    'simplon':             ('Simplon',         '🎹', '#7b1fa2'),
    'martiniplaza':        ('Martiniplaza',    '🏟️', '#558b2f'),
    'grandtheatregroningen':('Grand Theatre',  '🎭', '#37474f'),
    'theaterroden':        ('Winsinghhof',     '🌿', '#ad1457'),
    'em2groningen':        ('EM2',             '🎸', '#00695c'),
    'zummerbuhne':         ('Zummerbühne',     '🌾', '#827717'),
    'usva':                ('USVA',            '🎓', '#455a64'),
    'geertteis':           ('Geert Teis',      '🏡', '#5d4037'),
    'podiumnienoordleek':  ('Nienoord',        '🌳', '#33691e'),
    'grandcafe_zuidlaren': ('GC Zuidlaren',    '☕', '#795548'),
    'gekehoogstins.nl':    ('Geke Hoogstins',  '🌺', '#1b5e20'),
    'machinefabriek':      ('Machinefabriek',  '🏭', '#263238'),
    'be-wonder.com':       ('Be-Wonder',       '✨', '#ad1457'),
    'dorpshuisannen':      ('Dorpshuis Annen', '🏘️', '#6d4c41'),
    'denoorderbron.nl':    ('Noorderbron',     '🌲', '#00796b'),
    'detamboer':           ('De Tamboer',      '🥁', '#795548'),
    'posthuistheater':     ('Posthuis',        '🎭', '#4a148c'),
    'ontdekpoort':         ('OntdekPoort',     '🌉', '#1565c0'),
    'bostheater':          ('Bostheater',      '🌲', '#2e7d32'),
    'neushoorn':           ('Neushoorn',       '🦏', '#1a237e'),
    'groningermuseum':     ('Groninger Museum','🖼️', '#b71c1c'),
    'drentsmuseum':        ('Drents Museum',   '🏺', '#4e342e'),
    'podiumzuidhaege':     ('Zuidhaege Assen', '🎻', '#01579b'),
    'hunebedcentrum':      ('Hunebedcentrum',  '🪨', '#5d4037'),
    'koornbeurs':          ('Koornbeurs',      '🎪', '#880e4f'),
    'kunstpuntgroningen':  ('Kunstpunt',       '🎨', '#6a1b9a'),
    'uitzinnig':           ('Uitzinnig',       '🖌️', '#00695c'),
    # Landelijke podia
    'tivolivredenburg':    ('TivoliVredenburg','🎼', '#6a1b9a'),
    'melkweg':             ('Melkweg',         '🌌', '#283593'),
    'paradiso':            ('Paradiso',        '🔔', '#b71c1c'),
    '013':                 ('013 Tilburg',     '🎸', '#e65100'),
    'ziggodome':           ('Ziggo Dome',      '🏟️', '#00695c'),
    'effenaar':            ('Effenaar',        '⚡', '#f9a825'),
    'doornroosje':         ('Doornroosje',     '🌹', '#880e4f'),
    'ahoy':                ('Rotterdam Ahoy',  '⚓', '#1565c0'),
    'paard':               ('Het Paard',        '🐴', '#c62828'),
    'hedon':               ('Hedon Zwolle',     '🎵', '#6a1b9a'),
    'afaslive':            ('AFAS Live',        '🏛️', '#0d47a1'),
    'rotown':              ('Rotown',           '🎸', '#bf360c'),
    'dedoelen':            ('De Doelen',        '🎻', '#1b5e20'),
    'gelredome':           ('GelreDome',        '🏟️', '#f57f17'),
    'concertgebouw':       ('Concertgebouw',    '🎼', '#880e4f'),
    # Sport clubs (Noord-Nederland)
    'fcgroningen':         ('FC Groningen',     '⚽', '#00a651'),
    'fcemmen':             ('FC Emmen',         '⚽', '#003087'),
    'heerenveen':          ('SC Heerenveen',    '⚽', '#0052a5'),
    'cambuur':             ('SC Cambuur',       '⚽', '#ffd700'),
    'fctwente':            ('FC Twente',        '⚽', '#cc0000'),
    'goahead':             ('Go Ahead Eagles',  '⚽', '#f5a623'),
    'peczwolle':           ('PEC Zwolle',       '⚽', '#0033a0'),
    'donar':               ('Donar',            '🏀', '#e2001a'),
    'landstede':           ('Landstede Hammers','🏀', '#ff6b00'),
    'lycurgus':            ('Lycurgus',         '🏐', '#ffcc00'),
    'sudosa':              ('CRAFT Sudosa',     '🏐', '#2e7d32'),
    'friso':               ('Friso Sneek',      '🏐', '#d32f2f'),
    'grizzlys':            ('GIJS Groningen',   '🏒', '#6699cc'),
    'flyers':              ('Flyers Heerenveen','🏒', '#003087'),
    'ogcapitals':          ('OG Capitals',      '🏒', '#e65100'),
    'hurryup':             ('Hurry-Up',         '🤾', '#ff6600'),
    'eoemmen':             ("E&O Emmen",        '🤾', '#c62828'),
    'ldodk':               ('LDODK',            '🎯', '#f57c00'),
    'dos46':               ("DOS '46",          '🎯', '#1565c0'),
}

VENUE_LOC = {
    'spotgroningen.nl':     (53.2148, 6.5679, 'Groningen'),
    'vera':                 (53.2183, 6.5574, 'Groningen'),
    'simplon':              (53.2207, 6.5598, 'Groningen'),
    'em2groningen':         (53.2147, 6.5640, 'Groningen'),
    'forum.nl':             (53.2171, 6.5629, 'Groningen'),
    'grandtheatregroningen':(53.2190, 6.5656, 'Groningen'),
    'martiniplaza':         (53.2218, 6.5792, 'Groningen'),
    'usva':                 (53.2161, 6.5698, 'Groningen'),
    'machinefabriek':       (53.2165, 6.5532, 'Groningen'),
    'groningermuseum':      (53.2143, 6.5582, 'Groningen'),
    'vanberesteyn':         (53.1082, 6.8660, 'Groningen'),
    'geertteis':            (52.9843, 6.9491, 'Groningen'),
    'podiumnienoordleek':   (53.1617, 6.3829, 'Groningen'),
    'grandcafe_zuidlaren':  (53.0140, 6.6849, 'Groningen'),
    'atlastheater':         (52.7789, 6.9052, 'Drenthe'),
    'drenthe.nl':           (52.9953, 6.5625, 'Drenthe'),
    'visitgroningen':       (53.2194, 6.5665, 'Groningen'),
    'friesland.nl':         (53.2012, 5.8036, 'Friesland'),
    'kielzog':              (52.7235, 6.4754, 'Drenthe'),
    'denieuwekolk.nl':      (52.9953, 6.5625, 'Drenthe'),
    'detamboer':            (52.7235, 6.4754, 'Drenthe'),
    'theaterroden':         (53.1390, 6.4344, 'Drenthe'),
    'zummerbuhne':          (53.208276, 7.041508, 'Groningen'),  # Oostwold, Oldambt (niet het andere Oostwold bij Westerkwartier — zie decisions.md 2026-08-17)
    'drentsmuseum':         (52.9963, 6.5640, 'Drenthe'),
    'podiumzuidhaege':      (52.9930, 6.5580, 'Drenthe'),
    'hunebedcentrum':       (52.9236, 6.7904, 'Drenthe'),
    'gekehoogstins.nl':     (53.0083, 6.7683, 'Drenthe'),
    'dorpshuisannen':       (53.0340, 6.7350, 'Drenthe'),
    'denoorderbron.nl':     (53.0310, 6.7460, 'Drenthe'),
    'be-wonder.com':        (52.9200, 6.7900, 'Drenthe'),
    'lawei':                (53.1108, 6.0961, 'Friesland'),
    'posthuistheater':      (52.9596, 5.9192, 'Friesland'),
    'neushoorn':            (53.2012, 5.7999, 'Friesland'),
    'ontdekpoort':          (53.0328, 5.6603, 'Friesland'),
    'koornbeurs':           (53.1858, 5.5422, 'Friesland'),
    'bostheater':           (52.5146, 6.4198, 'Overijssel'),
    # Landelijke podia
    'tivolivredenburg':    (52.0927, 5.1116, 'Utrecht'),
    'melkweg':             (52.3651, 4.8839, 'Noord-Holland'),
    'paradiso':            (52.3638, 4.8843, 'Noord-Holland'),
    '013':                 (51.5639, 5.0747, 'Noord-Brabant'),
    'ziggodome':           (52.3571, 4.9428, 'Noord-Holland'),
    'effenaar':            (51.4428, 5.4756, 'Noord-Brabant'),
    'doornroosje':         (51.8455, 5.8629, 'Gelderland'),
    'ahoy':                (51.8897, 4.4864, 'Zuid-Holland'),
    'paard':               (52.0753, 4.3024, 'Zuid-Holland'),
    'hedon':               (52.5038, 6.0975, 'Overijssel'),
    'afaslive':            (52.3571, 4.9428, 'Noord-Holland'),
    'rotown':              (51.9197, 4.4786, 'Zuid-Holland'),
    'dedoelen':            (51.9197, 4.4786, 'Zuid-Holland'),
    'gelredome':           (51.9819, 5.8987, 'Gelderland'),
    'concertgebouw':       (52.3564, 4.8797, 'Noord-Holland'),
    'fcgroningen':         (53.2027, 6.5678, 'Groningen'),
    'fcemmen':             (52.7693, 6.8891, 'Drenthe'),
    'heerenveen':          (52.9556, 5.9167, 'Friesland'),
    'cambuur':             (53.2013, 5.8099, 'Friesland'),
    'fctwente':            (52.2356, 6.8575, 'Overijssel'),
    'goahead':             (52.2541, 6.1695, 'Overijssel'),
    'peczwolle':           (52.4854, 6.0746, 'Overijssel'),
    'donar':               (53.2265, 6.5683, 'Groningen'),
    'landstede':           (52.5024, 6.0968, 'Overijssel'),
    'lycurgus':            (53.2265, 6.5300, 'Groningen'),
    'sudosa':              (52.9875, 6.5575, 'Drenthe'),
    'friso':               (53.0350, 5.6600, 'Friesland'),
    'grizzlys':            (53.2265, 6.5300, 'Groningen'),
    'flyers':              (52.9506, 5.9233, 'Friesland'),
    'ogcapitals':          (53.2012, 5.7999, 'Friesland'),
    'hurryup':             (52.7800, 6.8900, 'Drenthe'),
    'eoemmen':             (52.7850, 6.8950, 'Drenthe'),
    'ldodk':               (52.9983, 6.0767, 'Friesland'),
    'dos46':               (52.7483, 6.2667, 'Drenthe'),
}

MUSIC_VENUES  = {'vera','simplon','em2groningen','spotgroningen.nl','grandcafe_zuidlaren',
                 'kielzog','machinefabriek','usva','detamboer','neushoorn',
                 'tivolivredenburg','melkweg','paradiso','013','ziggodome','effenaar','doornroosje','ahoy','paard','hedon',
                 'afaslive','rotown','dedoelen','gelredome','concertgebouw'}
SPORT_CLUBS = {
    'voetbal':    ['fcgroningen', 'fcemmen', 'heerenveen', 'cambuur', 'fctwente', 'goahead', 'peczwolle'],
    'basketbal':  ['donar', 'landstede'],
    'volleybal':  ['lycurgus', 'sudosa', 'friso'],
    'ijshockey':  ['grizzlys', 'flyers', 'ogcapitals'],
    'handbal':    ['hurryup', 'eoemmen'],
    'korfbal':    ['ldodk', 'dos46'],
}
SPORT_SRCS = {s for clubs in SPORT_CLUBS.values() for s in clubs}

SPORT_ICONS = {
    'voetbal': '⚽', 'basketbal': '🏀', 'volleybal': '🏐',
    'ijshockey': '🏒', 'handbal': '🤾', 'korfbal': '🧺',
}
SPORT_LABELS = {
    'voetbal': 'Voetbal', 'basketbal': 'Basketbal', 'volleybal': 'Volleybal',
    'ijshockey': 'IJshockey', 'handbal': 'Handbal', 'korfbal': 'Korfbal',
}

GENRE_ICONS = {'festival':'🎉','theater':'🎭','cabaret':'🎪','musical':'🎼','klassiek':'🎻','pop':'🎸',
               'jazz':'🎷','dans':'💃','expo':'🖼️','actief':'🥾','kinderen':'🎈','overig':'•'}
GENRE_LABELS = {'festival':'Festival / Evenement','theater':'Theater / Toneel','cabaret':'Cabaret / Comedy','musical':'Musical',
                'klassiek':'Klassiek / Opera','pop':'Pop / Rock','jazz':'Jazz / Blues',
                'dans':'Dans / Ballet','expo':'Expo / Kunst','actief':'Actief / Natuur',
                'kinderen':'Kinderen / Familie','overig':'Overig'}

THEATER_VENUES= {'lawei','atlastheater','denieuwekolk.nl','vanberesteyn','theaterroden','geertteis',
                 'grandtheatregroningen','martiniplaza','dorpshuisannen','podiumnienoordleek',
                 'zummerbuhne','posthuistheater','ontdekpoort','koornbeurs'}
EXPO_VENUES   = {'groningermuseum','drentsmuseum','hunebedcentrum','gekehoogstins.nl'}

_kinderen_pat = _re.compile(
    r'kinderen|kindershow|kindertheat|kindervoor|kinderdag|'
    r'familie|familieshow|familievoor|voor kinderen|voor de kids|'
    r'peuter|kleuter|baby|basisschool|juf roos|juf braaksel|woezel|'
    r'mees kees|vos & haas|\(\d\+\)', _re.I)

def classify(title, cats, source=''):
    t = title.lower()
    if _kinderen_pat.search(t): return 'kinderen'
    cat_map = {'toneel':'theater','theater':'theater','cabaret':'cabaret','musical':'musical',
               'klassiek':'klassiek','opera':'klassiek','dans':'dans','ballet':'dans',
               'familie':'kinderen','kinderen':'kinderen','jazz':'jazz','pop':'pop'}
    for c in cats:
        # cats=='expositie' is een genre-SIGNAAL van de bron zelf en dus
        # betrouwbaarder dan titel-keywords (zie de les bij SPOT/data-subgenres
        # hierboven) — vroeger stond hier ook nog een verplichte extra titel-
        # keyword-check, maar die maakte het signaal juist onbetrouwbaar (bv.
        # Engelse titels als "Coach house"/"SACRED EARTH" matchten geen enkel
        # Nederlands keyword en vielen alsnog terug op 'overig'). Bleek dood
        # spoor toch: vóór scrape_kunstpuntgroningen.py (2026-08-17) zette geen
        # enkele scraper 'expositie' in cats, dus geen bestaande bron kon
        # hierdoor geraakt worden. Zie decisions.md 2026-08-17.
        if c == 'expositie':
            return 'expo'
        elif c in cat_map:
            return cat_map[c]
    if source in EXPO_VENUES: return 'expo'
    if 'musical' in t: return 'musical'
    if any(w in t for w in ['cabaret','comedy','stand-up','humor']): return 'cabaret'
    if any(w in t for w in ['ballet','dans ','choreograf','dansavond']): return 'dans'
    # jazz eerst: 'quartet'/'trio'/'ensemble' zijn genre-ambigu en horen niet
    # exclusief bij klassiek (bv. 'Peter Bernstein Quartet' is jazz, geen klassiek)
    if any(w in t for w in ['jazz','blues','soul','swing','funk','bossa','reggae']): return 'jazz'
    if any(w in t for w in ['orkest','symfon','opera','klassiek',
                             'piano','viool','cello','strijk','filharmonisch','dirigent',
                             'recital']): return 'klassiek'
    if any(w in t for w in ['expositie','tentoonstelling','galerie','biënnale','biennale',
                             'storyworld','stripverhaal','stripmuseum','stripkunst','marilyn']): return 'expo'
    if any(w in t for w in [' theater',' toneel','toneelstuk','voorstelling']): return 'theater'
    if any(w in t for w in ['festival','feest','kermis','volksfeest','volksvermaak',
                             'sneekweek','lemsterwike','ballonfeesten','koningsdag',
                             'bevrijdingsdag','havenfeest','straatfestival',
                             'carnaval','folklorisch']): return 'festival'
    if any(w in t for w in ['rock','indie','punk','metal','concert','band','tribute',
                             'singer','songwriter','coverband','techno','house',
                             'hiphop','rap','hardrock','hardcore']): return 'pop'
    if any(w in t for w in ['wandeling','safari','natuur','strunen','stenen zoeken']): return 'actief'
    if source in MUSIC_VENUES:   return 'pop'
    if source in THEATER_VENUES: return 'theater'
    return 'overig'

NL_DAYS   = ['ma','di','wo','do','vr','za','zo']
NL_DAYS_LONG = ['Maandag','Dinsdag','Woensdag','Donderdag','Vrijdag','Zaterdag','Zondag']
NL_MONTHS = ['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec']
NL_MONTHS_LONG = ['Januari','Februari','Maart','April','Mei','Juni',
                  'Juli','Augustus','September','Oktober','November','December']

def fmt_date(iso):
    try: d=date.fromisoformat(iso); return f"{NL_DAYS[d.weekday()]} {d.day} {NL_MONTHS[d.month-1]}"
    except: return iso

def day_label(iso):
    """Volledige dag-groepskop, bv. 'Maandag 17 augustus' -- vervangt de
    herhaalde korte datum per rij (cluster 5-vervolgronde, Claude Design
    2026-08-18: 'ma 17 aug' stond tien keer onder elkaar)."""
    try:
        d = date.fromisoformat(iso)
        return f"{NL_DAYS_LONG[d.weekday()]} {d.day} {NL_MONTHS_LONG[d.month-1].lower()}"
    except Exception:
        return iso
def fmt_date_range(start_iso, end_iso):
    """Compacte weergave voor meerdaagse niet-expo events, bv. 'vr 21 t/m zo 23 aug'
    (zelfde d_start/d_end-veld als expo_card_html, maar kort formaat i.p.v. de
    lange 'vanaf ... t/m ...'-stijl — past bij de kleinere event-date regel)."""
    try:
        ds = date.fromisoformat(start_iso); de = date.fromisoformat(end_iso)
    except (ValueError, TypeError):
        return fmt_date(start_iso)
    if ds.year == de.year and ds.month == de.month:
        return f"{NL_DAYS[ds.weekday()]} {ds.day} t/m {NL_DAYS[de.weekday()]} {de.day} {NL_MONTHS[de.month-1]}"
    return f"{fmt_date(start_iso)} t/m {fmt_date(end_iso)}"
def month_id(iso):    return 'm'+iso[:7].replace('-','')
def month_label(iso):
    try: y,m=int(iso[:4]),int(iso[5:7]); return f"{NL_MONTHS_LONG[m-1]} {y}"
    except: return iso[:7]
def month_short(iso):
    try: y,m=int(iso[:4]),int(iso[5:7]); return f"{NL_MONTHS[m-1].capitalize()} '{str(y)[2:]}"
    except: return iso[:7]
def safe_key(k): return k.replace('.','_').replace('-','_')
def esc(s):      return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def event_genre(e):
    src = e.get('source','')
    if src in SPORT_SRCS: return 'sport'
    return classify(e.get('title',''), e.get('cats',[]), src)

for e in events:
    e['_genre'] = event_genre(e)

def event_is_valid(e):
    d = e.get('date','')
    if not d or d > '2027-12-31':
        return False
    de = e.get('date_end','')
    if e['_genre'] == 'expo':
        return not (de and de < TODAY)
    # Meerdaagse niet-expo events (bv. festivals van drenthe.nl/friesland.nl/
    # visitgroningen, zie decisions.md 2026-08-17): zolang date_end nog niet
    # gepasseerd is blijft het event zichtbaar, ook als de startdag al voorbij
    # is — anders verdwijnt bv. een 3-daags festival na dag 1 uit de agenda.
    # Anders dan bij expo: zonder date_end blijft de oude regel gelden
    # (verdwijnen zodra de enige/startdatum voorbij is), niet "altijd geldig".
    if de and de >= TODAY:
        return True
    return d >= TODAY

events_valid = sorted([e for e in events if e['_genre']!='expo' and event_is_valid(e)],
                      key=lambda e: e.get('date',''))
expo_valid = sorted([e for e in events if e['_genre']=='expo' and event_is_valid(e)],
                    key=lambda e: e.get('date',''))
total = len(events_valid)
expo_total = len(expo_valid)
# Aparte uitjes/sport-totalen (naast de gecombineerde 'total') zodat de
# statusregel per modus het juiste aantal kan tonen i.p.v. altijd tegen de
# gecombineerde TOTAL te vergelijken -- gemeld door Claude Design 2026-08-18:
# "Toont X van Y" klopte in Uitjes-modus nooit met "Toont alle", omdat Y ook
# sport+expo meetelde.
total_uitjes = sum(1 for e in events_valid if e.get('source') not in SPORT_SRCS)
total_sport = sum(1 for e in events_valid if e.get('source') in SPORT_SRCS)
by_month = defaultdict(list)
for e in events_valid: by_month[e['date'][:7]].append(e)
months_sorted = sorted(by_month.keys())

css_vars = '\n'.join(f'  --{safe_key(k)}:{v[2]};' for k,v in SRC.items())

def _contrast_text(hex_color):
    """Zwart of wit tekst o.b.v. helderheid van de achtergrondkleur — voorkomt
    onleesbare combinaties zoals witte tekst op geel (bv. cambuur #ffd700,
    lycurgus #ffcc00). Gevonden door Claude Design-review 2026-08-17, zie
    decisions.md: src_css() zette altijd wit, ongeacht achtergrondkleur —
    club_css() had toevallig al een (hardcoded, niet-generieke) uitzondering."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return '#212121' if (0.299*r + 0.587*g + 0.114*b) > 150 else '#fff'

def src_css(key):
    # Kleurstrategie omgegooid (Claude Design-review 2026-08-17, cluster 5):
    # kleur = identiteit EN actieve-staat tegelijk gaf geen visuele rust bij
    # 70 gekleurde chips + 2 gekleurde badges per kaart. Nu: bronchips zijn
    # neutraal (gedeelde .btn-stijl + 1 generieke actief-kleur, zie CSS),
    # broncode-kleur overleeft alleen nog als de 3px kaart-linkerrand -- de
    # enige plek waar per-bron-kleur nog functioneel nut heeft (snel scannen
    # welke kaart bij welke bron hoort in een lange lijst). Was voorheen ook
    # chip-border/tekst + een gekleurde badge-pill (.s-{sk}, nu verwijderd --
    # badge-src is nu platte grijze tekst, zie CSS).
    sk=safe_key(key); c=SRC.get(key,('','','#999'))[2]
    return f'.event.{sk}{{border-left-color:{c};}}'

src_css_all = '\n'.join(src_css(k) for k in SRC)
active_sources = sorted(set(e['source'] for e in events_valid))

LANDELIJK = {'tivolivredenburg','melkweg','paradiso','013','ziggodome','effenaar','doornroosje','ahoy'}

# Bron-popover toont bronnen gegroepeerd per provincie (Claude Design-review
# 2026-08-17, cluster 5: "groepering nodig, je Landelijk-knop bewijst dat")
# i.p.v. één platte lijst van ~60 chips. Groep afgeleid uit VENUE_LOC — geen
# nieuwe data nodig. PROV_ORDER bepaalt de volgorde (kerngebied eerst).
PROV_ORDER = ['Landelijk','Groningen','Drenthe','Friesland','Overijssel',
              'Utrecht','Noord-Holland','Zuid-Holland','Noord-Brabant','Gelderland','Overig']

def src_group(key):
    if key in LANDELIJK: return 'Landelijk'
    loc = VENUE_LOC.get(key)
    return loc[2] if loc else 'Overig'

src_buttons = '<button class="btn active" data-src="all">Alle bronnen</button>\n'
src_buttons += '  <button class="btn" data-src-group="landelijk" style="border-color:#c62828;color:#c62828;">🗺️ Landelijk (alle 8)</button>\n'
_src_by_group = {}
for key in active_sources:
    if key in SPORT_SRCS: continue  # sport clubs apart
    _src_by_group.setdefault(src_group(key), []).append(key)
_group_order = sorted(_src_by_group.keys(), key=lambda g: PROV_ORDER.index(g) if g in PROV_ORDER else len(PROV_ORDER))
for grp in _group_order:
    label_esc = esc(grp)
    src_buttons += f'  <div class="src-group-label">{label_esc}</div>\n'
    for key in _src_by_group[grp]:
        label,emoji,_ = SRC.get(key,(key,'•','#999'))
        src_buttons += f'  <button class="btn" data-src="{key}" data-src-label="{esc(label.lower())}">{esc(label)}</button>\n'

month_nav = '\n'.join(
    f'<a href="#{month_id(m+"-01")}" class="month-link">{month_short(m+"-01")}</a>'
    for m in months_sorted)

def event_html(e):
    src = e.get('source',''); sk = safe_key(src)
    is_sport = src in SPORT_SRCS
    genre = e['_genre']
    gender = e.get('gender', '') if is_sport else ''
    if is_sport:
        sport_type = e.get('sport', '')
        icon = SPORT_ICONS.get(sport_type, '🏆')
        glabel = SPORT_LABELS.get(sport_type, 'Sport')
    else:
        icon = GENRE_ICONS.get(genre,'•'); glabel = GENRE_LABELS.get(genre,'Overig')
    title_html = (f'<a href="{esc(e.get("url",""))}" target="_blank" rel="noopener">{esc(e.get("title",""))}</a>'
                  if e.get('url') else esc(e.get('title','')))
    loc = VENUE_LOC.get(src)
    prov = loc[2] if loc else e.get('province', 'Onbekend')
    # Prioriteit: exact event-eigen lat/lon (bv. van een aggregator die per
    # venue een precieze kaart-marker aanlevert, zie scrape_kunstpuntgroningen.py
    # / decisions.md 2026-08-17 — was tot dan toe ongebruikte infrastructuur:
    # events_db.py sloeg lat/lon al op maar geen enkele scraper vulde het en
    # deze functie las het nooit) > CITY_COORDS (plaatsnaam-lookup) > VENUE_LOC
    # (bron-niveau fallback, alleen zinvol bij één vaste locatie per bron).
    if e.get('lat') and e.get('lon'):
        lat_lon = f"{e['lat']},{e['lon']}"
    else:
        city_loc = CITY_COORDS.get((e.get('city') or '').strip())
        if city_loc:
            lat_lon = f'{city_loc[0]},{city_loc[1]}'
        elif loc:
            lat_lon = f'{loc[0]},{loc[1]}'
        else:
            lat_lon = ''
    d_start = e.get('date',''); d_end = e.get('date_end','')
    is_multiday = bool(d_end) and d_end != d_start
    # Vooraf berekende, lowercased zoektekst (titel + venue/stad) als data-
    # attribuut -- voorkomt dat het zoekveld bij elke toetsaanslag 8202x
    # child-elementen moet uitlezen en .toLowerCase() aanroepen. Zie
    # decisions.md 2026-08-17 (Claude Design-review).
    search_txt = esc(fold_diacritics((e.get('title','') + ' ' + (e.get('venue','') or e.get('city','') or '')).lower()))
    # Kaart-layout herzien (Claude Design-review, 4e ronde, 2026-08-18:
    # "het grid duwt de badges ~2000px van de titel af, de datum herhaalt
    # zich nodeloos op elke rij"). Geen aparte datumkolom meer (die info zit
    # nu in de dag-groepskop, zie main_html hieronder) -- alleen bij een
    # meerdaags event nog een klein datumbereik-label bij de titel, want de
    # dag-groepskop alleen zou dan de indruk wekken dat het een eendaags
    # event is. Genre-badge verhuisd naar direct achter de titel i.p.v. een
    # eigen kolom. Bron-badge (tekst) weggehaald -- de kaart-linkerrandkleur
    # is al de bron-indicator, twee keer dezelfde info was overbodig.
    daterange_html = (f'<span class="event-daterange-inline">{fmt_date_range(d_start, d_end)}</span>'
                       if is_multiday else '')
    return (f'<div class="event {sk}" data-src="{src}" data-genre="{genre}" '
            f'data-prov="{prov}" data-latlon="{lat_lon}" data-gender="{gender}" '
            f'data-date="{esc(d_start)}" data-dateend="{esc(d_end or d_start)}" '
            f'data-search="{search_txt}">'
            f'<div class="event-main">'
            f'<div class="event-title">{title_html} '
            f'<span class="badge badge-genre g-{genre}">{icon} {glabel}</span>{daterange_html}</div>'
            f'<div class="event-venue">{esc(e.get("venue","") or e.get("city",""))} '
            f'<span class="dist-badge"></span></div></div></div>')

def day_groups_html(events):
    """Groepeert opeenvolgende events met dezelfde datum onder 1 dag-kop
    i.p.v. de datum op elke rij te herhalen (cluster 5-vervolgronde, zie
    decisions.md 2026-08-18). `events` is al datum-gesorteerd (afgeleid van
    events_valid), dus groupby() volstaat zonder opnieuw te sorteren."""
    out = []
    for day, day_events in itertools.groupby(events, key=lambda e: e['date']):
        out.append(
            f'<div class="day-group"><h3 class="day-header">{day_label(day)}</h3>\n'
            + ''.join(event_html(e)+'\n' for e in day_events)
            + '</div>\n'
        )
    return ''.join(out)

main_html = ''.join(
    f'<div class="month-section" id="{month_id(m+"-01")}"><h2 class="month-header">{month_label(m+"-01")}</h2>\n'
    + day_groups_html(by_month[m])
    + '</div>\n'
    for m in months_sorted)

def fmt_date_long(iso):
    try: d=date.fromisoformat(iso); return f"{NL_DAYS[d.weekday()]} {d.day} {NL_MONTHS[d.month-1]} {d.year}"
    except: return iso

def expo_card_html(e):
    src = e.get('source',''); sk = safe_key(src)
    icon = GENRE_ICONS.get('expo','🖼️'); glabel = GENRE_LABELS.get('expo','Expo / Kunst')
    title_html = (f'<a href="{esc(e.get("url",""))}" target="_blank" rel="noopener">{esc(e.get("title",""))}</a>'
                  if e.get('url') else esc(e.get('title','')))
    loc = VENUE_LOC.get(src)
    prov = loc[2] if loc else e.get('province', 'Onbekend')
    # Prioriteit: exact event-eigen lat/lon (bv. van een aggregator die per
    # venue een precieze kaart-marker aanlevert, zie scrape_kunstpuntgroningen.py
    # / decisions.md 2026-08-17 — was tot dan toe ongebruikte infrastructuur:
    # events_db.py sloeg lat/lon al op maar geen enkele scraper vulde het en
    # deze functie las het nooit) > CITY_COORDS (plaatsnaam-lookup) > VENUE_LOC
    # (bron-niveau fallback, alleen zinvol bij één vaste locatie per bron).
    if e.get('lat') and e.get('lon'):
        lat_lon = f"{e['lat']},{e['lon']}"
    else:
        city_loc = CITY_COORDS.get((e.get('city') or '').strip())
        if city_loc:
            lat_lon = f'{city_loc[0]},{city_loc[1]}'
        elif loc:
            lat_lon = f'{loc[0]},{loc[1]}'
        else:
            lat_lon = ''
    d_start = e.get('date',''); d_end = e.get('date_end','')
    if d_end:
        date_txt = f"vanaf {fmt_date_long(d_start)} &middot; t/m {fmt_date_long(d_end)}"
    else:
        date_txt = f"vanaf {fmt_date_long(d_start)} &middot; einddatum onbekend"
    search_txt = esc(fold_diacritics((e.get('title','') + ' ' + (e.get('venue','') or e.get('city','') or '')).lower()))
    return (f'<div class="event expo-item {sk}" data-src="{src}" data-genre="expo" '
            f'data-prov="{prov}" data-latlon="{lat_lon}" '
            f'data-date="{esc(d_start)}" data-dateend="{esc(d_end or "9999-99-99")}" '
            f'data-titlekey="{esc(e.get("title","").lower())}" data-search="{search_txt}">'
            f'<div class="event-main"><div class="event-title">{title_html}</div>'
            f'<div class="event-daterange">{date_txt}</div>'
            f'<div class="event-venue">{esc(e.get("venue","") or e.get("city",""))} '
            f'<span class="dist-badge"></span></div></div>'
            f'<div class="event-badges">'
            f'<span class="badge badge-genre g-expo">{icon} {glabel}</span>'
            f'<span class="badge badge-src s-{sk}">{esc(SRC.get(src,(src,"",""))[0])}</span>'
            f'</div></div>')

expo_html = ''.join(expo_card_html(e) for e in expo_valid)

# Locale-onafhankelijk (was strftime('%B') — Engelse maandnaam op deze Windows-
# server-locale, zie decisions.md 2026-08-17, Claude Design-review).
_today = date.today()
today_str = f"{_today.day} {NL_MONTHS_LONG[_today.month-1]} {_today.year}"

provs = ['Groningen','Drenthe','Friesland','Overijssel','Utrecht','Noord-Holland','Zuid-Holland','Noord-Brabant','Gelderland']
prov_colors = {
    'Groningen':    '#1565c0',
    'Drenthe':      '#2e7d32',
    'Friesland':    '#6a1b9a',
    'Overijssel':   '#e65100',
    'Utrecht':      '#6a1b9a',
    'Noord-Holland':'#b71c1c',
    'Zuid-Holland': '#00695c',
    'Noord-Brabant':'#f57f17',
    'Gelderland':   '#4e342e',
}
prov_buttons = '<button class="btn active" data-prov="all">Alle provincies</button>\n'
for p in provs:
    c = prov_colors[p]
    prov_buttons += f'  <button class="btn" data-prov="{p}">{p}</button>\n'
prov_css = '\n'.join(
    f'.btn[data-prov="{p}"].active{{background:{prov_colors[p]};color:#fff;border-color:{prov_colors[p]};}}'
    for p in provs)

import json as _json
SPORT_COLORS = {
    'voetbal':   '#00a651',
    'basketbal': '#e07000',
    'volleybal': '#1565c0',
    'ijshockey': '#37474f',
    'handbal':   '#c62828',
    'korfbal':   '#f57c00',
}
sport_css = '\n'.join(
    f'.btn[data-sport="{s}"]:hover{{border-color:{c};color:{c};}}'
    f'.btn[data-sport="{s}"].active{{background:{c};color:#fff;border-color:{c};}}'
    for s,c in SPORT_COLORS.items())
club_css = '\n'.join(
    f'.btn[data-club="{k}"]:hover{{border-color:{SRC[k][2]};color:{SRC[k][2]};}}'
    f'.btn[data-club="{k}"].active{{background:{SRC[k][2]};color:{_contrast_text(SRC[k][2])};border-color:{SRC[k][2]};}}'
    for k in SPORT_SRCS if k in SRC)
gender_css = ('.btn[data-gender="all"].active{background:#555;color:#fff;border-color:#555;}'
              '.btn[data-gender="heren"].active{background:#1565c0;color:#fff;border-color:#1565c0;}'
              '.btn[data-gender="dames"].active{background:#c2185b;color:#fff;border-color:#c2185b;}')
landelijk_json = _json.dumps(sorted(LANDELIJK))

js = f'''
const TOTAL={total+expo_total};
const TOTAL_UITJES={total_uitjes}, TOTAL_SPORT={total_sport}, TOTAL_EXPO={expo_total};
let selSrc=new Set(), selGenre=new Set(), selProv=new Set(), maxDist=9999;
let currentMode='uitjes', selSport=new Set(), selClub=new Set(), selGender='all';
let searchQuery='', selWhenFrom=null, selWhenTo=null;
const SPORT_SRCS=new Set(['fcgroningen','fcemmen','heerenveen','cambuur','fctwente','goahead','peczwolle','donar','landstede','lycurgus','sudosa','friso','grizzlys','flyers','ogcapitals','hurryup','eoemmen','ldodk','dos46']);
const SPORT_BY_SRC={{fcgroningen:'voetbal',fcemmen:'voetbal',heerenveen:'voetbal',cambuur:'voetbal',fctwente:'voetbal',goahead:'voetbal',peczwolle:'voetbal',donar:'basketbal',landstede:'basketbal',lycurgus:'volleybal',sudosa:'volleybal',friso:'volleybal',grizzlys:'ijshockey',flyers:'ijshockey',ogcapitals:'ijshockey',hurryup:'handbal',eoemmen:'handbal',ldodk:'korfbal',dos46:'korfbal'}};
const SPORT_COLOR_MAP={{voetbal:'#00a651',basketbal:'#e07000',volleybal:'#1565c0',ijshockey:'#37474f',handbal:'#c62828',korfbal:'#f57c00'}};
const CLUB_COLOR_MAP={{fcgroningen:'#00a651',fcemmen:'#003087',heerenveen:'#0052a5',cambuur:'#ffd700',fctwente:'#cc0000',goahead:'#f5a623',peczwolle:'#0033a0',donar:'#e2001a',landstede:'#ff6b00',lycurgus:'#ffcc00',sudosa:'#2e7d32',friso:'#d32f2f',grizzlys:'#6699cc',flyers:'#003087',ogcapitals:'#e65100',hurryup:'#ff6600',eoemmen:'#c62828',ldodk:'#f57c00',dos46:'#1565c0'}};
const PROV_COLOR_MAP={{Groningen:'#1565c0',Drenthe:'#2e7d32',Friesland:'#6a1b9a',Overijssel:'#e65100',Utrecht:'#6a1b9a','Noord-Holland':'#b71c1c','Zuid-Holland':'#00695c','Noord-Brabant':'#f57f17',Gelderland:'#4e342e'}};
function actBtn(el,c){{el.style.background=c;el.style.color=(c==='#ffcc00'||c==='#ffd700')?'#212121':'#fff';el.style.borderColor=c;}}
function deactBtn(el){{el.style.background='';el.style.color='';el.style.borderColor='';}}
let centerLat=53.034, centerLon=6.735;

function initAriaPressed(){{
  document.querySelectorAll('.mode-toggle,.filters,.popover').forEach(c=>{{
    c.querySelectorAll('.btn,.mode-btn').forEach(b=>b.setAttribute('aria-pressed',b.classList.contains('active')?'true':'false'));
    new MutationObserver(muts=>{{
      muts.forEach(m=>{{
        const el=m.target;
        if(el.classList && (el.classList.contains('btn')||el.classList.contains('mode-btn'))){{
          el.setAttribute('aria-pressed',el.classList.contains('active')?'true':'false');
        }}
      }});
    }}).observe(c,{{attributes:true,attributeFilter:['class'],subtree:true}});
  }});
}}
initAriaPressed();

const backToTop=document.getElementById('back-to-top');
window.addEventListener('scroll',()=>{{backToTop.classList.toggle('hidden',window.scrollY<400);}},{{passive:true}});

function haversine(lat1,lon1,lat2,lon2){{
  const R=6371, dLat=(lat2-lat1)*Math.PI/180, dLon=(lon2-lon1)*Math.PI/180;
  const a=Math.sin(dLat/2)**2+Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
  return Math.round(R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a)));
}}

// Afstanden staan in deze Map i.p.v. in dataset.dist -- een Map-lookup is
// sneller dan telkens een DOM-attribuut lezen/schrijven bij 8202 events,
// zie decisions.md 2026-08-17 (Claude Design-review).
const eventDist=new Map();
function updateDistances(){{
  document.querySelectorAll('.event[data-latlon]').forEach(ev=>{{
    const ll=ev.dataset.latlon;
    if(!ll)return;
    const [lat,lon]=ll.split(',').map(Number);
    const d=haversine(centerLat,centerLon,lat,lon);
    eventDist.set(ev,d);
    const b=ev.querySelector('.dist-badge');
    if(b)b.textContent='~'+d+'km';
  }});
}}

// Bewust GEEN requestAnimationFrame-batching (eerst geprobeerd, zie
// decisions.md 2026-08-17): in een niet-zichtbaar/achtergrond-tabblad
// (document.visibilityState=='hidden') stelt de browser rAF-callbacks uit
// of pauzeert ze helemaal, waardoor een klik dan geen zichtbaar effect meer
// had — bevestigd met een echte browsertest. Marginale winst (1 klik = 1
// aanroep toch al) woog niet op tegen dat betrouwbaarheidsrisico.
function renderActiveFilters(){{
  const wrap=document.getElementById('active-filters');
  const tokens=[];
  const searchInput=document.getElementById('search-input');
  if(searchQuery) tokens.push(['Zoeken: "'+searchQuery+'"', ()=>{{searchInput.value='';searchQuery='';apply();}}]);
  const whenBtn=document.querySelector('#popover-when .btn[data-when].active');
  if(whenBtn&&whenBtn.dataset.when!=='all') tokens.push([whenBtn.textContent, ()=>document.querySelector('#popover-when .btn[data-when="all"]').click()]);
  else if(!whenBtn&&(selWhenFrom||selWhenTo)) tokens.push(['Periode: '+(selWhenFrom||'…')+' t/m '+(selWhenTo||'…'), ()=>{{whenFromInput.value='';whenToInput.value='';onCustomWhenChange();}}]);
  selProv.forEach(p=>{{const b=document.querySelector('.btn[data-prov="'+p+'"]'); if(b)tokens.push([p, ()=>b.click()]);}});
  if(maxDist<9999) tokens.push(['≤ '+maxDist+' km', ()=>{{document.querySelector('.dist-btn[data-dist="9999"]').click();}}]);
  if(currentMode==='uitjes'){{
    selGenre.forEach(g=>{{const b=document.querySelector('.btn[data-genre="'+g+'"]'); if(b)tokens.push([b.textContent, ()=>b.click()]);}});
    selSrc.forEach(s=>{{const b=document.querySelector('.btn[data-src="'+s+'"]'); if(b)tokens.push([b.textContent, ()=>b.click()]);}});
  }}
  if(currentMode==='sport'){{
    selSport.forEach(sp=>{{const b=document.querySelector('.btn[data-sport="'+sp+'"]'); if(b)tokens.push([b.textContent, ()=>b.click()]);}});
    selClub.forEach(c=>{{const b=document.querySelector('.btn[data-club="'+c+'"]'); if(b)tokens.push([b.textContent, ()=>b.click()]);}});
    if(selGender!=='all'){{const b=document.querySelector('.btn[data-gender="'+selGender+'"]'); if(b)tokens.push([b.textContent, ()=>document.querySelector('.btn[data-gender="all"]').click()]);}}
  }}
  wrap.innerHTML='';
  if(tokens.length===0){{wrap.classList.add('hidden');return;}}
  wrap.classList.remove('hidden');
  tokens.forEach(([label,onRemove])=>{{
    const t=document.createElement('span'); t.className='filter-token';
    const txt=document.createElement('span'); txt.textContent=label;
    const btn=document.createElement('button'); btn.textContent='×'; btn.setAttribute('aria-label','Verwijder filter: '+label);
    btn.addEventListener('click',onRemove);
    t.appendChild(txt); t.appendChild(btn);
    wrap.appendChild(t);
  }});
  const clearAll=document.createElement('button'); clearAll.className='filter-token clear-all'; clearAll.textContent='Wis alles';
  clearAll.addEventListener('click',clearAllFilters);
  wrap.appendChild(clearAll);
}}

function apply(){{
  let v=0;
  document.querySelectorAll('.event').forEach(ev=>{{
    const src=ev.dataset.src, dist=eventDist.get(ev)??9999;
    const isSport=SPORT_SRCS.has(src);
    const isExpo=ev.classList.contains('expo-item');
    let ok;
    if(currentMode==='uitjes'){{
      ok=!isSport&&!isExpo&&(selSrc.size===0||selSrc.has(src))&&(selGenre.size===0||selGenre.has(ev.dataset.genre))&&(selProv.size===0||selProv.has(ev.dataset.prov))&&dist<=maxDist;
    }}else if(currentMode==='sport'){{
      const sp=SPORT_BY_SRC[src];
      const evGender=ev.dataset.gender||'heren';
      ok=isSport&&(selSport.size===0||selSport.has(sp))&&(selClub.size===0||selClub.has(src))&&(selGender==='all'||evGender===selGender||evGender==='gemengd')&&(selProv.size===0||selProv.has(ev.dataset.prov))&&dist<=maxDist;
    }}else{{
      ok=isExpo&&(selProv.size===0||selProv.has(ev.dataset.prov))&&dist<=maxDist;
    }}
    if(ok&&searchWords.length){{
      const hay=ev.dataset.search||'';
      ok=searchWords.every(w=>hay.includes(w));
    }}
    if(ok&&currentMode!=='exposities'&&(selWhenFrom||selWhenTo)){{
      const evEnd=ev.dataset.dateend||ev.dataset.date;
      ok=(!selWhenFrom||evEnd>=selWhenFrom)&&(!selWhenTo||ev.dataset.date<=selWhenTo);
    }}
    ev.classList.toggle('hidden',!ok);if(ok)v++;
  }});
  document.querySelectorAll('.day-group').forEach(g=>{{
    g.classList.toggle('hidden',g.querySelectorAll('.event:not(.hidden)').length===0);
  }});
  document.querySelectorAll('.month-section').forEach(s=>{{
    s.classList.toggle('hidden',s.querySelectorAll('.event:not(.hidden)').length===0);
  }});
  const modeTotal=currentMode==='uitjes'?TOTAL_UITJES:currentMode==='sport'?TOTAL_SPORT:TOTAL_EXPO;
  const modeNoun=currentMode==='uitjes'?'uitjes':currentMode==='sport'?'wedstrijden':'exposities';
  document.getElementById('stats').textContent=v===modeTotal?'Toont alle '+modeTotal+' '+modeNoun:'Toont '+v+' van '+modeTotal+' '+modeNoun;
  const emptyEl=document.getElementById('empty-state');
  emptyEl.classList.toggle('hidden',v!==0);
  if(v===0){{
    // Directe uitweg-knop i.p.v. alleen tekst -- gemeld door Claude Design
    // 2026-08-18: gebruiker moest zelf terug naar de toolbar om iets te
    // wijzigen. "Alle afstanden" als eerste, gerichte stap als afstand de
    // vermoedelijke oorzaak is; anders meteen "Wis filters".
    emptyEl.innerHTML='';
    const msg=document.createElement('span');
    msg.textContent = maxDist<9999
      ? 'Geen events gevonden binnen '+maxDist+' km — probeer een grotere afstand of andere filters. '
      : 'Geen events gevonden met de huidige filters — probeer andere filters. ';
    emptyEl.appendChild(msg);
    if(maxDist<9999){{
      const distBtn=document.createElement('button');
      distBtn.className='empty-action-btn';
      distBtn.textContent='Alle afstanden';
      distBtn.addEventListener('click',()=>document.querySelector('.dist-btn[data-dist="9999"]').click());
      emptyEl.appendChild(distBtn);
    }}
    const clearBtn=document.createElement('button');
    clearBtn.className='empty-action-btn';
    clearBtn.textContent='Wis filters';
    clearBtn.addEventListener('click',clearAllFilters);
    emptyEl.appendChild(clearBtn);
  }}
  if(currentMode==='uitjes'){{
    document.querySelector('.btn[data-src="all"]')?.classList.toggle('active',selSrc.size===0);
    document.querySelector('.btn[data-genre="all"]')?.classList.toggle('active',selGenre.size===0);
  }}
  const apb=document.querySelector('.btn[data-prov="all"]'),apa=selProv.size===0;
  apb.classList.toggle('active',apa);if(apa)actBtn(apb,'#555');else deactBtn(apb);
  document.getElementById('dist-label').textContent=maxDist>=9999?'Alle afstanden':'≤ '+maxDist+' km';
  renderActiveFilters();
  updateFilterCounts();
  syncURL();
}}

async function geocode(addr){{
  try{{
    const url='https://nominatim.openstreetmap.org/search?q='+encodeURIComponent(addr)+'&format=json&limit=1&countrycodes=nl';
    const r=await fetch(url);
    const data=await r.json();
    if(data.length>0) return [parseFloat(data[0].lat),parseFloat(data[0].lon),data[0].display_name];
  }}catch(e){{}}
  return null;
}}

document.getElementById('addr-btn').addEventListener('click',async()=>{{
  const addr=document.getElementById('addr-input').value.trim();
  if(!addr)return;
  const status=document.getElementById('addr-status');
  status.textContent='Zoeken…';
  const res=await geocode(addr);
  if(res){{
    centerLat=res[0]; centerLon=res[1];
    status.textContent='📍 '+res[2].split(',').slice(0,2).join(', ');
    updateDistances(); apply();
  }}else{{
    status.textContent='❌ Niet gevonden';
  }}
}});

document.getElementById('addr-input').addEventListener('keydown',e=>{{
  if(e.key==='Enter') document.getElementById('addr-btn').click();
}});
// Ook toepassen bij het verlaten van het veld (blur), niet alleen op Enter/
// klik -- anders staat er getypte tekst die niets doet totdat je expliciet
// op Zoek klikt, terwijl de status eronder nog het oude punt toont (gemeld
// door Claude Design 2026-08-18: 'Zuidlaren' in het veld, 'standaard: Annen'
// eronder).
document.getElementById('addr-input').addEventListener('blur',()=>{{
  const addr=document.getElementById('addr-input').value.trim();
  if(addr) document.getElementById('addr-btn').click();
}});

document.getElementById('loc-btn').addEventListener('click',()=>{{
  const status=document.getElementById('addr-status');
  if(!navigator.geolocation){{ status.textContent='Niet beschikbaar'; return; }}
  status.textContent='Locatie ophalen…';
  navigator.geolocation.getCurrentPosition(pos=>{{
    centerLat=pos.coords.latitude; centerLon=pos.coords.longitude;
    document.getElementById('addr-input').value='';
    status.textContent='📍 Huidige locatie ('+centerLat.toFixed(3)+', '+centerLon.toFixed(3)+')';
    updateDistances(); apply();
  }},()=>{{ status.textContent='❌ Locatie geweigerd'; }});
}});

const distCustomInput=document.getElementById('dist-custom-input');
document.querySelectorAll('.dist-btn').forEach(b=>{{
  b.addEventListener('click',function(){{
    maxDist=parseInt(this.dataset.dist);
    document.querySelectorAll('.dist-btn').forEach(x=>x.classList.toggle('active',x===this));
    distCustomInput.value='';
    apply();
  }});
}});
distCustomInput.addEventListener('change',function(){{
  const n=parseInt(this.value,10);
  maxDist=(this.value.trim()===''||isNaN(n)||n<=0)?9999:n;
  document.querySelectorAll('.dist-btn').forEach(x=>x.classList.remove('active'));
  apply();
}});

// --- Zoekveld (titel + venue), gedebouncet zodat niet elke toetsaanslag
// meteen 8202 events opnieuw doorloopt -- zie decisions.md 2026-08-17. ---
// Diakrieten-folding (bv. 'zummerbuhne'->'zummerbuhne', matcht dan tegen de
// server-side ook al gefolde data-search) + losse woorden voor een AND-match
// i.p.v. een letterlijke substring -- 'dorpshuis annen' matchte voorheen
// niet als de titel 'Dorpshuis Annen' as-is stond maar de woordvolgorde in
// de zoekterm anders was. Zie decisions.md 2026-08-18.
function foldDiacritics(s){{ return s.normalize('NFD').replace(/[\u0300-\u036f]/g,''); }}
let searchDebounce=null, searchWords=[];
document.getElementById('search-input').addEventListener('input',function(){{
  clearTimeout(searchDebounce);
  const val=this.value;
  searchDebounce=setTimeout(()=>{{
    searchQuery=foldDiacritics(val.trim().toLowerCase());
    searchWords=searchQuery.split(/\\s+/).filter(Boolean);
    apply();
  }},250);
}});

// --- Datumfilter (Vandaag/Dit weekend/Deze week/Deze maand/eigen periode) ---
function computeWhenRange(preset){{
  const now=new Date(); now.setHours(0,0,0,0);
  // LOKALE datumcomponenten, NIET .toISOString() (die converteert naar UTC --
  // met Nederlandse zomertijd (UTC+2) schuift 'vandaag' dan een dag terug,
  // bevestigd met een echte browsertest. Zie decisions.md 2026-08-17.)
  const iso=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  const addDays=(d,n)=>{{const r=new Date(d);r.setDate(r.getDate()+n);return r;}};
  if(preset==='today') return [iso(now),iso(now)];
  if(preset==='weekend'){{
    const day=now.getDay();
    let start=now;
    if(day>=1&&day<=5) start=addDays(now,5-day);
    const end=day===0?now:addDays(start,day===6?1:2);
    return [iso(start),iso(end)];
  }}
  if(preset==='week') return [iso(now),iso(addDays(now,6))];
  if(preset==='month'){{
    const end=new Date(now.getFullYear(),now.getMonth()+1,0);
    return [iso(now),iso(end)];
  }}
  return [null,null];
}}
const whenFromInput=document.getElementById('when-from'), whenToInput=document.getElementById('when-to');
document.querySelectorAll('#popover-when .btn[data-when]').forEach(b=>{{
  b.addEventListener('click',function(){{
    document.querySelectorAll('#popover-when .btn[data-when]').forEach(x=>x.classList.toggle('active',x===this));
    const [from,to]=computeWhenRange(this.dataset.when);
    selWhenFrom=from; selWhenTo=to;
    whenFromInput.value=from||''; whenToInput.value=to||'';
    apply();
  }});
}});
function onCustomWhenChange(){{
  document.querySelectorAll('#popover-when .btn[data-when]').forEach(x=>x.classList.remove('active'));
  selWhenFrom=whenFromInput.value||null;
  selWhenTo=whenToInput.value||null;
  if(!selWhenFrom&&!selWhenTo) document.querySelector('#popover-when .btn[data-when="all"]').classList.add('active');
  apply();
}}
whenFromInput.addEventListener('change',onCustomWhenChange);
whenToInput.addEventListener('change',onCustomWhenChange);

// --- Sorteren voor Uitjes (datum/afstand) -- herordent kaarten BINNEN elke
// DAG-groep (niet over dag-grenzen heen, sinds de dag-groepering van
// 2026-08-18 -- een kaart fysiek onder een andere dag-kop verplaatsen zou
// misleidend zijn, het event is niet echt op die dag). Lager risico dan de
// maand-groepering zelf op te heffen zoals bij Exposities' platte lijst. ---
document.querySelectorAll('#uitjes-sort .btn[data-usort]').forEach(b=>{{
  b.addEventListener('click',function(){{
    document.querySelectorAll('#uitjes-sort .btn[data-usort]').forEach(x=>x.classList.toggle('active',x===this));
    const sort=this.dataset.usort;
    document.querySelectorAll('.day-group').forEach(grp=>{{
      const items=Array.from(grp.querySelectorAll('.event'));
      items.sort((a,c)=>{{
        if(sort==='afstand') return (eventDist.get(a)??9999)-(eventDist.get(c)??9999);
        return (a.dataset.date||'').localeCompare(c.dataset.date||'');
      }});
      items.forEach(it=>grp.appendChild(it));
    }});
  }});
}});

const LANDELIJK=new Set({landelijk_json});
document.querySelector('.btn[data-src-group="landelijk"]').addEventListener('click',function(){{
  const isActive=this.classList.contains('active');
  if(isActive){{
    LANDELIJK.forEach(v=>selSrc.delete(v));
    this.classList.remove('active');
  }}else{{
    LANDELIJK.forEach(v=>selSrc.add(v));
    this.classList.add('active');
    document.querySelector('.btn[data-src="all"]').classList.remove('active');
  }}
  document.querySelectorAll('.btn[data-src]:not([data-src="all"])').forEach(x=>x.classList.toggle('active',selSrc.has(x.dataset.src)));
  apply();
}});
document.querySelectorAll('.btn[data-src]').forEach(b=>b.addEventListener('click',()=>{{
  const v=b.dataset.src;
  if(v==='all'){{selSrc.clear();document.querySelector('.btn[data-src-group="landelijk"]').classList.remove('active');}}
  else{{if(selSrc.has(v))selSrc.delete(v);else selSrc.add(v);}}
  document.querySelectorAll('.btn[data-src]:not([data-src="all"])').forEach(x=>x.classList.toggle('active',selSrc.has(x.dataset.src)));
  apply();
}}));
document.querySelectorAll('.btn[data-genre]').forEach(b=>b.addEventListener('click',()=>{{
  const v=b.dataset.genre;
  if(v==='all')selGenre.clear();
  else{{if(selGenre.has(v))selGenre.delete(v);else selGenre.add(v);}}
  document.querySelectorAll('.btn[data-genre]:not([data-genre="all"])').forEach(x=>x.classList.toggle('active',selGenre.has(x.dataset.genre)));
  apply();
}}));
document.querySelectorAll('.btn[data-prov]').forEach(b=>b.addEventListener('click',()=>{{
  const v=b.dataset.prov;
  if(v==='all')selProv.clear();
  else{{if(selProv.has(v))selProv.delete(v);else selProv.add(v);}}
  document.querySelectorAll('.btn[data-prov]:not([data-prov="all"])').forEach(x=>{{
    const a=selProv.has(x.dataset.prov);x.classList.toggle('active',a);
    if(a)actBtn(x,PROV_COLOR_MAP[x.dataset.prov]||'#555');else deactBtn(x);
  }});
  const pb=document.querySelector('.btn[data-prov="all"]'),pa=selProv.size===0;
  pb.classList.toggle('active',pa);if(pa)actBtn(pb,'#555');else deactBtn(pb);
  apply();
}}));

// --- Popovers: 1 tegelijk open, sluiten bij buitenklik/Escape/modus-wissel.
// Toolbar-knop-zichtbaarheid bepaalt of een popover uberhaupt te openen is
// (geen aparte binnen-popover mode-check meer nodig, behalve voor Sorteren
// dat 2 mogelijke inhoud-blokken deelt tussen uitjes/exposities). ---
function closeAllPopovers(){{
  document.querySelectorAll('.popover').forEach(p=>p.hidden=true);
  document.querySelectorAll('.toolbar-btn[data-popover]').forEach(b=>b.setAttribute('aria-expanded','false'));
  document.getElementById('popover-backdrop').hidden=true;
}}
function positionPopover(popover,trigger){{
  const r=trigger.getBoundingClientRect();
  popover.style.top=(r.bottom+4)+'px';
  let left=r.left;
  const maxLeft=window.innerWidth-popover.offsetWidth-8;
  if(left>maxLeft) left=Math.max(8,maxLeft);
  popover.style.left=left+'px';
}}
document.querySelectorAll('.toolbar-btn[data-popover]').forEach(btn=>{{
  btn.addEventListener('click',function(e){{
    e.stopPropagation();
    const popover=document.getElementById(this.dataset.popover);
    const wasOpen=!popover.hidden;
    closeAllPopovers();
    if(!wasOpen){{
      popover.hidden=false;
      document.getElementById('popover-backdrop').hidden=false;
      this.setAttribute('aria-expanded','true');
      positionPopover(popover,this);
    }}
  }});
}});
document.getElementById('popover-backdrop').addEventListener('click',closeAllPopovers);
document.addEventListener('keydown',e=>{{if(e.key==='Escape')closeAllPopovers();}});
document.querySelectorAll('.popover').forEach(p=>p.addEventListener('click',e=>e.stopPropagation()));

// --- Filterteller per toolbar-knop (Claude Design's 'filterteller'-voorstel) ---
function updateFilterCounts(){{
  const setCount=(id,n)=>{{const el=document.getElementById(id); if(el) el.textContent=n>0?' ('+n+')':'';}};
  setCount('tb-when-count',(selWhenFrom||selWhenTo)?1:0);
  setCount('tb-where-count',selProv.size+(maxDist<9999?1:0));
  setCount('tb-genre-count',selGenre.size);
  setCount('tb-src-count',selSrc.size);
  setCount('tb-sport-count',selSport.size);
  setCount('tb-club-count',selClub.size+(selGender!=='all'?1:0));
}}

// --- Bron-popover: eigen zoekveld filtert de gegroepeerde chips, verbergt
// een groep-kopje als geen enkele chip erin nog matcht. ---
document.getElementById('src-search').addEventListener('input',function(){{
  const q=this.value.trim().toLowerCase();
  const list=document.getElementById('popover-src-list');
  let lastGroupLabel=null, groupVisible=false;
  Array.from(list.children).forEach(el=>{{
    if(el.classList.contains('src-group-label')){{
      if(lastGroupLabel) lastGroupLabel.style.display=groupVisible?'':'none';
      lastGroupLabel=el; groupVisible=false;
    }}else if(el.dataset.srcLabel){{
      const match=!q||el.dataset.srcLabel.includes(q);
      el.style.display=match?'':'none';
      if(match) groupVisible=true;
    }}
  }});
  if(lastGroupLabel) lastGroupLabel.style.display=groupVisible?'':'none';
}});

// --- "Wis filters": 1 centrale functie, hergebruikt door zowel de nieuwe
// toolbar-knop als de "Wis alles"-token in de actieve-filter-samenvatting. ---
function clearAllFilters(){{
  searchQuery=''; document.getElementById('search-input').value='';
  document.querySelector('#popover-when .btn[data-when="all"]')?.click();
  document.querySelector('.btn[data-prov="all"]')?.click();
  document.querySelector('.dist-btn[data-dist="9999"]')?.click();
  document.querySelector('.btn[data-genre="all"]')?.click();
  document.querySelector('.btn[data-src="all"]')?.click();
  document.querySelector('.btn[data-sport="all"]')?.click();
  document.querySelector('.btn[data-club="all"]')?.click();
  document.querySelector('.btn[data-gender="all"]')?.click();
  apply();
}}
document.getElementById('clear-filters-btn').addEventListener('click',()=>{{clearAllFilters();closeAllPopovers();}});

function setMode(m){{
  currentMode=m;
  document.getElementById('btn-uitjes').classList.toggle('active',m==='uitjes');
  document.getElementById('btn-sport').classList.toggle('active',m==='sport');
  document.getElementById('btn-exposities').classList.toggle('active',m==='exposities');
  closeAllPopovers();
  // Welke toolbar-knoppen (en dus welke popovers) zijn relevant per modus --
  // 'Waar' en 'Sorteren' en het zoekveld blijven in alle 3 modi beschikbaar.
  document.getElementById('tb-when').style.display=m!=='exposities'?'':'none';
  document.getElementById('tb-genre').style.display=m==='uitjes'?'':'none';
  document.getElementById('tb-src').style.display=m==='uitjes'?'':'none';
  document.getElementById('tb-sport').style.display=m==='sport'?'':'none';
  document.getElementById('tb-club').style.display=m==='sport'?'':'none';
  document.getElementById('expo-filters').style.display=m==='exposities'?'flex':'none';
  document.getElementById('uitjes-sort').style.display=(m==='uitjes'||m==='sport')?'':'none';
  document.getElementById('month-nav-wrap').style.display=m==='exposities'?'none':'';
  document.querySelector('main').style.display=m==='exposities'?'none':'';
  document.getElementById('expo-wrap').style.display=m==='exposities'?'':'none';
  // Filters die in de nieuwe modus geen betekenis hebben vervallen vanzelf;
  // de rest (provincie, afstand, zoekterm) blijft behouden bij modus-wissel
  // -- voorheen werd bij ELKE wissel alles gewist, zie decisions.md 2026-08-17
  // (Claude Design-review, Michiel koos expliciet voor 'bewaren waar mogelijk').
  if(m!=='sport'){{
    selSport.clear();selClub.clear();selGender='all';
    document.querySelectorAll('.btn[data-sport],.btn[data-club]').forEach(x=>deactBtn(x));
    document.querySelectorAll('.btn[data-gender]').forEach(x=>x.classList.toggle('active',x.dataset.gender==='all'));
    const smSA=document.querySelector('.btn[data-sport="all"]'),smCA=document.querySelector('.btn[data-club="all"]');
    if(smSA){{smSA.classList.add('active');actBtn(smSA,'#555');}}
    if(smCA){{smCA.classList.add('active');actBtn(smCA,'#555');}}
  }}
  if(m!=='uitjes'){{
    selSrc.clear();selGenre.clear();
    document.querySelectorAll('.btn[data-src]:not([data-src="all"]),.btn[data-genre]:not([data-genre="all"])').forEach(x=>x.classList.remove('active'));
    document.querySelector('.btn[data-src="all"]')?.classList.add('active');
    document.querySelector('.btn[data-genre="all"]')?.classList.add('active');
  }}
  apply();
}}
document.querySelectorAll('.btn[data-sport]').forEach(b=>b.addEventListener('click',()=>{{
  const v=b.dataset.sport;
  if(v==='all'){{selSport.clear();}}
  else{{if(selSport.has(v))selSport.delete(v);else selSport.add(v);}}
  document.querySelectorAll('.btn[data-sport]:not([data-sport="all"])').forEach(x=>{{
    const a=selSport.has(x.dataset.sport);x.classList.toggle('active',a);
    if(a)actBtn(x,SPORT_COLOR_MAP[x.dataset.sport]||'#555');else deactBtn(x);
  }});
  const sb=document.querySelector('.btn[data-sport="all"]'),sa=selSport.size===0;
  sb.classList.toggle('active',sa);if(sa)actBtn(sb,'#555');else deactBtn(sb);
  // Toon/verberg clubknoppen op basis van geselecteerde sport
  document.querySelectorAll('[data-club]:not([data-club="all"])').forEach(x=>{{
    x.style.display=(selSport.size===0||selSport.has(x.dataset.sportType))?'':'none';
  }});
  selClub.clear();
  document.querySelectorAll('[data-club]:not([data-club="all"])').forEach(x=>{{x.classList.remove('active');deactBtn(x);}});
  const cb=document.querySelector('.btn[data-club="all"]');
  cb.classList.add('active');actBtn(cb,'#555');
  apply();
}}));
document.querySelectorAll('.btn[data-club]').forEach(b=>b.addEventListener('click',()=>{{
  const v=b.dataset.club;
  if(v==='all')selClub.clear();
  else{{if(selClub.has(v))selClub.delete(v);else selClub.add(v);}}
  document.querySelectorAll('.btn[data-club]:not([data-club="all"])').forEach(x=>{{
    const a=selClub.has(x.dataset.club);x.classList.toggle('active',a);
    if(a)actBtn(x,CLUB_COLOR_MAP[x.dataset.club]||'#555');else deactBtn(x);
  }});
  const cb2=document.querySelector('.btn[data-club="all"]'),ca=selClub.size===0;
  cb2.classList.toggle('active',ca);if(ca)actBtn(cb2,'#555');else deactBtn(cb2);
  apply();
}}));
document.querySelectorAll('.btn[data-gender]').forEach(b=>b.addEventListener('click',()=>{{
  selGender=b.dataset.gender;
  document.querySelectorAll('.btn[data-gender]').forEach(x=>x.classList.toggle('active',x.dataset.gender===selGender));
  apply();
}}));
document.querySelectorAll('.btn[data-sort]').forEach(b=>b.addEventListener('click',()=>{{
  document.querySelectorAll('.btn[data-sort]').forEach(x=>x.classList.toggle('active',x===b));
  const sort=b.dataset.sort;
  const wrap=document.getElementById('expo-wrap');
  const items=Array.from(wrap.querySelectorAll('.expo-item'));
  items.sort((a,c)=>{{
    if(sort==='start') return a.dataset.date.localeCompare(c.dataset.date);
    if(sort==='end') return a.dataset.dateend.localeCompare(c.dataset.dateend);
    return a.dataset.titlekey.localeCompare(c.dataset.titlekey);
  }});
  items.forEach(it=>wrap.appendChild(it));
}}));
// --- URL-state: filters/modus/zoekterm in de query-string, zodat een
// refresh/terug-knop de selectie niet wist en je een link kunt delen.
// history.replaceState (niet pushState) i.p.v. elke chip-klik een eigen
// back-button-stap te geven. ---
const DEFAULT_LAT=53.034, DEFAULT_LON=6.735;

// --- localStorage: adres + laatste modus onthouden tussen bezoeken (was
// eerder bewust uitgesteld, zie decisions.md 2026-08-17 -- nu gebouwd op
// Michiels verzoek). URL-params winnen altijd van localStorage: een gedeelde
// link moet niet stilzwijgend overschreven worden door iemands eigen
// eerder-opgeslagen voorkeur. ---
function saveLocalPrefs(){{
  try{{
    localStorage.setItem('ua_addr',document.getElementById('addr-input').value);
    localStorage.setItem('ua_lat',centerLat);
    localStorage.setItem('ua_lon',centerLon);
    localStorage.setItem('ua_mode',currentMode);
  }}catch(e){{}}
}}
function loadLocalPrefs(){{
  try{{
    return {{
      addr: localStorage.getItem('ua_addr'),
      lat: parseFloat(localStorage.getItem('ua_lat')),
      lon: parseFloat(localStorage.getItem('ua_lon')),
      mode: localStorage.getItem('ua_mode')
    }};
  }}catch(e){{ return {{}}; }}
}}

function syncURL(){{
  const p=new URLSearchParams();
  if(currentMode!=='uitjes') p.set('mode',currentMode);
  if(selProv.size) p.set('prov',Array.from(selProv).join(','));
  if(maxDist<9999) p.set('d',maxDist);
  if(Math.abs(centerLat-DEFAULT_LAT)>0.0001||Math.abs(centerLon-DEFAULT_LON)>0.0001){{
    p.set('lat',centerLat.toFixed(4)); p.set('lon',centerLon.toFixed(4));
  }}
  if(searchQuery) p.set('q',searchQuery);
  const whenBtn=document.querySelector('#popover-when .btn[data-when].active');
  if(whenBtn&&whenBtn.dataset.when!=='all'){{
    p.set('when',whenBtn.dataset.when);
  }}else if(selWhenFrom||selWhenTo){{
    if(selWhenFrom) p.set('from',selWhenFrom);
    if(selWhenTo) p.set('to',selWhenTo);
  }}
  if(currentMode==='uitjes'){{
    if(selGenre.size) p.set('genre',Array.from(selGenre).join(','));
    if(selSrc.size) p.set('src',Array.from(selSrc).join(','));
    const usortBtn=document.querySelector('#uitjes-sort .btn[data-usort].active');
    if(usortBtn&&usortBtn.dataset.usort!=='datum') p.set('usort',usortBtn.dataset.usort);
  }}
  if(currentMode==='sport'){{
    if(selSport.size) p.set('sport',Array.from(selSport).join(','));
    if(selClub.size) p.set('club',Array.from(selClub).join(','));
    if(selGender!=='all') p.set('gender',selGender);
  }}
  if(currentMode==='exposities'){{
    const sortBtn=document.querySelector('#expo-filters .btn[data-sort].active');
    if(sortBtn&&sortBtn.dataset.sort!=='start') p.set('esort',sortBtn.dataset.sort);
  }}
  const qs=p.toString();
  history.replaceState(null,'',location.pathname+(qs?'?'+qs:''));
  saveLocalPrefs();
}}
function restoreFromURL(){{
  const p=new URLSearchParams(location.search);
  const hasAnyParam=Array.from(p.keys()).length>0;
  const local=hasAnyParam?{{}}:loadLocalPrefs();

  const mode=p.get('mode')||local.mode;
  if(mode==='sport'||mode==='exposities') currentMode=mode;

  const prov=p.get('prov'); if(prov) prov.split(',').forEach(x=>selProv.add(x));
  const d=parseInt(p.get('d'),10); if(!isNaN(d)&&d>0) maxDist=d;

  const lat=parseFloat(p.get('lat')), lon=parseFloat(p.get('lon'));
  if(!isNaN(lat)&&!isNaN(lon)){{
    centerLat=lat; centerLon=lon;
    document.getElementById('addr-status').textContent='📍 uit gedeelde link';
  }}else if(local.addr&&!isNaN(local.lat)&&!isNaN(local.lon)){{
    centerLat=local.lat; centerLon=local.lon;
    document.getElementById('addr-input').value=local.addr;
    document.getElementById('addr-status').textContent='📍 '+local.addr+' (onthouden)';
  }}

  const q=p.get('q'); if(q){{searchQuery=q; document.getElementById('search-input').value=q;}}

  const when=p.get('when');
  const from=p.get('from'), to=p.get('to');
  if(when){{
    const [wf,wt]=computeWhenRange(when);
    selWhenFrom=wf; selWhenTo=wt;
    document.querySelectorAll('#popover-when .btn[data-when]').forEach(x=>x.classList.toggle('active',x.dataset.when===when));
    whenFromInput.value=wf||''; whenToInput.value=wt||'';
  }}else if(from||to){{
    selWhenFrom=from||null; selWhenTo=to||null;
    whenFromInput.value=from||''; whenToInput.value=to||'';
  }}

  const genre=p.get('genre'); if(genre) genre.split(',').forEach(x=>selGenre.add(x));
  const src=p.get('src'); if(src) src.split(',').forEach(x=>selSrc.add(x));
  const usort=p.get('usort');
  if(usort) document.querySelectorAll('#uitjes-sort .btn[data-usort]').forEach(x=>x.classList.toggle('active',x.dataset.usort===usort));

  const sport=p.get('sport'); if(sport) sport.split(',').forEach(x=>selSport.add(x));
  const club=p.get('club'); if(club) club.split(',').forEach(x=>selClub.add(x));
  const gender=p.get('gender'); if(gender){{selGender=gender;}}

  const esort=p.get('esort');
  if(esort) document.querySelectorAll('#expo-filters .btn[data-sort]').forEach(x=>x.classList.toggle('active',x.dataset.sort===esort));

  document.querySelectorAll('.btn[data-prov]').forEach(b=>{{if(b.dataset.prov!=='all') b.classList.toggle('active',selProv.has(b.dataset.prov));}});
  document.querySelectorAll('.btn[data-genre]').forEach(b=>{{if(b.dataset.genre!=='all') b.classList.toggle('active',selGenre.has(b.dataset.genre));}});
  document.querySelectorAll('.btn[data-src]').forEach(b=>{{if(b.dataset.src) b.classList.toggle('active',selSrc.has(b.dataset.src));}});
  document.querySelectorAll('.btn[data-sport]').forEach(b=>{{if(b.dataset.sport!=='all') b.classList.toggle('active',selSport.has(b.dataset.sport));}});
  document.querySelectorAll('.btn[data-club]').forEach(b=>{{if(b.dataset.club!=='all') b.classList.toggle('active',selClub.has(b.dataset.club));}});
  document.querySelectorAll('.btn[data-gender]').forEach(b=>{{b.classList.toggle('active',b.dataset.gender===selGender);}});
  if(maxDist<9999){{
    const knownStep=[10,25,50,100].includes(maxDist);
    document.querySelectorAll('.dist-btn').forEach(b=>b.classList.toggle('active',knownStep&&parseInt(b.dataset.dist)===maxDist));
    if(!knownStep) document.getElementById('dist-custom-input').value=maxDist;
  }}
}}

// Init: URL-state herstellen (indien aanwezig) vóór de eerste render, dan
// afstanden vanuit standaard centrum (Annen), en de mode-filtering toepassen
// (bugfix 2026-08-15: zonder de setMode-aanroep bleven bv. sportwedstrijden
// zichtbaar tussen de Uitjes tot de gebruiker voor het eerst een filter
// aanklikte). setMode(currentMode) i.p.v. hardcoded 'uitjes' zodat een
// herstelde modus uit de URL niet meteen weer overschreven wordt.
restoreFromURL();
updateDistances();
setMode(currentMode);
'''

html = f'''<!DOCTYPE html>
<html lang="nl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Uitjes Agenda</title>
<style>
:root{{{css_vars}
  --bg:#f9f9f9;--card:#fff;--border:#e0e0e0;--text:#212121;--muted:#6b6b6b;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:15px;line-height:1.45;}}
/* Eén sticky wrapper voor topbar+toolbar samen (i.p.v. losse gestapelde
   sticky-elementen met een handmatig berekende top-offset) -- voorkomt het
   fragiele-offset-probleem dat bij de eerste sticky-volgorde-triage werd
   overwogen (header-hoogte kan wrappen op smalle schermen), zie overleg.md
   punt 17 / decisions.md 2026-08-17 (cluster 5, toolbar-herbouw). */
.topbar{{background:#fff;border-bottom:2px solid var(--border);position:sticky;top:0;z-index:100;padding:10px 16px 8px;}}
.topbar-top{{display:flex;align-items:center;gap:16px;flex-wrap:wrap;}}
.topbar-top h1{{font-size:1.2rem;font-weight:700;margin:0;}}
.meta{{font-size:0.78rem;color:var(--muted);margin-top:2px;}}
.mode-toggle{{display:flex;gap:8px;}}
.mode-btn{{padding:5px 18px;border-radius:20px;border:2px solid #ccc;background:#fff;cursor:pointer;font-weight:700;font-size:0.88rem;}}
.mode-btn.active{{background:#1565c0;color:#fff;border-color:#1565c0;}}
.toolbar{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:8px;}}
.toolbar-buttons{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;flex:1 1 auto;}}
.toolbar-btn{{padding:8px 14px;min-height:44px;border-radius:20px;border:1.5px solid #ccc;background:#fff;cursor:pointer;font-size:0.85rem;color:#555;white-space:nowrap;display:inline-flex;align-items:center;}}
.toolbar-btn:hover{{opacity:.85;}}
.toolbar-btn::after{{content:'▾';margin-left:5px;font-size:0.7em;}}
.toolbar-btn[aria-expanded="true"]{{background:#e3f2fd;border-color:#1565c0;color:#1565c0;}}
.toolbar-btn.clear-btn{{border-color:#ef9a9a;color:#c62828;}}
.toolbar-btn.clear-btn::after{{content:none;}}
.tb-count{{font-weight:700;}}
#search-input{{flex:1 1 220px;min-width:160px;min-height:44px;}}
.popover-backdrop{{display:none;position:fixed;inset:0;z-index:150;background:transparent;}}
.popover-backdrop:not([hidden]){{display:block;}}
/* [hidden] leunt normaal op de user-agent-stylesheet (display:none), maar
   die heeft een LAGERE specificiteit dan een eigen .popover{{display:flex}}
   -regel -- auteur-CSS wint dan van UA-CSS bij gelijke specificiteit, dus
   een 'gesloten' popover bleef gewoon zichtbaar (bevestigd door Michiel op
   echte Firefox, 2026-08-18 -- niet zichtbaar in de test-omgeving omdat
   screenshots daar niet werkten, alleen de hidden-property is gecheckt, niet
   de daadwerkelijke rendering). Nu expliciet zelf geregeld i.p.v. op de
   UA-standaard te vertrouwen: display:none is de default, display:flex
   alleen zonder [hidden]. */
.popover{{display:none;position:fixed;z-index:160;background:#fff;border:1px solid var(--border);border-radius:10px;
  box-shadow:0 8px 24px rgba(0,0,0,.18);padding:12px 14px;flex-wrap:wrap;gap:6px;
  align-items:center;max-width:min(92vw,480px);max-height:70vh;overflow-y:auto;}}
.popover:not([hidden]){{display:flex;}}
.popover-daterow{{display:flex;gap:6px;width:100%;}}
.popover-search{{width:100%;padding:6px 10px;border-radius:20px;border:1.5px solid #ccc;font-size:1rem;margin-bottom:4px;}}
.popover-search:focus{{outline:none;border-color:#1565c0;}}
.popover-src-list{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;width:100%;}}
.src-group-label{{font-size:0.72rem;font-weight:700;color:var(--muted);width:100%;margin:6px 0 0;text-transform:uppercase;letter-spacing:.03em;}}
.src-group-label:first-child{{margin-top:0;}}
.filters-label{{font-size:0.75rem;color:var(--muted);width:100%;margin-bottom:2px;}}
.btn{{padding:6px 12px;min-height:44px;border-radius:20px;border:1.5px solid #ccc;background:#fff;cursor:pointer;font-size:0.78rem;color:#555;transition:all .15s;white-space:nowrap;}}
.btn:hover{{opacity:.8;}}
.btn[data-src="all"].active,.btn[data-genre="all"].active,.btn[data-prov="all"].active,.btn[data-when="all"].active{{background:#555;color:#fff;border-color:#555;}}
.btn[data-sport="all"].active,.btn[data-club="all"].active{{background:#555;color:#fff;border-color:#555;}}
{sport_css}
{club_css}
{gender_css}
.btn[data-src]:not([data-src="all"]).active{{background:#1565c0;color:#fff;border-color:#1565c0;}}
{src_css_all}
{prov_css}
.btn[data-genre="festival"].active{{background:#e91e63;color:#fff;border-color:#e91e63;}}
.btn[data-genre="theater"].active{{background:#880e4f;color:#fff;border-color:#880e4f;}}
.btn[data-genre="cabaret"].active{{background:#e65100;color:#fff;border-color:#e65100;}}
.btn[data-genre="musical"].active{{background:#6a1b9a;color:#fff;border-color:#6a1b9a;}}
.btn[data-genre="klassiek"].active{{background:#283593;color:#fff;border-color:#283593;}}
.btn[data-genre="pop"].active{{background:#c62828;color:#fff;border-color:#c62828;}}
.btn[data-genre="jazz"].active{{background:#004d40;color:#fff;border-color:#004d40;}}
.btn[data-genre="dans"].active{{background:#bf360c;color:#fff;border-color:#bf360c;}}
.btn[data-genre="expo"].active{{background:#1b5e20;color:#fff;border-color:#1b5e20;}}
.btn[data-genre="actief"].active{{background:#006064;color:#fff;border-color:#006064;}}
.btn[data-genre="kinderen"].active{{background:#f57f17;color:#fff;border-color:#f57f17;}}
.btn[data-genre="overig"].active{{background:#555;color:#fff;border-color:#555;}}
.g-theater{{background:#fce4ec;color:#880e4f;}} .g-cabaret{{background:#fff3e0;color:#e65100;}}
.g-musical{{background:#f3e5f5;color:#6a1b9a;}} .g-klassiek{{background:#e8eaf6;color:#283593;}}
.g-pop{{background:#fce4ec;color:#c62828;}} .g-jazz{{background:#e0f2f1;color:#004d40;}}
.g-dans{{background:#fdf3e7;color:#bf360c;}} .g-expo{{background:#e8f5e9;color:#1b5e20;}}
.g-actief{{background:#e0f7fa;color:#006064;}} .g-kinderen{{background:#fff8e1;color:#f57f17;}}
.g-overig{{background:#f5f5f5;color:#555;}}
.addr-row{{display:flex;align-items:center;gap:6px;flex-wrap:wrap;width:100%;}}
.addr-row label{{font-size:0.78rem;color:var(--muted);white-space:nowrap;}}
#addr-input{{padding:4px 10px;border-radius:20px;border:1.5px solid #ccc;font-size:1rem;width:180px;}}
#addr-input:focus{{outline:none;border-color:#1565c0;}}
.icon-btn{{padding:4px 8px;border-radius:20px;border:1.5px solid #ccc;background:#fff;cursor:pointer;font-size:0.82rem;}}
.icon-btn:hover{{background:#f5f5f5;}}
.dist-buttons{{display:flex;align-items:center;gap:4px;flex-wrap:wrap;}}
.dist-btn{{padding:4px 10px;}}
#dist-custom-input{{padding:4px 10px;border-radius:20px;border:1.5px solid #ccc;font-size:1rem;width:80px;}}
#dist-custom-input:focus{{outline:none;border-color:#1565c0;}}
#dist-label{{font-size:0.78rem;color:var(--muted);font-weight:600;}}
#addr-status{{font-size:0.75rem;color:var(--muted);max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
.month-nav{{background:#fff;border-bottom:1px solid var(--border);padding:8px 16px;overflow-x:auto;white-space:nowrap;}}
.month-link{{display:inline-block;padding:3px 8px;margin-right:4px;border-radius:4px;text-decoration:none;color:var(--muted);font-size:0.78rem;background:#f5f5f5;}}
.month-link:hover{{background:#e0e0e0;}}
#stats{{background:#fff;padding:6px 16px;font-size:0.8rem;color:var(--muted);border-bottom:1px solid var(--border);}}
#empty-state{{margin:24px 16px;padding:20px;background:#fff;border:1px dashed var(--border);border-radius:8px;color:var(--muted);text-align:center;font-size:0.9rem;}}
.empty-action-btn{{margin:8px 4px 0;padding:8px 16px;min-height:44px;border-radius:20px;border:1.5px solid #1565c0;background:#fff;color:#1565c0;cursor:pointer;font-size:0.85rem;font-weight:600;}}
.empty-action-btn:hover{{background:#e3f2fd;}}
#empty-state.hidden{{display:none;}}
main{{padding:0 16px 32px;max-width:1000px;margin:0 auto;}}
.month-section{{margin-top:20px;}} .month-section.hidden{{display:none;}}
.day-group.hidden{{display:none;}}
.month-header{{font-size:1rem;font-weight:700;color:var(--muted);padding:8px 0 6px;border-bottom:1px solid var(--border);margin-bottom:8px;}}
.event{{background:var(--card);border-left:3px solid #ccc;border-radius:4px;padding:8px 10px;margin-bottom:6px;content-visibility:auto;contain-intrinsic-size:auto 50px;}}
.event.hidden{{display:none;}}
.day-header{{font-size:0.85rem;font-weight:700;color:var(--muted);padding:10px 0 4px;border-bottom:1px solid var(--border);margin:6px 0 6px;}}
.day-group:first-child .day-header{{margin-top:0;}}
.event-title{{display:flex;align-items:center;gap:6px;flex-wrap:wrap;}}
.event-title a{{color:var(--text);text-decoration:none;font-weight:600;font-size:1rem;}}
.event-daterange-inline{{font-size:0.72rem;color:#1565c0;font-weight:600;white-space:nowrap;}}
.event-title a:hover{{text-decoration:underline;color:#1565c0;}}
.event-venue{{font-size:0.75rem;color:var(--muted);margin-top:2px;}}
.event-daterange{{font-size:0.75rem;color:#1565c0;font-weight:600;margin-top:2px;}}
.event.expo-item{{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:start;}}
.btn[data-sort].active,.btn[data-when]:not([data-when="all"]).active,.btn[data-usort].active{{background:#1565c0;color:#fff;border-color:#1565c0;}}
.dist-badge{{font-size:0.72rem;color:var(--muted);margin-left:4px;}}
.event-badges{{display:flex;flex-direction:column;gap:3px;align-items:flex-end;}}
a:focus-visible,button:focus-visible,input:focus-visible{{outline:2px solid #1565c0;outline-offset:2px;}}
.badge{{font-size:0.68rem;padding:2px 6px;border-radius:10px;white-space:nowrap;}}
.badge-src{{font-weight:400;color:var(--muted);}}
#back-to-top{{position:fixed;bottom:20px;right:20px;width:44px;height:44px;border-radius:50%;background:#1565c0;color:#fff;border:none;font-size:1.2rem;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.25);z-index:200;}}
#back-to-top.hidden{{display:none;}}
#back-to-top:hover{{background:#0d47a1;}}
#search-input{{width:100%;padding:8px 12px;border-radius:20px;border:1.5px solid #ccc;font-size:1rem;}}
#search-input:focus{{outline:none;border-color:#1565c0;}}
#when-from,#when-to{{padding:4px 8px;border-radius:20px;border:1.5px solid #ccc;font-size:0.85rem;}}
#active-filters{{padding:6px 16px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;background:#fff;border-bottom:1px solid var(--border);}}
#active-filters.hidden{{display:none;}}
.filter-token{{display:inline-flex;align-items:center;gap:4px;background:#e3f2fd;color:#1565c0;border:1px solid #90caf9;border-radius:14px;padding:2px 4px 2px 10px;font-size:0.78rem;}}
.filter-token button{{background:none;border:none;color:#1565c0;cursor:pointer;font-size:1rem;line-height:1;padding:2px 6px;}}
.filter-token.clear-all{{background:#fce4ec;color:#c62828;border-color:#ef9a9a;cursor:pointer;padding:4px 12px;}}

@media(max-width:600px){{
  .addr-row{{flex-direction:column;align-items:stretch;}}
  .addr-row label{{margin-bottom:2px;}}
  #addr-input{{width:100%;}}
  .dist-buttons{{width:100%;}}
  .chip-scroll,.month-nav,.toolbar-buttons{{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;mask-image:linear-gradient(to right,transparent,black 12px,black calc(100% - 12px),transparent);-webkit-mask-image:linear-gradient(to right,transparent,black 12px,black calc(100% - 12px),transparent);}}
  .toolbar{{flex-direction:column;align-items:stretch;}}
  #search-input{{width:100%;}}
  .toolbar-buttons{{width:100%;}}
  .popover{{left:8px !important;right:8px;max-width:calc(100vw - 16px);width:calc(100vw - 16px);}}
  .topbar-top{{gap:8px;}}
}}
</style></head><body>
<div class="topbar" id="topbar">
  <div class="topbar-top">
    <h1>🗓️ Uitjes Agenda</h1>
    <div class="mode-toggle" role="group" aria-label="Weergave">
      <button class="mode-btn active" id="btn-uitjes" onclick="setMode('uitjes')">🗓️ Uitjes</button>
      <button class="mode-btn" id="btn-sport" onclick="setMode('sport')">⚽ Sport</button>
      <button class="mode-btn" id="btn-exposities" onclick="setMode('exposities')">🖼️ Exposities</button>
    </div>
  </div>
  <div class="meta">Bijgewerkt: {today_str} &nbsp;·&nbsp; {total} events &nbsp;·&nbsp; {expo_total} exposities &nbsp;·&nbsp; {len(active_sources)} bronnen</div>
  <div class="toolbar" id="toolbar">
    <input type="search" id="search-input" placeholder="🔍 Zoek op titel of locatie…" aria-label="Zoek op titel of locatie">
    <div class="toolbar-buttons" id="toolbar-buttons">
      <button class="toolbar-btn" id="tb-when" data-popover="popover-when" aria-haspopup="true" aria-expanded="false">Wanneer<span class="tb-count" id="tb-when-count"></span></button>
      <button class="toolbar-btn" id="tb-where" data-popover="popover-where" aria-haspopup="true" aria-expanded="false">Waar<span class="tb-count" id="tb-where-count"></span></button>
      <button class="toolbar-btn" id="tb-genre" data-popover="popover-genre" aria-haspopup="true" aria-expanded="false">Genre<span class="tb-count" id="tb-genre-count"></span></button>
      <button class="toolbar-btn" id="tb-src" data-popover="popover-src" aria-haspopup="true" aria-expanded="false">Bron<span class="tb-count" id="tb-src-count"></span></button>
      <button class="toolbar-btn" id="tb-sport" data-popover="popover-sport" aria-haspopup="true" aria-expanded="false">Sport<span class="tb-count" id="tb-sport-count"></span></button>
      <button class="toolbar-btn" id="tb-club" data-popover="popover-club" aria-haspopup="true" aria-expanded="false">Club<span class="tb-count" id="tb-club-count"></span></button>
      <button class="toolbar-btn" id="tb-sort" data-popover="popover-sort" aria-haspopup="true" aria-expanded="false">Sorteren</button>
      <button class="toolbar-btn clear-btn" id="clear-filters-btn">Wis filters</button>
    </div>
  </div>
</div>
<div class="popover-backdrop" id="popover-backdrop" hidden></div>

<div class="popover" id="popover-when" hidden role="group" aria-labelledby="lbl-datum">
  <div class="filters-label" id="lbl-datum">Wanneer</div>
  <button class="btn active" data-when="all">Alle</button>
  <button class="btn" data-when="today">Vandaag</button>
  <button class="btn" data-when="weekend">Dit weekend</button>
  <button class="btn" data-when="week">Deze week</button>
  <button class="btn" data-when="month">Deze maand</button>
  <div class="popover-daterow">
    <input type="date" id="when-from" aria-label="Vanaf datum" title="Eigen periode: vanaf">
    <input type="date" id="when-to" aria-label="Tot datum" title="Eigen periode: tot">
  </div>
</div>

<div class="popover" id="popover-where" hidden role="group" aria-labelledby="lbl-provincie">
  <div class="filters-label" id="lbl-provincie">Provincie &amp; afstand</div>
  {prov_buttons}
  <div class="addr-row">
    <label>Afstand van:</label>
    <input type="text" id="addr-input" list="nl-places" placeholder="adres of plaatsnaam" value="Annen, Drenthe">
    <datalist id="nl-places"><option value="Groningen"><option value="Assen"><option value="Emmen"><option value="Hoogeveen"><option value="Meppel"><option value="Coevorden"><option value="Borger"><option value="Stadskanaal"><option value="Veendam"><option value="Delfzijl"><option value="Leeuwarden"><option value="Sneek"><option value="Heerenveen"><option value="Drachten"><option value="Franeker"><option value="Harlingen"><option value="Dokkum"><option value="Joure"><option value="Zwolle"><option value="Deventer"><option value="Almelo"><option value="Hengelo"><option value="Enschede"><option value="Kampen"><option value="Hardenberg"><option value="Ommen"><option value="Utrecht"><option value="Amersfoort"><option value="Houten"><option value="Nieuwegein"><option value="Zeist"><option value="Woerden"><option value="Veenendaal"><option value="Amsterdam"><option value="Haarlem"><option value="Alkmaar"><option value="Den Helder"><option value="Purmerend"><option value="Zaandam"><option value="Hoorn"><option value="Hilversum"><option value="Amstelveen"><option value="Den Haag"><option value="Rotterdam"><option value="Leiden"><option value="Delft"><option value="Dordrecht"><option value="Gouda"><option value="Schiedam"><option value="Zoetermeer"><option value="Alphen aan den Rijn"><option value="Eindhoven"><option value="Tilburg"><option value="Den Bosch"><option value="Breda"><option value="Helmond"><option value="Roosendaal"><option value="Bergen op Zoom"><option value="Oss"><option value="Veghel"><option value="Nijmegen"><option value="Arnhem"><option value="Apeldoorn"><option value="Doetinchem"><option value="Harderwijk"><option value="Tiel"><option value="Wageningen"><option value="Winterswijk"><option value="Annen"><option value="Gieten"><option value="Tynaarlo"><option value="Beilen"><option value="Roden"><option value="Leek"><option value="Zuidlaren"><option value="Hoogezand"><option value="Winschoten"><option value="Dalen"><option value="Emmer-Compascuum"><option value="Nieuwe-Pekela"><option value="Ter Apel"><option value="Oosterhesselen"></datalist>
    <button class="icon-btn" id="addr-btn">🔍 Zoek</button>
    <button class="icon-btn" id="loc-btn" title="Gebruik mijn locatie">📍 Locatie</button>
    <div class="dist-buttons" id="dist-buttons" role="group" aria-label="Afstand">
      <button type="button" class="btn dist-btn" data-dist="10">10 km</button>
      <button type="button" class="btn dist-btn" data-dist="25">25 km</button>
      <button type="button" class="btn dist-btn" data-dist="50">50 km</button>
      <button type="button" class="btn dist-btn" data-dist="100">100 km</button>
      <button type="button" class="btn dist-btn active" data-dist="9999">Alle</button>
      <input type="number" id="dist-custom-input" placeholder="eigen km" min="1">
    </div>
    <span id="dist-label">Alle afstanden</span>
    <span id="addr-status">standaard: Annen</span>
  </div>
</div>

<div class="popover" id="popover-genre" hidden role="group" aria-labelledby="lbl-genre">
  <div class="filters-label" id="lbl-genre">Genre</div>
  <button class="btn active" data-genre="all">Alle genres</button>
  <button class="btn" data-genre="festival">🎉 Festival</button>
  <button class="btn" data-genre="theater">🎭 Theater</button>
  <button class="btn" data-genre="cabaret">🎪 Cabaret</button>
  <button class="btn" data-genre="musical">🎼 Musical</button>
  <button class="btn" data-genre="klassiek">🎻 Klassiek</button>
  <button class="btn" data-genre="pop">🎸 Pop / Rock</button>
  <button class="btn" data-genre="jazz">🎷 Jazz / Blues</button>
  <button class="btn" data-genre="dans">💃 Dans</button>
  <button class="btn" data-genre="actief">🥾 Actief</button>
  <button class="btn" data-genre="kinderen">🎈 Kinderen</button>
  <button class="btn" data-genre="overig">• Overig</button>
</div>

<div class="popover popover-src" id="popover-src" hidden role="group" aria-labelledby="lbl-bron">
  <div class="filters-label" id="lbl-bron">Bron</div>
  <input type="text" id="src-search" placeholder="Zoek bron…" class="popover-search" aria-label="Zoek bron">
  <div class="popover-src-list" id="popover-src-list">
  {src_buttons}
  </div>
</div>

<div class="popover" id="popover-sport" hidden>
  <div class="filters-label" id="lbl-sport">Sport</div>
  <button class="btn active" data-sport="all">Alle sporten</button>
  <button class="btn" data-sport="voetbal">⚽ Voetbal</button>
  <button class="btn" data-sport="basketbal">🏀 Basketbal</button>
  <button class="btn" data-sport="volleybal">🏐 Volleybal</button>
  <button class="btn" data-sport="ijshockey">🏒 IJshockey</button>
  <button class="btn" data-sport="handbal">🤾 Handbal</button>
  <button class="btn" data-sport="korfbal">🎯 Korfbal</button>
  <div class="filters-label" id="lbl-geslacht">Geslacht</div>
  <button class="btn active" data-gender="all">Beide</button>
  <button class="btn" data-gender="heren">♂ Heren</button>
  <button class="btn" data-gender="dames">♀ Dames</button>
</div>

<div class="popover" id="popover-club" hidden role="group" aria-labelledby="lbl-club">
  <div class="filters-label" id="lbl-club">Club</div>
  <button class="btn active" data-club="all">Alle clubs</button>
  <button class="btn" data-club="fcgroningen" data-sport-type="voetbal">⚽ FC Groningen</button>
  <button class="btn" data-club="fcemmen" data-sport-type="voetbal">⚽ FC Emmen</button>
  <button class="btn" data-club="heerenveen" data-sport-type="voetbal">⚽ SC Heerenveen</button>
  <button class="btn" data-club="cambuur" data-sport-type="voetbal">⚽ SC Cambuur</button>
  <button class="btn" data-club="fctwente" data-sport-type="voetbal">⚽ FC Twente</button>
  <button class="btn" data-club="goahead" data-sport-type="voetbal">⚽ Go Ahead Eagles</button>
  <button class="btn" data-club="peczwolle" data-sport-type="voetbal">⚽ PEC Zwolle</button>
  <button class="btn" data-club="donar" data-sport-type="basketbal">🏀 Donar</button>
  <button class="btn" data-club="landstede" data-sport-type="basketbal">🏀 Landstede</button>
  <button class="btn" data-club="lycurgus" data-sport-type="volleybal">🏐 Lycurgus</button>
  <button class="btn" data-club="sudosa" data-sport-type="volleybal">🏐 CRAFT Sudosa</button>
  <button class="btn" data-club="friso" data-sport-type="volleybal">🏐 Friso Sneek</button>
  <button class="btn" data-club="grizzlys" data-sport-type="ijshockey">🏒 GIJS</button>
  <button class="btn" data-club="flyers" data-sport-type="ijshockey">🏒 Flyers</button>
  <button class="btn" data-club="ogcapitals" data-sport-type="ijshockey">🏒 OG Capitals</button>
  <button class="btn" data-club="hurryup" data-sport-type="handbal">🤾 Hurry-Up</button>
  <button class="btn" data-club="eoemmen" data-sport-type="handbal">🤾 E&amp;O Emmen</button>
  <button class="btn" data-club="ldodk" data-sport-type="korfbal">🎯 LDODK</button>
  <button class="btn" data-club="dos46" data-sport-type="korfbal">🎯 DOS '46</button>
</div>

<div class="popover" id="popover-sort" hidden>
  <div class="filters" id="uitjes-sort" role="group" aria-labelledby="lbl-usort" style="border:none;padding:0;">
    <div class="filters-label" id="lbl-usort">Sorteren</div>
    <button class="btn active" data-usort="datum">Datum</button>
    <button class="btn" data-usort="afstand">Afstand</button>
  </div>
  <div class="filters" id="expo-filters" style="display:none;border:none;padding:0;" role="group" aria-labelledby="lbl-sorteren">
    <div class="filters-label" id="lbl-sorteren">Sorteren (Exposities)</div>
    <button class="btn active" data-sort="start">Startdatum</button>
    <button class="btn" data-sort="end">Einddatum</button>
    <button class="btn" data-sort="alpha">Alfabetisch</button>
  </div>
</div>

<div id="active-filters" class="hidden"></div>
<div class="month-nav" id="month-nav-wrap">{month_nav}</div>
<div id="stats">Toont alle {total_uitjes} uitjes</div>
<div id="empty-state" class="hidden"></div>
<main>{main_html}</main>
<div id="expo-wrap" style="display:none;padding:0 16px 32px;">{expo_html}</div>
<button id="back-to-top" class="hidden" title="Naar boven" aria-label="Naar boven" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">&uarr;</button>
<script>{js}</script>
<footer style="margin-top:32px;padding:16px;font-size:0.72rem;color:var(--muted);border-top:1px solid #e0e0e0;line-height:1.6;">
  Uitjes Agenda is een onafhankelijke verzamelagenda. We tonen alleen beperkte feitelijke informatie zoals titel, datum, locatie en bron, met een link naar de oorspronkelijke aanbieder. Voor actuele informatie, tickets, wijzigingen en voorwaarden verwijzen we altijd naar de officiële website van de organisator of locatie. Bent u rechthebbende of organisator en wilt u een event of bron laten aanpassen of verwijderen? Neem contact op via <a href="mailto:chielemans@hotmail.com" style="color:var(--muted);">chielemans@hotmail.com</a>
</footer>
</body></html>'''

with open(HTML_OUT,'w',encoding='utf-8') as f:
    f.write(html)
print(f"HTML: {len(html):,} bytes | {total} events")
