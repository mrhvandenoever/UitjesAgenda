"""
fix_gen2.py — voeg Festival toe als genre + toon stad op eventkaart
Run: python fix_gen2.py  (daarna python gen_uitjes.py)
"""
f = open('gen_uitjes.py', encoding='utf-8').read()

# ── 1. classify(): festival-return vóór de pop-check ─────────────────────────
old1 = ("    if any(w in t for w in ['rock','indie','punk','metal','concert','band','tribute',\n"
        "                             'singer','songwriter','coverband','techno','house',\n"
        "                             'hiphop','rap','hardrock','hardcore']): return 'pop'")
new1 = ("    if any(w in t for w in ['festival','feest','kermis','volksfeest','volksvermaak',\n"
        "                             'sneekweek','lemsterwike','ballonfeesten','koningsdag',\n"
        "                             'bevrijdingsdag','havenfeest','straatfestival',\n"
        "                             'carnaval','folklorisch']): return 'festival'\n"
        "    if any(w in t for w in ['rock','indie','punk','metal','concert','band','tribute',\n"
        "                             'singer','songwriter','coverband','techno','house',\n"
        "                             'hiphop','rap','hardrock','hardcore']): return 'pop'")
assert old1 in f, "classify() anchor niet gevonden!"
f = f.replace(old1, new1, 1)
print("fix 1 (classify festival): OK")

# ── 2. icon_map: voeg festival toe ───────────────────────────────────────────
old2 = "    icon_map = {'theater':'\U0001f3ad','cabaret':'\U0001f3aa','musical':'\U0001f3bc','klassiek':'\U0001f3bb','pop':'\U0001f3b8',"
new2 = "    icon_map = {'festival':'\U0001f389','theater':'\U0001f3ad','cabaret':'\U0001f3aa','musical':'\U0001f3bc','klassiek':'\U0001f3bb','pop':'\U0001f3b8',"
assert old2 in f, "icon_map anchor niet gevonden!"
f = f.replace(old2, new2, 1)
print("fix 2 (icon_map): OK")

# ── 3. glabel_map: voeg festival toe ─────────────────────────────────────────
old3 = "    glabel_map = {'theater':'Theater / Toneel','cabaret':'Cabaret / Comedy','musical':'Musical',"
new3 = "    glabel_map = {'festival':'Festival / Evenement','theater':'Theater / Toneel','cabaret':'Cabaret / Comedy','musical':'Musical',"
assert old3 in f, "glabel_map anchor niet gevonden!"
f = f.replace(old3, new3, 1)
print("fix 3 (glabel_map): OK")

# ── 4. CSS: festival knopkleur ────────────────────────────────────────────────
old4 = ".btn[data-genre=\"theater\"].active{{background:#880e4f;color:#fff;border-color:#880e4f;}}"
new4 = (".btn[data-genre=\"festival\"].active{{background:#e91e63;color:#fff;border-color:#e91e63;}}\n"
        ".btn[data-genre=\"theater\"].active{{background:#880e4f;color:#fff;border-color:#880e4f;}}")
assert old4 in f, "CSS genre anchor niet gevonden!"
f = f.replace(old4, new4, 1)
print("fix 4 (CSS): OK")

# ── 5. HTML genre-knopje ──────────────────────────────────────────────────────
old5 = '  <button class="btn" data-genre="theater">\U0001f3ad Theater</button>'
new5 = ('  <button class="btn" data-genre="festival">\U0001f389 Festival</button>\n'
        '  <button class="btn" data-genre="theater">\U0001f3ad Theater</button>')
assert old5 in f, "HTML genre-knop anchor niet gevonden!"
f = f.replace(old5, new5, 1)
print("fix 5 (HTML knop): OK")

# ── 6. Toon stad op eventkaart ────────────────────────────────────────────────
old6 = "            f'<div class=\"event-venue\">{esc(e.get(\"venue\",\"\"))} '"
new6 = "            f'<div class=\"event-venue\">{esc(e.get(\"venue\",\"\") or e.get(\"city\",\"\"))} '"
assert old6 in f, "event-venue anchor niet gevonden!"
f = f.replace(old6, new6, 1)
print("fix 6 (stad op kaart): OK")

open('gen_uitjes.py', 'w', encoding='utf-8').write(f)
print("\nKlaar. Run nu: python gen_uitjes.py")
