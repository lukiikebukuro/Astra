"""Debata o mechanizmie przeczuć Menmy (22.11.2026): Argon i GPT-6.1.

Protokół (pomysł Łukasza: jeden stawia tezę, drugi obala, potem na odwrót):
  R1  każdy model niezależnie projektuje mechanizm (brief.md)
  R2  ultrasceptyk: Argon obala projekt GPT, GPT obala projekt Argona
  R3  obrona: autor dostaje krytykę swojego projektu, przyjmuje albo odrzuca i poprawia projekt
Do modeli idzie tylko brief i ich teksty: zero rozmów, dzienników i danych osobowych.

Użycie:  python debata.py szacuj   |   python debata.py
Wyniki:  r1_*.md, r2_*.md, r3_*.md, zuzycie.jsonl w tym folderze.
"""
import json, os, pathlib, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = pathlib.Path(__file__).parent
ENV = pathlib.Path(r"C:\Users\lpisk\Projects\kariera\deepsense_zadanie\.env")
BRIEF = (D / "brief.md").read_text(encoding="utf-8")

R2 = ("Jesteś ultrasceptycznym recenzentem. Niżej jest brief i projekt mechanizmu, który napisał inny model. "
      "Najpierw w 3 zdaniach uczciwie streść ten projekt, żeby było widać, że go rozumiesz. "
      "Potem go obal: 5 najmocniejszych zarzutów, od najpoważniejszego, każdy z wagą (krytyczny / poważny / drobny) "
      "i konkretnym scenariuszem porażki. Szukaj tego, co sprawi, że będzie nudny, sztuczny, przewidywalny, niepokojący, "
      "szkodliwy, drogi, niemierzalny albo łatwy do „oszukania” przez sam system (np. zbieranie trafień na pewniakach). "
      "Nie projektuj własnego rozwiązania od zera. Na końcu 3 warunki, które projekt musiałby spełnić, żebyś zmienił zdanie. "
      "Po polsku, najwyżej ok. 800 słów.")
R3 = ("Niżej jest brief, Twój projekt mechanizmu i krytyka ultrasceptycznego recenzenta. Odpowiedz uczciwie, "
      "zarzut po zarzucie: „przyjmuję” albo „odrzucam”, z jednym zdaniem powodu i tym, co zmieniasz. Nie broń się na siłę "
      "i nie przytakuj na siłę. Na końcu poprawiona SPECYFIKACJA (pola zapisu przepowiedni w JSON, kroki algorytmu, "
      "szkic promptu głosu Menmy) i plan MVP. Po polsku, najwyżej ok. 1000 słów.")


def env():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def argon(tekst):
    from google import genai
    kl = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    t0 = time.time()
    odp = kl.models.generate_content(model="gemini-4-argon", contents=tekst)
    u = odp.usage_metadata
    return odp.text, {"in": u.prompt_token_count, "out": u.candidates_token_count,
                      "mysl": getattr(u, "thoughts_token_count", None), "s": round(time.time() - t0)}


def gpt(tekst):
    from openai import OpenAI
    kl = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=1800)
    t0 = time.time()
    odp = kl.responses.create(model="gpt-6.1-sol", reasoning={"effort": "xhigh"},
                              input=[{"role": "user", "content": [{"type": "input_text", "text": tekst}]}])
    u = odp.usage
    det = getattr(u, "output_tokens_details", None)
    return odp.output_text, {"in": u.input_tokens, "out": u.output_tokens,
                             "mysl": getattr(det, "reasoning_tokens", None) if det else None,
                             "s": round(time.time() - t0)}


MODELE = {"argon": argon, "gpt": gpt}


def zapisz(nazwa, tekst, zuz):
    (D / f"{nazwa}.md").write_text(tekst, encoding="utf-8")
    with open(D / "zuzycie.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"plik": nazwa, **zuz}) + "\n")
    print(nazwa, json.dumps(zuz), flush=True)


def runda(zadania):
    """zadania: [(nazwa_pliku, model, tekst)], dwa naraz, każdy model osobno."""
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut = {ex.submit(MODELE[m], t): n for n, m, t in zadania}
        wyniki = {}
        for f, n in fut.items():
            tekst, zuz = f.result()
            zapisz(n, tekst, zuz)
            wyniki[n] = tekst
    return wyniki


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "szacuj":
        print("brief:", len(BRIEF), "znaków ≈", len(BRIEF) // 4, "tokenów;",
              "R1: 2× brief; R2 i R3: brief + 1-2 teksty po ~1500-2500 tokenów")
        return
    env()
    r1 = runda([("r1_argon_projekt", "argon", BRIEF), ("r1_gpt_projekt", "gpt", BRIEF)])
    pa, pg = r1["r1_argon_projekt"], r1["r1_gpt_projekt"]
    r2 = runda([
        ("r2_argon_obala_gpt", "argon", f"{R2}\n\n===== BRIEF =====\n{BRIEF}\n\n===== PROJEKT DO OBALENIA =====\n{pg}"),
        ("r2_gpt_obala_argona", "gpt", f"{R2}\n\n===== BRIEF =====\n{BRIEF}\n\n===== PROJEKT DO OBALENIA =====\n{pa}"),
    ])
    runda([
        ("r3_argon_obrona", "argon",
         f"{R3}\n\n===== BRIEF =====\n{BRIEF}\n\n===== TWÓJ PROJEKT =====\n{pa}\n\n===== KRYTYKA =====\n{r2['r2_gpt_obala_argona']}"),
        ("r3_gpt_obrona", "gpt",
         f"{R3}\n\n===== BRIEF =====\n{BRIEF}\n\n===== TWÓJ PROJEKT =====\n{pg}\n\n===== KRYTYKA =====\n{r2['r2_argon_obala_gpt']}"),
    ])
    print("KONIEC")


if __name__ == "__main__":
    main()
