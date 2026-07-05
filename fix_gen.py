"""Fix gen_uitjes.py: voeg visitgroningen + friesland.nl toe aan SRC en VENUE_LOC."""
f = open('gen_uitjes.py', encoding='utf-8').read()

# 1. SRC dict
old = "    'drenthe.nl':          ('Drenthe',         '\U0001f7e2', '#2e7d32'),"
new = (
    "    'drenthe.nl':          ('Drenthe',         '\U0001f7e2', '#2e7d32'),\n"
    "    'visitgroningen':      ('Visitgroningen',  '\U0001f7e3', '#6a1b9a'),\n"
    "    'friesland.nl':        ('Friesland',       '\U0001f535', '#0277bd'),"
)
assert old in f, "SRC-anchor niet gevonden!"
f = f.replace(old, new, 1)

# 2. VENUE_LOC
old2 = "    'drenthe.nl':           (52.9953, 6.5625, 'Drenthe'),"
new2 = (
    "    'drenthe.nl':           (52.9953, 6.5625, 'Drenthe'),\n"
    "    'visitgroningen':       (53.2194, 6.5665, 'Groningen'),\n"
    "    'friesland.nl':         (53.2012, 5.8036, 'Friesland'),"
)
assert old2 in f, "VENUE_LOC-anchor niet gevonden!"
f = f.replace(old2, new2, 1)

# 3. Haal 'festival' uit de pop-keywords (zodat festivals niet als pop worden gelabeld)
old3 = ("'rock','indie','punk','metal','concert','band','tribute',\n"
        "                             'singer','songwriter','coverband','festival','techno','house',")
new3 = ("'rock','indie','punk','metal','concert','band','tribute',\n"
        "                             'singer','songwriter','coverband','techno','house',")
if old3 in f:
    f = f.replace(old3, new3, 1)
    print("fix 3 (festival uit pop): OK")
else:
    print("fix 3: niet gevonden, skip")

open('gen_uitjes.py', 'w', encoding='utf-8').write(f)
print("Klaar. Run nu: python gen_uitjes.py")
