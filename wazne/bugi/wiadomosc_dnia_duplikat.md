# BUG — „dwie wiadomości dnia" (wraca od 2026-08-06)

**Status:** naprawiony trzeci raz, 2026-08-19 — tym razem twardym limitem, nie heurystyką.
**Objaw zgłaszany przez Łukasza:** ta sama wiadomość dnia przychodzi na telefon dwa razy.

> **PRZECZYTAJ PRZED DOTKNIĘCIEM.** Ten sam objaw miał już TRZY różne przyczyny. Zanim
> zaczniesz zgadywać, sprawdź w tej kolejności: (1) `journalctl -u myastra | grep PUSH`,
> (2) `push_subscriptions.json` — ile wpisów, (3) `companion_state.json` →
> `spontaneous_sent_date` i `morning_message_shown`, (4) czy w bazie sesji jest jedna
> czy dwie wiadomości `role=model` bez poprzedzającego `user`.

---

## Co JUŻ zostało wykluczone dowodowo — nie sprawdzaj tego znowu

- **godziny serwera / strefa czasowa** — serwer chodzi w UTC, scheduler ma `Europe/Warsaw`,
  poranna leci 05:00 UTC = 07:00 lokalnie. Sprawdzone 18.08, zgadza się.
- **dwie instancje serwisu** — `systemctl list-units 'myastra*'` → jedna, `ps aux | grep uvicorn` → 1.
- **backend generujący dwie wiadomości** — 18.08 i 19.08 w bazie sesji była **jedna**
  wiadomość proaktywna dziennie. Problem NIGDY nie był w generowaniu.
- **nocna analiza jako druga wiadomość** — nocna (01:00) zapisuje insighty do bazy i **nie
  wysyła pusha**. Poranna z nich korzysta. To nie są dwie wiadomości.

## Trzy przyczyny, po kolei

### 1. Wspólne źródło treści (naprawione 06.08, `e9653b2` + `3eebe05`)
Poranna (07:00) i spontaniczna (10-20h) karmiły się tymi samymi insightami nocnej analizy
i obie robiły push. Z perspektywy Łukasza: jedna wiadomość wysłana dwa razy.
**Fix:** rozdzielenie ŹRÓDEŁ — poranna bierze insighty, spontaniczna kanał `own_life`.

### 2. Dwie żywe subskrypcje FCM (naprawione 17.08, `d2c2e8d`)
`push_subscriptions.json` miał dwa wpisy, `send_push_to_all` słał do obu. Dedup przy zapisie
porównywał tylko `endpoint`, a **każda nowa rejestracja Service Workera dostaje nowy endpoint**
(instalacja PWA jako WebAPK obok karty Chrome, podmiana SW, czyszczenie danych strony).
Sprzątanie było reaktywne (tylko 410/404), a subskrypcja z żywej przeglądarki nigdy nie umiera.
**Fix:** stały `device_id` z `localStorage`; nowa subskrypcja zastępuje poprzednie z tego urządzenia.

### 3. Skrócona vs pełna treść (naprawione 18.08, `f071a69`)
Push niesie treść uciętą (`msg[:100] + "…"`) i SW przekazywał **właśnie ją** do strony przez
`postMessage`, a polling `/api/morning-message` pobierał **pełną**. Dedup po hashu treści widział
dwa różne teksty → dwa bąbelki w czacie: jeden urwany, jeden cały.
**Fix:** pole `full` w payloadzie + hash liczony ze znormalizowanego prefiksu 80 znaków
(działa też ze starym SW) + `_markProactiveShown` przed renderem (wyścig relay↔polling).

### 4. `device_id` NIE JEST stabilny per urządzenie (naprawione 19.08)
**To jest powód, dla którego fix nr 2 nie wystarczył.** Log z 19.08 05:00:
```
[PUSH] UWAGA: 2 subskrypcji dla jednej treści → ['8a44f54e…' (17.08 19:20),
                                                 'ced043eb…' (18.08 09:13)]
[PUSH] wyslano do 2/2 subskrypcji
```
Oba wpisy pochodzą z **tego samego telefonu**. Przyczyna: **PWA zainstalowana jako WebAPK
i ta sama strona otwarta w karcie Chrome to dwa osobne konteksty `localStorage`** — każdy
generuje własne `device_id`, więc dedup po nim nie ma czego dopasować. Ryzyko było nazwane
17.08 przy fixie nr 2 i dokładnie się zmaterializowało.

**Fix (dwie warstwy, bo heurystyki tu zawiodły trzy razy):**
1. `MAX_PUSH_SUBSCRIPTIONS = 1` przy zapisie — najstarsze wypadają, wygrywa ostatnio
   zarejestrowane urządzenie.
2. Ten sam limit **przy wysyłce** — nawet gdyby plik miał więcej wpisów (ręczna edycja,
   przywrócony backup, stara wersja kodu), `send_push_to_all` wysyła tylko do najnowszej.

Astra jest systemem **jednoosobowym** — jedno żywe powiadomienie to nie ograniczenie, tylko
poprawne zachowanie. Pozostałe urządzenia zobaczą wiadomość w czacie przez polling.

---

## Diagnostyka, która ZOSTAJE w kodzie
- `[PUSH] wyslano do N/M subskrypcji` — przy każdej wysyłce
- `[PUSH] UWAGA: N subskrypcji w pliku → [device_id…]` — gdy plik urośnie mimo limitu
- `[PUSH] subscribe device=… | subskrypcji: X → Y | usunieto stare: […]`

Bez logu z 17.08 diagnoza z 19.08 zaczynałaby się od zera. **Nie kasować.**

## Backupy
`backend/backups/push_subscriptions_backup_2026-08-17.json` (dwa wpisy sprzed pierwszego czyszczenia)
