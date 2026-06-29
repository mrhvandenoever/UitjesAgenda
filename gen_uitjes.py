# gen_uitjes.py - Uitjes Agenda builder
# Gebruik: python gen_uitjes.py
# Output: uitjes_agenda.html (naast dit script)
import os, sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EVENTS_JSON = os.path.join(SCRIPT_DIR, 'events_categorized.json')
HTML_OUT = os.path.join(SCRIPT_DIR, 'index.html')

import json, re as _re, math
from datetime import date
TODAY = date.today().isoformat()
from collections import defaultdict

with open(EVENTS_JSON) as f:
    events = json.load(f)

SRC = {
    'spotgroningen.nl':    ('Spot',            '🔴', '#e53935'),
    'lawei':               ('De Lawei',        '🎶', '#6d4c41'),
    'atlastheater':        ('Atlas Emmen',     '🟡', '#f57f17'),
    'drenthe.nl':          ('Drenthe',         '🟢', '#2e7d32'),
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
    'kielzog':              (52.7235, 6.4754, 'Drenthe'),
    'denieuwekolk.nl':      (52.9953, 6.5625, 'Drenthe'),
    'detamboer':            (52.7235, 6.4754, 'Drenthe'),
    'theaterroden':         (53.1390, 6.4344, 'Drenthe'),
    'zummerbuhne':          (52.8500, 6.7500, 'Drenthe'),
    'drentsmuseum':         (52.9963, 6.5640, 'Drenthe'),
    'podiumzuidhaege':      (52.9930, 6.5580, 'Drenthe'),
    'hunebedcentrum':       (52.9236, 6.7904, 'Drenthe'),
    'gekehoogstins.nl':     (53.0083, 6.7683, 'Drenthe'),
    'dorpshuisannen':       (53.0340, 6.7350, 'Drenthe'),
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
}

MUSIC_VENUES  = {'vera','simplon','em2groningen','spotgroningen.nl','grandcafe_zuidlaren',
                 'kielzog','machinefabriek','usva','detamboer','neushoorn',
                 'tivolivredenburg','melkweg','paradiso','013','ziggodome','effenaar','doornroosje','ahoy','paard'}
THEATER_VENUES= {'lawei','atlastheater','denieuwekolk.nl','vanberesteyn','theaterroden','geertteis',
                 'grandtheatregroningen','martiniplaza','dorpshuisannen','podiumnienoordleek',
                 'zummerbuhne','posthuistheater','ontdekpoort','koornbeurs'}
EXPO_VENUES   = {'groningermuseum','drentsmuseum','hunebedcentrum'}

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
               'familie':'kinderen','kinderen':'kinderen'}
    for c in cats:
        if c == 'expositie':
            if any(w in t for w in ['expositie','tentoonstelling','galerie','expo','schilderij',
                                     'architect','design','kunst','biennale','poppenhuis',
                                     'marilyn','storyworld','strip','botanisch']):
                return 'expo'
        elif c in cat_map:
            return cat_map[c]
    if source in EXPO_VENUES: return 'expo'
    if 'musical' in t: return 'musical'
    if any(w in t for w in ['cabaret','comedy','stand-up','humor']): return 'cabaret'
    if any(w in t for w in ['ballet','dans ','choreograf','dansavond']): return 'dans'
    if any(w in t for w in ['orkest','symfon','opera','klassiek','kwartet','quartet',
                             'piano','viool','cello','strijk','filharmonisch','dirigent',
                             'ensemble','trio','kamer','recital']): return 'klassiek'
    if any(w in t for w in ['jazz','blues','soul','swing','funk','bossa','reggae']): return 'jazz'
    if any(w in t for w in ['expositie','tentoonstelling','galerie','biënnale','biennale',
                             'storyworld','strip','marilyn']): return 'expo'
    if any(w in t for w in [' theater',' toneel','toneelstuk','voorstelling']): return 'theater'
    if any(w in t for w in ['rock','indie','punk','metal','concert','band','tribute',
                             'singer','songwriter','coverband','festival','techno','house',
                             'hiphop','rap','hardrock','hardcore']): return 'pop'
    if any(w in t for w in ['wandeling','safari','natuur','strunen','stenen zoeken']): return 'actief'
    if source in MUSIC_VENUES:   return 'pop'
    if source in THEATER_VENUES: return 'theater'
    return 'overig'

NL_DAYS   = ['ma','di','wo','do','vr','za','zo']
NL_MONTHS = ['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec']
NL_MONTHS_LONG = ['Januari','Februari','Maart','April','Mei','Juni',
                  'Juli','Augustus','September','Oktober','November','December']

def fmt_date(iso):
    try: d=date.fromisoformat(iso); return f"{NL_DAYS[d.weekday()]} {d.day} {NL_MONTHS[d.month-1]}"
    except: return iso
def month_id(iso):    return 'm'+iso[:7].replace('-','')
def month_label(iso):
    try: y,m=int(iso[:4]),int(iso[5:7]); return f"{NL_MONTHS_LONG[m-1]} {y}"
    except: return iso[:7]
def month_short(iso):
    try: y,m=int(iso[:4]),int(iso[5:7]); return f"{NL_MONTHS[m-1].capitalize()} '{str(y)[2:]}"
    except: return iso[:7]
def safe_key(k): return k.replace('.','_').replace('-','_')
def esc(s):      return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

events_valid = sorted([e for e in events if TODAY<=e.get('date','')<='2027-12-31'],
                      key=lambda e: e.get('date',''))
total = len(events_valid)
by_month = defaultdict(list)
for e in events_valid: by_month[e['date'][:7]].append(e)
months_sorted = sorted(by_month.keys())

css_vars = '\n'.join(f'  --{safe_key(k)}:{v[2]};' for k,v in SRC.items())

def src_css(key):
    sk=safe_key(key); c=SRC.get(key,('','','#999'))[2]
    return (f'.btn[data-src="{key}"]{{border-color:{c};color:{c};}}'
            f'.btn[data-src="{key}"].active{{background:{c};color:#fff;border-color:{c};}}'
            f'.event.{sk}{{border-left-color:{c};}}'
            f'.s-{sk}{{background:{c}22;color:{c};border:1px solid {c}44;}}')

src_css_all = '\n'.join(src_css(k) for k in SRC)
active_sources = sorted(set(e['source'] for e in events_valid))

LANDELIJK = {'tivolivredenburg','melkweg','paradiso','013','ziggodome','effenaar','doornroosje','ahoy'}
src_buttons = '<button class="btn active" data-src="all">Alle bronnen</button>\n'
src_buttons += '  <button class="btn" data-src-group="landelijk" style="border-color:#c62828;color:#c62828;">🗺️ Landelijk</button>\n'
for key in active_sources:
    label,emoji,_ = SRC.get(key,(key,'•','#999'))
    src_buttons += f'  <button class="btn" data-src="{key}">{emoji} {esc(label)}</button>\n'

month_nav = '\n'.join(
    f'<a href="#{month_id(m+"-01")}" class="month-link">{month_short(m+"-01")}</a>'
    for m in months_sorted)

def event_html(e):
    src = e.get('source',''); sk = safe_key(src)
    genre = classify(e.get('title',''), e.get('cats',[]), src)
    icon_map = {'theater':'🎭','cabaret':'🎪','musical':'🎼','klassiek':'🎻','pop':'🎸',
                'jazz':'🎷','dans':'💃','expo':'🖼️','actief':'🥾','kinderen':'🎈','overig':'•'}
    glabel_map = {'theater':'Theater / Toneel','cabaret':'Cabaret / Comedy','musical':'Musical',
                  'klassiek':'Klassiek / Opera','pop':'Pop / Rock','jazz':'Jazz / Blues',
                  'dans':'Dans / Ballet','expo':'Expo / Kunst','actief':'Actief / Natuur',
                  'kinderen':'Kinderen / Familie','overig':'Overig'}
    icon = icon_map.get(genre,'•'); glabel = glabel_map.get(genre,'Overig')
    title_html = (f'<a href="{esc(e.get("url",""))}" target="_blank">{esc(e.get("title",""))}</a>'
                  if e.get('url') else esc(e.get('title','')))
    loc = VENUE_LOC.get(src)
    prov = loc[2] if loc else 'Onbekend'
    lat_lon = f'{loc[0]},{loc[1]}' if loc else ''
    return (f'<div class="event {sk}" data-src="{src}" data-genre="{genre}" '
            f'data-prov="{prov}" data-latlon="{lat_lon}">'
            f'<div class="event-date">{fmt_date(e.get("date",""))}</div>'
            f'<div class="event-main"><div class="event-title">{title_html}</div>'
            f'<div class="event-venue">{esc(e.get("venue",""))} '
            f'<span class="dist-badge"></span></div></div>'
            f'<div class="event-badges">'
            f'<span class="badge badge-genre g-{genre}">{icon} {glabel}</span>'
            f'<span class="badge badge-src s-{sk}">{esc(SRC.get(src,(src,"",""))[0])}</span>'
            f'</div></div>')

main_html = ''.join(
    f'<div class="month-section" id="{month_id(m+"-01")}"><h2 class="month-header">{month_label(m+"-01")}</h2>\n'
    + ''.join(event_html(e)+'\n' for e in by_month[m])
    + '</div>\n'
    for m in months_sorted)

today_str = date.today().strftime('%-d %B %Y')

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
    prov_buttons += f'  <button class="btn" data-prov="{p}" style="border-color:{c};color:{c};">{p}</button>\n'
prov_css = '\n'.join(
    f'.btn[data-prov="{p}"].active{{background:{prov_colors[p]};color:#fff;border-color:{prov_colors[p]};}}'
    for p in provs)

import json as _json
landelijk_json = _json.dumps(sorted(LANDELIJK))

js = f'''
const TOTAL={total};
let selSrc=new Set(), selGenre=new Set(), selProv=new Set(), maxDist=9999;
let centerLat=53.034, centerLon=6.735;

function haversine(lat1,lon1,lat2,lon2){{
  const R=6371, dLat=(lat2-lat1)*Math.PI/180, dLon=(lon2-lon1)*Math.PI/180;
  const a=Math.sin(dLat/2)**2+Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
  return Math.round(R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a)));
}}

function updateDistances(){{
  document.querySelectorAll('.event[data-latlon]').forEach(ev=>{{
    const ll=ev.dataset.latlon;
    if(!ll)return;
    const [lat,lon]=ll.split(',').map(Number);
    const d=haversine(centerLat,centerLon,lat,lon);
    ev.dataset.dist=d;
    const b=ev.querySelector('.dist-badge');
    if(b)b.textContent='~'+d+'km';
  }});
}}

function apply(){{
  let v=0;
  document.querySelectorAll('.event').forEach(ev=>{{
    const dist=parseInt(ev.dataset.dist||9999);
    const ok=
      (selSrc.size===0  || selSrc.has(ev.dataset.src))  &&
      (selGenre.size===0|| selGenre.has(ev.dataset.genre)) &&
      (selProv.size===0 || selProv.has(ev.dataset.prov)) &&
      dist<=maxDist;
    ev.classList.toggle('hidden',!ok); if(ok)v++;
  }});
  document.querySelectorAll('.month-section').forEach(s=>{{
    s.classList.toggle('hidden',s.querySelectorAll('.event:not(.hidden)').length===0);
  }});
  document.getElementById('stats').textContent=
    v===TOTAL?'Toont alle '+TOTAL+' events':'Toont '+v+' van '+TOTAL+' events';
  document.querySelector('.btn[data-src="all"]').classList.toggle('active',selSrc.size===0);
  document.querySelector('.btn[data-genre="all"]').classList.toggle('active',selGenre.size===0);
  document.querySelector('.btn[data-prov="all"]').classList.toggle('active',selProv.size===0);
  const lbl=maxDist>=9999?'Alle afstanden':'≤ '+maxDist+' km';
  document.getElementById('dist-label').textContent=lbl;
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

document.getElementById('dist-slider').addEventListener('input',function(){{
  const steps=[25,50,75,100,9999];
  maxDist=steps[parseInt(this.value)];
  apply();
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
  document.querySelectorAll('.btn[data-prov]:not([data-prov="all"])').forEach(x=>x.classList.toggle('active',selProv.has(x.dataset.prov)));
  apply();
}}));

// Init: zet afstanden vanuit standaard centrum (Annen)
updateDistances();
'''

html = f'''<!DOCTYPE html>
<html lang="nl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Uitjes Agenda</title>
<style>
:root{{{css_vars}
  --bg:#f9f9f9;--card:#fff;--border:#e0e0e0;--text:#212121;--muted:#757575;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:14px;}}
header{{background:#fff;border-bottom:2px solid var(--border);padding:12px 16px;position:sticky;top:0;z-index:100;}}
header h1{{font-size:1.2rem;font-weight:700;margin-bottom:2px;}}
.meta{{font-size:0.8rem;color:var(--muted);}}
.filters{{background:#fff;border-bottom:1px solid var(--border);padding:8px 16px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;}}
.filters-label{{font-size:0.75rem;color:var(--muted);width:100%;margin-bottom:2px;}}
.btn{{padding:4px 10px;border-radius:20px;border:1.5px solid #ccc;background:#fff;cursor:pointer;font-size:0.78rem;color:#555;transition:all .15s;white-space:nowrap;}}
.btn:hover{{opacity:.8;}}
.btn[data-src="all"].active,.btn[data-genre="all"].active,.btn[data-prov="all"].active{{background:#555;color:#fff;border-color:#555;}}
{src_css_all}
{prov_css}
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
#addr-input{{padding:4px 10px;border-radius:20px;border:1.5px solid #ccc;font-size:0.78rem;width:180px;}}
#addr-input:focus{{outline:none;border-color:#1565c0;}}
.icon-btn{{padding:4px 8px;border-radius:20px;border:1.5px solid #ccc;background:#fff;cursor:pointer;font-size:0.82rem;}}
.icon-btn:hover{{background:#f5f5f5;}}
.dist-slider-wrap{{display:flex;align-items:center;gap:6px;}}
#dist-slider{{width:100px;accent-color:#1565c0;cursor:pointer;}}
#dist-label{{font-size:0.78rem;color:#1565c0;font-weight:600;min-width:110px;}}
#addr-status{{font-size:0.75rem;color:var(--muted);max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
.month-nav{{background:#fff;border-bottom:1px solid var(--border);padding:8px 16px;overflow-x:auto;white-space:nowrap;}}
.month-link{{display:inline-block;padding:3px 8px;margin-right:4px;border-radius:4px;text-decoration:none;color:var(--muted);font-size:0.78rem;background:#f5f5f5;}}
.month-link:hover{{background:#e0e0e0;}}
#stats{{background:#fff;padding:6px 16px;font-size:0.8rem;color:var(--muted);border-bottom:1px solid var(--border);}}
main{{padding:0 16px 32px;}}
.month-section{{margin-top:20px;}} .month-section.hidden{{display:none;}}
.month-header{{font-size:1rem;font-weight:700;color:var(--muted);padding:8px 0 6px;border-bottom:1px solid var(--border);margin-bottom:8px;}}
.event{{background:var(--card);border-left:3px solid #ccc;border-radius:4px;padding:8px 10px;margin-bottom:6px;display:grid;grid-template-columns:70px 1fr auto;gap:8px;align-items:start;}}
.event.hidden{{display:none;}}
.event-date{{font-size:0.78rem;color:var(--muted);font-weight:600;padding-top:2px;}}
.event-title a{{color:#1565c0;text-decoration:none;font-weight:500;}}
.event-title a:hover{{text-decoration:underline;}}
.event-venue{{font-size:0.75rem;color:var(--muted);margin-top:2px;}}
.dist-badge{{font-size:0.68rem;color:#aaa;margin-left:4px;}}
.event-badges{{display:flex;flex-direction:column;gap:3px;align-items:flex-end;}}
.badge{{font-size:0.68rem;padding:2px 6px;border-radius:10px;white-space:nowrap;}}
.badge-src{{font-weight:600;}}
@media(max-width:600px){{
  .event{{grid-template-columns:60px 1fr;}}
  .event-badges{{grid-column:1/-1;flex-direction:row;flex-wrap:wrap;justify-content:flex-start;}}
}}
</style></head><body>
<header>
  <h1>🗓️ Uitjes Agenda</h1>
  <div class="meta">Bijgewerkt: {today_str} &nbsp;·&nbsp; {total} events &nbsp;·&nbsp; {len(active_sources)} bronnen</div>
</header>
<div class="filters">
  <div class="filters-label">Provincie &amp; afstand</div>
  {prov_buttons}
  <div class="addr-row">
    <label>Afstand van:</label>
    <input type="text" id="addr-input" list="nl-places" placeholder="adres of plaatsnaam" value="Annen, Drenthe">
    <datalist id="nl-places"><option value="Groningen"><option value="Assen"><option value="Emmen"><option value="Hoogeveen"><option value="Meppel"><option value="Coevorden"><option value="Borger"><option value="Stadskanaal"><option value="Veendam"><option value="Delfzijl"><option value="Leeuwarden"><option value="Sneek"><option value="Heerenveen"><option value="Drachten"><option value="Franeker"><option value="Harlingen"><option value="Dokkum"><option value="Joure"><option value="Zwolle"><option value="Deventer"><option value="Almelo"><option value="Hengelo"><option value="Enschede"><option value="Kampen"><option value="Hardenberg"><option value="Ommen"><option value="Utrecht"><option value="Amersfoort"><option value="Houten"><option value="Nieuwegein"><option value="Zeist"><option value="Woerden"><option value="Veenendaal"><option value="Amsterdam"><option value="Haarlem"><option value="Alkmaar"><option value="Den Helder"><option value="Purmerend"><option value="Zaandam"><option value="Hoorn"><option value="Hilversum"><option value="Amstelveen"><option value="Den Haag"><option value="Rotterdam"><option value="Leiden"><option value="Delft"><option value="Dordrecht"><option value="Gouda"><option value="Schiedam"><option value="Zoetermeer"><option value="Alphen aan den Rijn"><option value="Eindhoven"><option value="Tilburg"><option value="Den Bosch"><option value="Breda"><option value="Helmond"><option value="Roosendaal"><option value="Bergen op Zoom"><option value="Oss"><option value="Veghel"><option value="Nijmegen"><option value="Arnhem"><option value="Apeldoorn"><option value="Doetinchem"><option value="Harderwijk"><option value="Tiel"><option value="Wageningen"><option value="Winterswijk"><option value="Annen"><option value="Gieten"><option value="Tynaarlo"><option value="Beilen"><option value="Roden"><option value="Leek"><option value="Zuidlaren"><option value="Hoogezand"><option value="Winschoten"><option value="Dalen"><option value="Emmer-Compascuum"><option value="Nieuwe-Pekela"><option value="Ter Apel"><option value="Oosterhesselen"></datalist>
    <button class="icon-btn" id="addr-btn">🔍 Zoek</button>
    <button class="icon-btn" id="loc-btn" title="Gebruik mijn locatie">📍 Locatie</button>
    <div class="dist-slider-wrap">
      <input type="range" id="dist-slider" min="0" max="4" step="1" value="4">
      <span id="dist-label">Alle afstanden</span>
    </div>
    <span id="addr-status">standaard: Annen</span>
  </div>
</div>
<div class="filters">
  <div class="filters-label">Genre</div>
  <button class="btn active" data-genre="all">Alle genres</button>
  <button class="btn" data-genre="theater">🎭 Theater</button>
  <button class="btn" data-genre="cabaret">🎪 Cabaret</button>
  <button class="btn" data-genre="musical">🎼 Musical</button>
  <button class="btn" data-genre="klassiek">🎻 Klassiek</button>
  <button class="btn" data-genre="pop">🎸 Pop / Rock</button>
  <button class="btn" data-genre="jazz">🎷 Jazz</button>
  <button class="btn" data-genre="dans">💃 Dans</button>
  <button class="btn" data-genre="expo">🖼️ Expo</button>
  <button class="btn" data-genre="actief">🥾 Actief</button>
  <button class="btn" data-genre="kinderen">🎈 Kinderen</button>
  <button class="btn" data-genre="overig">• Overig</button>
</div>
<div class="filters">
  <div class="filters-label">Bron</div>
  {src_buttons}
</div>
<div class="month-nav">{month_nav}</div>
<div id="stats">Toont alle {total} events</div>
<main>{main_html}</main>
<script>{js}</script>
</body></html>'''

with open(HTML_OUT,'w',encoding='utf-8') as f:
    f.write(html)
print(f"HTML: {len(html):,} bytes | {total} events")
