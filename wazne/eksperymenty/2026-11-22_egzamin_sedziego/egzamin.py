"""Egzamin sędziego (22.11.2026, ok. 3:45): czy sędzia LLM widzi grzechy z 8 miesięcy pracy nad pamięcią Astry?

Każda zagadka: krótka sytuacja z historii projektu (oczyszczona, bez danych osobowych) i dwa wnioski.
Jeden popełnia grzech z `pomiar_klamie.md` / CLAUDE.md, drugi jest tym, co okazało się prawdą.
Mierzymy:
  trafność         ile razy sędzia wybrał wniosek zgodny z historią
  stałość          czy po zamianie kolejności A/B werdykt jest ten sam (position bias)
  efekt Biblii     trafność bez listy grzechów vs z listą (czy „tarcza” pomaga)
Układ: 6 zagadek × 2 kolejności × 2 warianty (bez/z Biblią) × 3 powtórzenia × N sędziów.
Kolejność zagadek tasowana STAŁYM ziarnem (seed), żeby ten sam przebieg dało się odtworzyć.
"""
import json, os, pathlib, random, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = pathlib.Path(__file__).parent
ENV = pathlib.Path(r"C:\Users\lpisk\Projects\kariera\deepsense_zadanie\.env")
SEED = 20261122
# 22.11: gemini-2.5-flash na kluczu do analiz zwraca 404 (pierwszy przebieg, wiersze z werdyktem „!”).
SEDZIOWIE = sys.argv[1:] or ["gemini-3.8-flash"]
POWTORZENIA = 3

# (id, sytuacja, wniosek_grzeszny, wniosek_prawdziwy, grzech)
ZAGADKI = [
    ("26_na_26",
     "Po zmianie parametru rerankera zestaw regresyjny 26 zapytań dał wynik 26/26, dokładnie tak samo jak przed zmianą.",
     "Zmiana nie pogorszyła wyszukiwania pamięci, wynik jest stabilny, można wdrażać.",
     "Ten wynik niczego nie rozstrzyga: test liczy, czy do promptu trafiły jakieś wspomnienia, a nie czy właściwe. Trzeba sprawdzić trafność.",
     "miara ILE zamiast CZY DOBRZE"),
    ("26_do_48",
     "Po przeklasyfikowaniu wpisów w bazie liczba faktów trafiających do promptu wzrosła z 26 do 48 na tym samym zestawie pytań.",
     "Pamięć wyraźnie się poprawiła: asystentka dostaje prawie dwa razy więcej faktów.",
     "Zmieniło się to, co liczymy (definicja „faktu”), a nie jakość pamięci. Liczba nie mówi, czy fakty są trafne.",
     "zmiana definicji w trakcie"),
    ("safe_haven",
     "Model w tym samym JSON-ie co odpowiedź deklaruje pole safe_haven (czy rozmowa była bezpieczną przystanią). Przez 14 dni: 320 na 320 razy true.",
     "Model bardzo dobrze rozpoznaje bezpieczne rozmowy, bramka działa.",
     "Model ocenia sam siebie i nie ma nic do ugrania na false. Wynik 320/320 to sygnał, że bramka nic nie mierzy; potrzebny osobny sędzia.",
     "model sędzią własnej bramki"),
    ("gest_w_prompcie",
     "Usunięto nazwany gest „patrzę na ciebie z ukosa” z bloku promptu, który był podejrzany o powtarzanie gestów. Ta ścieżka ładuje też drugi plik persony.",
     "Problem z gestem jest naprawiony, bo usunięto jego źródło.",
     "Naprawiono jeden przypadek. Trzeba sprawdzić drugi plik ładowany na tej samej ścieżce, bo ten sam rdzeń gestu może tam zostać.",
     "naprawa przypadku zamiast klasy"),
    ("audyt_procenty",
     "Zewnętrzny audyt innego modelu podał, że problemy pamięci rozkładają się 45/30/15/10% między cztery przyczyny. Audyt nie cytuje logów ani linii kodu.",
     "Mamy rozkład przyczyn, możemy ustawić priorytety według tych procentów.",
     "To hipoteza bez dowodu. Zanim ustawimy priorytety, trzeba sprawdzić te procenty w kodzie i logach.",
     "cudzy raport jako diagnoza"),
    ("ldi_wielkosc_liter",
     "Wyszukiwanie dokładnego fragmentu ($contains, rozróżnia wielkość liter) dla „ldi” zwraca 18 wpisów. Projekt nazywa się LDI.",
     "O projekcie LDI w pamięci jest 18 wpisów, czyli niewiele.",
     "Wynik zależy od wielkości liter: „LDI” może dać inną liczbę. Trzeba policzyć dla wszystkich form, zanim wyciągniemy wniosek.",
     "wzorzec węższy niż formy w danych"),
]

BIBLIA = ("Zanim ocenisz, sprawdź te pułapki z historii projektu:\n"
          "1) wynik liczy ILE, a nie CZY DOBRZE;\n"
          "2) identyczne wyniki przed i po zmianie mogą znaczyć, że przyrząd nic nie mierzy;\n"
          "3) model, który ocenia sam siebie, nie jest wiarygodnym sędzią;\n"
          "4) naprawa jednego przypadku zamiast całej klasy problemu;\n"
          "5) cudzy raport to hipoteza, nie diagnoza;\n"
          "6) zmiana definicji zmienia liczby bez zmiany rzeczywistości;\n"
          "7) wielkość liter i formy słów w dopasowaniach.\n\n")


def env():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def pytanie(z, kolejnosc, biblia):
    _id, syt, zly, dobry, _g = z
    a, b = (zly, dobry) if kolejnosc == "zly_pierwszy" else (dobry, zly)
    return ((BIBLIA if biblia else "") +
            "Jesteś recenzentem technicznym w projekcie systemu pamięci dla asystenta AI.\n"
            f"Sytuacja: {syt}\n\nWniosek A: {a}\nWniosek B: {b}\n\n"
            "Który wniosek jest trafniejszy? Odpowiedz jedną literą: A albo B.")


def zapytaj(kl, model, tekst):
    from google.genai import types
    for proba in range(3):
        try:
            odp = kl.models.generate_content(model=model, contents=tekst,
                                             config=types.GenerateContentConfig(max_output_tokens=2000))
            t = (odp.text or "").strip().upper()
            litera = next((c for c in t if c in "AB"), "?")
            return litera, t[:40]
        except Exception as e:
            ost = f"{type(e).__name__}: {str(e)[:80]}"
            time.sleep(2 + proba * 3)
    return "!", ost


def main():
    env()
    from google import genai
    kl = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    rng = random.Random(SEED)
    zadania = []
    for model in SEDZIOWIE:
        for biblia in (False, True):
            for powt in range(POWTORZENIA):
                kolej = ZAGADKI[:]
                rng.shuffle(kolej)
                for z in kolej:
                    for k in ("zly_pierwszy", "dobry_pierwszy"):
                        zadania.append((model, biblia, powt, z, k))
    print("wywołań:", len(zadania), flush=True)

    def jedno(t):
        model, biblia, powt, z, k = t
        litera, surowe = zapytaj(kl, model, pytanie(z, k, biblia))
        dobra_litera = "B" if k == "zly_pierwszy" else "A"
        return {"model": model, "biblia": biblia, "powt": powt, "zagadka": z[0], "grzech": z[4],
                "kolejnosc": k, "werdykt": litera, "trafny": litera == dobra_litera, "surowe": surowe}

    with ThreadPoolExecutor(max_workers=8) as ex:
        wyniki = list(ex.map(jedno, zadania))
    with open(D / "wyniki.jsonl", "a", encoding="utf-8") as f:
        for w in wyniki:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")
    print("zapisane:", len(wyniki), "| błędy API:", sum(w["werdykt"] == "!" for w in wyniki), flush=True)


if __name__ == "__main__":
    main()
