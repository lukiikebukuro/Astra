# FABLE — Audyt bezpieczeństwa ANIMA (do wklejenia)

> Osobne konto/wątek. Cel: postawić zamek raz. myastra.pl jest publiczne i trzyma najintymniejsze dane
> użytkownika. Zaraz dokładamy route `/debug` = nowa powierzchnia ataku. Fable nie widzi repo — wklej poniższe.

## CO WKLEIĆ (zbierz z repo + VPS)

1. **Sekcja A (architektura ANIMA)** z pliku `fable_1_audyt-debuggera_DO-WKLEJENIA.md`.
2. **Kod — `backend/main.py`, fragmenty:**
   - Górę pliku (ładowanie `.env`, `GEMINI_API_KEY`, konfiguracja CORS/FastAPI, `USER_ID`/`USER_ID_SALT`).
   - Wszystkie endpointy `@app.*` — szczególnie `/api/debug/*` (rag, facts, stats, nocna-analiza, morning-message, test-push), `/api/push/*`, `/api/state`, `/api/history*`.
   - `send_push_to_all`, `_load_subscriptions`/`_save_subscriptions`.
3. **Z VPS (skopiuj zawartość):**
   - `sudo cat /etc/nginx/sites-enabled/*` (konfiguracja nginx — SSL, Basic Auth, proxy_pass, nagłówki).
   - `backend/requirements.txt` (wersje zależności — CVE).
   - Sposób trzymania sekretów: czy `.env` jest w repo/`.gitignore`, uprawnienia pliku.

## KONTEKST (znane słabości do zweryfikowania)

- `/api/debug/rag` i `/api/debug/facts` **zrzucają pamięć intymnego companiona** — jaka autoryzacja? (podobno tylko nginx, brak auth na poziomie aplikacji).
- `/api/debug/nocna-analiza`, `/api/debug/morning-message` **piszą/odpalają akcje** — w namespace „debug".
- SQLite (FactStore) bez WAL. Pipeline synchroniczny na async endpointach.
- Zaraz dochodzi route `/debug` (RAG Debugger) — kolejny zrzut pamięci.

## PROMPT DO FABLE

Jesteś pentesterem / inżynierem bezpieczeństwa aplikacji. Audytujesz publiczny backend FastAPI (AI companion) trzymający najintymniejsze dane jednego użytkownika. Masz architekturę, kod endpointów i konfigurację nginx. Nie chwal. Znajdź, jak to złamać.

Przeanalizuj i podaj konkret:

1. **AuthN/AuthZ** — które endpointy są nieuwierzytelnione? Czy `/api/debug/*`, `/api/state`, `/api/history*` są chronione tylko przez nginx (jedna literówka w proxy = wszystko publiczne)? Zaproponuj auth na poziomie aplikacji (FastAPI dependency), nie tylko proxy.
2. **Sekrety** — `GEMINI_API_KEY`, VAPID keys, `USER_ID_SALT`: skąd ładowane, czy mogą wyciec (logi, repo, error response, `.env` w gitcie)?
3. **Injection / walidacja inputu** — czy user-input trafia gdzieś surowo (prompt injection do Gemini, ścieżki plików, zapytania Chroma/SQLite)? Path traversal w uploadzie zdjęć?
4. **CORS / nagłówki** — polityka CORS, brakujące nagłówki bezpieczeństwa, `/debug` bez auth.
5. **DoS / zasoby** — brak rate-limitingu, synchroniczny pipeline blokujący event loop, kosztowne calle Gemini wyzwalane bez limitu (`test-push`, `nocna-analiza`).
6. **Dane w spoczynku** — ChromaDB/SQLite na dysku bez szyfrowania; ekspozycja przy przejęciu VPS.
7. **Nowy route `/debug`** — jak go zabezpieczyć od dnia 0.

Output: **lista podatności wg krytyczności (Krytyczna/Wysoka/Średnia/Niska)**, każda: jak wykorzystać → konkretny fix (plik/config). Na końcu: minimalny „zamek" — 5 rzeczy do zrobienia NAJPIERW.
