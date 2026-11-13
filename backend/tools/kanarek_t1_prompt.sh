#!/usr/bin/env bash
# Kanarek 1 (T1, 2026-10-20): czy system_prompt z Amnezji jest identyczny przed i po deployu.
# Uruchamiane NA VPS:  bash kanarek_t1_prompt.sh przed   |   bash kanarek_t1_prompt.sh po
# DRY (generate=false): zero Gemini, zero zapisu. Sekrety tylko ze zmiennych, nigdy w wyjściu.
set -euo pipefail
ETAP="${1:?podaj: przed albo po}"
DIR=/tmp/t1_kanarek
mkdir -p "$DIR/$ETAP"
cd /var/www/myastra/astra/backend
set -a; . ./.env; set +a

python3 - "$DIR" "$ETAP" <<'PY'
import base64, json, os, re, sys, urllib.parse, urllib.request
d, etap = sys.argv[1], sys.argv[2]
ZAPYTANIA = [
    ("astra", "kiedy mam operację"), ("astra", "co u ciebie słychać"), ("astra", "pamiętasz LDI?"),
    ("holo", "co robimy dziś wieczorem"), ("menma", "hej, wróciłem"), ("nazuna", "jak się masz, ziomek"),
]
u, p = os.getenv("DEBUG_USER"), os.getenv("DEBUG_PASS")
hdr = {"Authorization": "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()} if u and p else {}
# Czas w prompcie (godzina, data, "X min temu") zmienia się między przebiegami — maskujemy cyfry
# w tych formach, reszta tekstu musi zgadzać się co do znaku.
def maska(s):
    s = re.sub(r"\d{4}-\d{2}-\d{2}[T ]?[\d:.]*", "<DATA>", s)
    s = re.sub(r"\d{1,2}[:.]\d{2}(:\d{2})?", "<GODZ>", s)
    s = re.sub(r"\d{1,2}\.\d{1,2}\.\d{4}", "<DATA>", s)
    return s
wynik_ok = True
for i, (persona, q) in enumerate(ZAPYTANIA):
    url = "http://127.0.0.1:8001/api/debug/inspect?" + urllib.parse.urlencode({"query": q, "persona": persona})
    with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=120) as r:
        sp = json.load(r)["system_prompt"]
    open(f"{d}/{etap}/{i}_{persona}.txt", "w", encoding="utf-8").write(sp)
    if etap == "przed":
        print(f"[ZAPISANE] {persona:6} | {q} | {len(sp)} zn.")
        continue
    stary = open(f"{d}/przed/{i}_{persona}.txt", encoding="utf-8").read()
    if sp == stary:
        print(f"[IDENTYCZNY bit w bit] {persona:6} | {q}")
    elif maska(sp) == maska(stary):
        print(f"[IDENTYCZNY poza czasem] {persona:6} | {q}")
    else:
        wynik_ok = False
        a, b = maska(stary).splitlines(), maska(sp).splitlines()
        rozne = [(x, y) for x, y in zip(a, b) if x != y]
        print(f"[ROZNICA] {persona:6} | {q} | linii przed/po {len(a)}/{len(b)}, roznych {len(rozne)}")
        for x, y in rozne[:3]:
            print(f"    przed: {x[:120]}\n    po:    {y[:120]}")
if etap == "po":
    print("WYNIK:", "PRZESZLO" if wynik_ok else "ROZNICA -> COFAMY")
PY
