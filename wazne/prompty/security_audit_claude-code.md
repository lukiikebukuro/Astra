# PROMPT — Audyt bezpieczeństwa (LDI + Astra/ANIMA) dla NOWEJ instancji Claude Code

> Wklej poniższy prompt do świeżej instancji Claude Code. WAŻNE: instancja musi mieć dostęp do OBU repozytoriów
> (Astra/ANIMA oraz LDI/forteca_finalna). Jeśli któregoś brakuje — dodaj je do sesji przed startem.

---

Jesteś inżynierem bezpieczeństwa aplikacji robiącym audyt dwóch produkcyjnych systemów jednego solo-foundera:
1. **Astra/ANIMA** — AI companion (FastAPI + ChromaDB + SQLite), publiczny na myastra.pl, trzyma NAJINTYMNIEJSZE dane jednego użytkownika.
2. **LDI (forteca_finalna)** — silnik lost-demand dla e-commerce, publiczny na adeptai.pl.

Masz dostęp do repozytoriów — CZYTAJ realny kod, nie zgaduj. Nie chwal. Twoje zadanie: znaleźć, jak to złamać, i dać konkretny fix. Pracuj metodycznie, per system.

## Dla KAŻDEGO systemu sprawdź:

1. **Sekrety w kodzie/gitcie** — przeszukaj repo (grep) za API keys, hasłami, tokenami, `.env` w gicie, hardcoded credentials. Sprawdź `.gitignore` i historię commitów (czy sekret kiedyś wyciekł).
2. **AuthN/AuthZ** — wypisz WSZYSTKIE endpointy (grep `@app.` / route decorators). Które są nieuwierzytelnione? Czy wrażliwe (`/api/debug/*`, dump pamięci, triggery, admin) polegają tylko na nginx? Zaproponuj auth na poziomie aplikacji.
3. **Injection / walidacja inputu** — user-input trafiający surowo do: promptów LLM (prompt injection), zapytań SQL/Chroma, ścieżek plików (path traversal, np. upload zdjęć), komend shell.
4. **Dane w spoczynku** — bazy (ChromaDB, SQLite) na dysku bez szyfrowania; co wycieka przy przejęciu VPS; uprawnienia plików.
5. **Zależności** — przejrzyj `requirements.txt` / `package.json` za znanymi CVE i porzuconymi pakietami.
6. **Powierzchnia sieciowa** — CORS, brakujące nagłówki bezpieczeństwa, rate-limiting (brak = DoS przez kosztowne calle LLM), ekspozycja portów.
7. **Logi** — czy sekrety/dane osobowe lądują w logach/stdout.

## Output (per system + wspólne)

- **Tabela podatności wg krytyczności** (Krytyczna / Wysoka / Średnia / Niska): Podatność → jak wykorzystać → dokładny fix (plik/linia/config).
- **„Minimalny zamek"** — 5 rzeczy do zrobienia NAJPIERW, żeby zamknąć największe dziury najmniejszym wysiłkiem.
- **Szybkie winy** — co można naprawić w <15 min każde.

Zacznij od przeszukania obu repo za sekretami i wylistowania wszystkich endpointów. Potem idź punkt po punkcie.
