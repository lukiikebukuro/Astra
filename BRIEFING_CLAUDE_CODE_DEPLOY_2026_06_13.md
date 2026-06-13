# BRIEFING DLA CLAUDE CODE — Deploy 2026-06-13

## Co zostało zrobione (przez GitHub Copilot)

Zmiany są już na GitHubie (`main`, commit `7a50cee`).
Szczegółowy opis tego co i dlaczego zmieniono: `wazne/ewolucja Astry/evolution_log_2026_06_13.md`

## Twoje zadanie

**Wejdź na VPS i wykonaj:**

1. `git pull origin main` w katalogu projektu Astry
2. Zrestartuj backend (uvicorn / systemd / pm2 — cokolwiek tam działa)
3. Sprawdź logi czy serwer wstał bez błędów
4. Opcjonalnie: szybki `curl http://localhost:PORT/api/health` żeby potwierdzić że odpowiada

## Co się zmieniło w kodzie (skrót)

- `backend/main.py` — duże zmiany w prompt assembly (patrz evolution log)
- `backend/amelia_companion_state.json` — **nowy plik** (jeśli VPS ma własny stan Amelii, NIE nadpisuj go git pullem — plik jest w `.gitignore` lub nie? Sprawdź to najpierw)
- Usunięte pliki: `inner_monologue_NEW.py`, `prompts/astra/level_*.txt`

## Ważna uwaga przed pullem

Sprawdź czy `backend/amelia_companion_state.json` i `backend/companion_state.json` są w `.gitignore` na VPS. Jeśli nie są — git pull może nadpisać stan relacji produkcyjnej bazy. Jeśli są w `.gitignore`, pull ich nie tknie i jest bezpieczny.
