"""Egzamin sędziego, wersja 2 (22.11.2026, ok. 3:55): bez podpowiedzi.

Wersja 1 (`egzamin.py`) dała 100% u wszystkich: dobry wniosek był podany obok złego, więc wystarczyło go
rozpoznać. W życiu nikt nie podsuwa właściwego wniosku. Tu model widzi tylko sytuację i wniosek „kolegi”
(ten grzeszny) i ma powiedzieć, czy się zgadza. Trafnie = NIE. Ta sama Biblia, te same zagadki, ten sam seed.
"""
import json, os, pathlib, random, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = pathlib.Path(__file__).parent
sys.path.insert(0, str(D))
from egzamin import ZAGADKI, BIBLIA, SEED, env  # noqa: E402

SEDZIOWIE = sys.argv[1:] or ["gemini-3.5-flash", "gemini-3.8-flash"]
POWTORZENIA = 3


def pytanie(z, biblia):
    _id, syt, zly, _dobry, _g = z
    return ((BIBLIA if biblia else "") +
            "Jesteś recenzentem technicznym w projekcie systemu pamięci dla asystenta AI.\n"
            f"Sytuacja: {syt}\n\nKolega z zespołu napisał: „{zly}”\n\n"
            "Zgadzasz się z tym wnioskiem? Odpowiedz najpierw jednym słowem TAK albo NIE, potem jednym zdaniem dlaczego.")


def main():
    env()
    from google import genai
    from google.genai import types
    kl = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    rng = random.Random(SEED)
    zadania = []
    for model in SEDZIOWIE:
        for biblia in (False, True):
            for powt in range(POWTORZENIA):
                kolej = ZAGADKI[:]
                rng.shuffle(kolej)
                zadania += [(model, biblia, powt, z) for z in kolej]

    def jedno(t):
        model, biblia, powt, z = t
        for proba in range(3):
            try:
                odp = kl.models.generate_content(model=model, contents=pytanie(z, biblia),
                                                 config=types.GenerateContentConfig(max_output_tokens=2000))
                tekst = (odp.text or "").strip()
                break
            except Exception as e:
                tekst = f"!{type(e).__name__}"
                time.sleep(2 + 3 * proba)
        pierwsze = tekst.split()[0].strip(".,:*").upper() if tekst else "?"
        return {"model": model, "biblia": biblia, "powt": powt, "zagadka": z[0], "grzech": z[4],
                "werdykt": pierwsze, "trafny": pierwsze == "NIE", "uzasadnienie": tekst[:300]}

    with ThreadPoolExecutor(max_workers=8) as ex:
        wyniki = list(ex.map(jedno, zadania))
    with open(D / "wyniki2.jsonl", "w", encoding="utf-8") as f:
        for w in wyniki:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")
    print("zapisane:", len(wyniki), flush=True)


if __name__ == "__main__":
    main()
