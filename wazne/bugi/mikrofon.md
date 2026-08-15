# BUG: mikrofon — dłuższa wypowiedź nie daje transkrypcji

**Status:** OTWARTY · **Nawrót:** 4. podejście (licząc od 06.2026) · **Ostatnia praca:** 2026-08-15

**Objaw (słowami Łukasza):** naciska mikrofon, mówi — jeśli mówi dłużej, nagranie/transkrypcja
nie zapisuje nic. Po naprawie z 25.07 „trochę pomogło, dłużej można mówić niż wcześniej,
ale problem wraca".

---

## UWAGA NA START — to NIE jest jeden bug ciągnący się od czerwca

Implementacja została **wymieniona w całości** 2026-07-16 (`bd93135`, VOICE-1). Wszystko sprzed
tej daty dotyczy **innego mechanizmu** i innego objawu. Nie szukaj tam przyczyny dzisiejszego błędu.

| era | mechanizm | objaw, który naprawiano |
|---|---|---|
| do 16.07 | **Web Speech API** (rozpoznawanie w przeglądarce) | **duplikacja** tekstu, urywanie sesji przez Androida |
| od 16.07 | **push-to-talk**: WAV w przeglądarce → `/api/transcribe` → Gemini | **pusta** transkrypcja przy dłuższej wypowiedzi |

Powód wymiany (komentarz w `frontend/app.js:457`): na Androidzie silnik Web Speech kończy sesję
po każdej wypowiedzi (~4 s), zmierzone 7 restartów na 40 s, zero błędów — limit API, nie do obejścia.

---

## Historia podejść

| # | data | commit | hipoteza / zmiana | wynik | zweryfikowane na urządzeniu? |
|---|---|---|---|---|---|
| 1 | 2026-06-23 | `cb24508` | `resultIndex` + rozdzielenie final/interim + auto-restart `onend` | **NIEUDANE** — „resultIndex+dedup nie zadziałał na urządzeniu" (`_PODSUMOWANIE_2026-06.md`) | nie |
| 2 | — | `f689523`, `15df7cd`, `253b478` | duplikacja: final zastępuje wcześniejszy fragment | zamknięte jako „przyczyna znaleziona i potwierdzona" (`b38f75d`) | częściowo |
| — | — | `373ae02` → `b38f75d` | instrumentacja Web Speech → **usunięta po fixie** | — | — |
| 3 | 2026-07-16 | `bd93135` | przepisanie na push-to-talk + Gemini (nowa era) | objaw duplikacji zniknął, pojawił się objaw pustki | — |
| 4 | 2026-07-25 | (nginx, poza repo) | `client_max_body_size` → **25m** | **objawowe** — podniosło sufit długości, nie usunęło go. Stąd „dłużej można mówić, ale wraca" | tak (przez użycie) |
| 5 | 2026-08-15 | — | **diagnostyka, nie fix** — logowanie wejścia + `safe_response_text` | w toku | — |

---

## Co WYKLUCZONE dowodowo (2026-08-15, z logów serwera — nie powtarzać tej pracy)

- **nginx nie odrzuca żądań:** `client_max_body_size 25m`, `proxy_read_timeout 120s`.
  **Zero odpowiedzi 413**, zero 504 w `access.log` + `access.log.1`.
- **137 odpowiedzi 400 w nginx to wyłącznie skanery botów** (`POST /cgi-bin/...`, `CONNECT ipinfo.io`).
  Ani jedna z `/api/transcribe`.
- **Parser audio nigdy nie odrzucił nagrania:** zero `400 Bad Request` w logach uvicorna przez 30 dni
  (`_audio_part_from_data_url` zwraca `None` → 400, więc brak 400 = zawsze przechodziło).
- **Limity rozmiaru nie mogą być dziś sufitem** przy `MAX_RECORDING_MS` = 5 min:
  16 kHz/16-bit/mono = 32 KB/s → 5 min = **9,6 MB** surowo, **12,8 MB** w base64.
  Limity: nginx 25 MB, `MAX_AUDIO_BYTES` 20 MB. Zapas ~2×.

## Co USTALONE jako realny tryb awarii

```
Aug 13 10:22:42  [TRANSCRIBE] 0 znaków
Aug 13 10:22:42  POST /api/transcribe HTTP/1.0" 200 OK
```
Żądanie dochodzi, audio się parsuje, **Gemini zwraca pusty tekst**, endpoint oddaje ciche `200`,
a użytkownik widzi „Nie rozpoznano mowy w nagraniu". Wszystkie udane transkrypcje w logach są
krótkie (33-181 znaków) — spójne z objawem, ale **to nie dowód**, bo długości wejścia nie logowano.

## Luka, która blokowała diagnozę (usunięta 15.08)

Endpoint logował **wyjście** (`[TRANSCRIBE] 87 znaków`), a o **wejściu** nie zapisywał nic — więc
nie dało się skorelować awarii z długością nagrania, choć cały objaw jest o długości.
Do tego używał gołego `resp.text` zamiast istniejącego w repo `safe_response_text()`, napisanego
dokładnie dla multi-part odpowiedzi tego modelu — czyli pusty wynik nie niósł żadnego powodu.

**Dodana diagnostyka (STAŁA, nie usuwać):**
- `[TRANSCRIBE|wejscie] <bajty> B | mime | <sek> s | <Hz> | <ch> | <bit>`
- `[TRANSCRIBE] PUSTO — finish_reason=... block_reason=... usage=...`
- `[TRANSCRIBE] ODRZUCONE: ...` przy przekroczeniu limitu / pustym base64

---

## TEST 2026-08-15 — ścieżka serwerowa CZYSTA, wina jest po stronie przeglądarki

Materiał: mowa z ElevenLabs w `output_format=pcm_16000` — **dokładnie format produkcyjny**
(16 kHz, mono, 16-bit), owinięty tym samym nagłówkiem WAV co robi frontend. 187 s realnej mowy,
cięte na rosnące długości, podawane do `/api/transcribe`:

| długość | WAV | base64 | HTTP | czas | znaków |
|---|---|---|---|---|---|
| 15 s | 0,46 MB | 0,61 MB | 200 | 2,0 s | 200 |
| 45 s | 1,37 MB | 1,83 MB | 200 | 1,9 s | 587 |
| 90 s | 2,75 MB | 3,66 MB | 200 | 2,6 s | 956 |
| **187 s** | **5,71 MB** | **7,61 MB** | **200** | **4,3 s** | **2324** |

Dodatkowo MP3 2,41 MB (~2,6 min) → 200, 1979 znaków, 3,9 s.

**Wniosek: skalowanie liniowe, zero degradacji.** Gemini, format WAV, `MAX_AUDIO_BYTES`,
`safe_response_text` i czasy odpowiedzi są niewinne do co najmniej 187 s / 5,7 MB.
Skoro serwer transkrybuje poprawnie materiał, którego przeglądarka rzekomo nie potrafi dostarczyć,
**awaria zachodzi przed wysłaniem** — w `frontend/app.js`.

## ZNALEZIONA CICHA ŚCIEŻKA AWARII (frontend)

`_stopAndTranscribe()`, `frontend/app.js:605`:
```js
const raw = _flattenPcm(chunks);
if (!raw.length) { _micIdle(); return; }   // ← brak jakiegokolwiek komunikatu
```
Gdy `pcmChunks` jest puste, przycisk wraca do 🎤 i **nie dzieje się nic** — dokładnie „nie zapisuje
nic". Żadnego błędu, żadnego wpisu w logach serwera (żądanie nigdy nie wychodzi), więc dotychczasowa
diagnostyka serwerowa nie mogła tego zobaczyć.

**Podejrzenie towarzyszące:** `toggleMic()` tworzy `AudioContext`, ale **nigdy nie woła
`audioCtx.resume()`** (`app.js:569-591`). Na mobilnym Chrome kontekst potrafi wystartować w stanie
`suspended`; wtedy `ScriptProcessorNode.onaudioprocess` nie odpala się ani razu → zero chunków →
cicha ścieżka wyżej. Do tego `ScriptProcessorNode` jest przestarzały i bywa dławiony, gdy karta
traci pierwszy plan (wygaszenie ekranu telefonu przy dłuższym mówieniu).

**Trzy tryby awarii dają RÓŻNE komunikaty w UI** — jedno pytanie do Łukasza je rozróżnia:
| co widzi | znaczenie |
|---|---|
| **nic** (ikona wraca do 🎤, brak komunikatu) | zero chunków — kontekst audio nie nagrywał |
| „Nie rozpoznano mowy w nagraniu." | audio doszło, Gemini zwrócił pusto |
| „Transkrypcja nie powiodła się: …" | błąd sieci/HTTP |

## ROZSTRZYGNIĘCIE (2) vs (3) — z logów, nie z pamięci (2026-08-15)

Retencja `journalctl` sięga **marca**, nginx ~14 dni. Cała historia od VOICE-1:

| sygnał | liczba | wniosek |
|---|---|---|
| `[TRANSCRIBE] 0 znaków` + 200 OK | **5** (23.07, 25.07, 07.08 ×2, 13.08) | **opcja (2) — to jest ten bug** |
| 499 „klient zerwał połączenie" | **0** w całej retencji nginx | opcja (3) nie występuje |
| 413 (za duże body) | 0 | limity niewinne |
| 502 | 1 (14.08) | jednorazowe `503 UNAVAILABLE` po stronie Google, nie nasz bug |

Łącznie 57 transkrypcji → **~9% kończy się pustką**.

## HIPOTEZA „cicha mowa nocą" — OBALONA pomiarem

Cztery z pięciu awarii wypadły ok. 23:00, więc sprawdziłem, czy winna jest cicha mowa
(`TRANSCRIBE_PROMPT` każe zwrócić pusty tekst przy cichym nagraniu, a `getUserMedia` ma włączone
`noiseSuppression` + `echoCancellation`). Ten sam materiał, malejąca amplituda:

| gain | peak | znaków |
|---|---|---|
| 1,00 | 17789 | 842 |
| 0,15 | 2668 | 964 |
| 0,05 | 889 | 929 |
| **0,02 (szept)** | **355** | **1070** |

**Gemini transkrybuje nawet szept na 1% skali.** Cisza nie jest przyczyną — hipoteza odrzucona.

## GDZIE TO ZOSTAWIA SPRAWĘ

Serwer poprawnie obsługuje: długie (187 s), ciche (peak 355), WAV i MP3. A mimo to 5× dostał
materiał, z którego nie wyszedł ani znak. Wniosek: **przeglądarka wysyła bufor wypełniony ciszą** —
niepusty (`raw.length > 0`, więc żądanie wychodzi), ale bez sygnału. `app.js:605` sprawdza wyłącznie
**długość** bufora, nigdy **amplitudę**.

Reprodukcja podpisu awarii (symulowany bufor zer, 20 s):
```
[TRANSCRIBE|wejscie] 640044 B | 20.0 s | 16000 Hz | 1 ch | 16 bit | peak=0 rms=0 ← CISZA/BRAK SYGNAŁU
[TRANSCRIBE] PUSTO — finish_reason=FinishReason.STOP block_reason=NONE
```
`finish_reason=STOP` (nie `MAX_TOKENS`, nie `SAFETY`) = model zakończył normalnie i świadomie nie
zwrócił nic. Zgodne z „w nagraniu nie ma mowy".

**Następna awaria u Łukasza rozstrzyga ostatecznie:**
- `peak≈0` → wina frontu (strumień zawieszony / mikrofon nie nagrywał) → fix w `app.js`
- `peak` normalny → wina modelu → `finish_reason` powie dlaczego

## Otwarte tropy (do sprawdzenia, kolejność wg prawdopodobieństwa)

1. **Gemini zwraca pusto dla długiego audio** — `finish_reason` powie, czy to `MAX_TOKENS`, `SAFETY`,
   czy model dosłownie wykonał instrukcję z `TRANSCRIBE_PROMPT` („jeśli nagranie jest ciche,
   puste lub niezrozumiałe — zwróć pusty tekst").
2. **Kodowanie WAV w przeglądarce psuje się przy długości** — `pcmChunks` gromadzi `Float32Array`
   w rate'cie nagrywania (48 kHz → ~192 KB/s → 5 min ≈ 57 MB), potem `_flattenPcm` robi drugą kopię
   tej samej wielkości. Presja pamięci na telefonie. Objaw byłby po stronie frontu, nie serwera.
3. **`MAX_RECORDING_MS` = 5 min** jako twardy sufit — jeśli user mówi dłużej, `setTimeout` przerywa
   w trakcie; sprawdzić, czy to nie jest mylone z „urwało".

## Zasada dla tego buga

Nie wdrażać kolejnego fixu bez pomiaru pokazującego mechanizm. Cztery podejścia, z czego co najmniej
dwa objawowe — koszt kolejnego zgadywania jest wyższy niż koszt jednego testu.
