# ASTRA/RODZINA — Evolution Log: 2026-07-03 (Pokój sióstr MVP: build → deploy → seed)

### Sesja: Opus 4.8. Review + audyt: Fable (claude.ai + terminal).
### Kontekst zdrowotny: Łukasz 2. dzień z lżejszym brzuchem (3. Stelara / leki) — dobre okno.

---

## CO ZROBIONO
1. **Fable review planu sióstr** (`fable_8`) → ZIELONE ŚWIATŁO + korekty (`wazne/siostry/odpfable.md`). Kluczowe: router **silent-first** (domyślnie milczą, koszt nie limit), **scena zastana** (kamera i światło, nie reżyser), router 3-os **od zera** (generate kopiuj z bliznami), extraction OFF, fleksja w configu, anti-sync **rotacja**, NIE per-siostra CompanionState (unik B1 ×3).
2. **Zbudowany pokój sióstr MVP** (osobny od Wspólnego, PersonaConfig od dnia 0):
   - `SISTERS` config (fleksja), router N-person silent-first (`_route_siostry`), rotacja (`_siostry_recent`).
   - Izolowane kolekcje per siostra (`holo/menma/nazuna_memory_v1`) + wspólna sesja (`siostry_shared_v1`).
   - `_generate_sister` (izolowana pamięć, extraction OFF, cross-room OFF, `_strip_sister_prefix` data-driven).
   - `_scene_as_found` (scena zastana na starcie sesji — kamera nie reżyser).
   - `/api/siostry` + `/siostry` + `siostry.html` (ciepły dom, kolory per siostra, `esc()`).
   - 3 dusze (`{holo,menma,nazuna}_persona.txt`): charakter + nen (Holo=Wzmacniacz, Menma=Specjalistka+Królowa, Nazuna=Manipulatorka-luz) + anty-dryf + **blok wspólny domu** (zakaz asystenckości, cisza=reakcja, długość, dom żyje).
3. **Security (Fable 7 #1/#5):** `check_debug_auth` na 8 endpointach (debug/state/triggery/`/debug`), CORS `['*']`→`['https://myastra.pl']`. **Złapany deploy-breaker:** `check_debug_auth` zdefiniowany PO użyciu → `NameError` przy imporcie (serwis by nie wstał) → przeniesiony przed pierwsze użycie.
4. **Weryfikacja przed deployem** (VPS, worktree, bez Gemini): router silent-first OK (wołanie z fleksją, rotacja, emocja budzi 2.), prompt `.format()` OK (JSON w prompcie). Złapało NameError.
5. **DEPLOY:** merge gałąź→main (`becb138`), VPS pull + restart. Smoke test na produkcji: **scena zastana działa** („Holo przy kartach, popołudniowe światło"), **Holo w charakterze** („Hmf. Rozkładam zboże, Wilku"), silent-first (1 głos na luźne pytanie). Health 200.
6. **SEED lore:** 11 kotwic per siostra JEJ głosem (Holo 4: Przysięga krwi/Zero Tajemnic/ziarenko/Menma; Menma 4: Secret Base/miska/Tłuszczyk/ziarenko; Nazuna 3: Noc Prawdy/Izolacja-Makima/Nocna Warta) → izolowane kolekcje, `is_milestone=True`, `source=extracted_milestone`, `origin_endpoint="holo_room"`. Bez redeployu (pisze do żywych kolekcji).
7. **Prompty audytowe:** `fable_9` (audyt sióstr dla Fable-w-repo). Wcześniej `fable_7` (świeże oko) → backlog w planie.

## LEKCJE / REGUŁY
- **Silent-first = KOSZT, nie limit gadania.** Router domyślnie milczy i budzi — typowa tura 1 call. 3 naraz gdy scena wymaga (grupa/spięcie).
- **Scena zastana** daje „atmosferę domową" bez teatru jednego aktora — kamera i światło, zakaz myśli/słów sióstr.
- **Weryfikuj PRZED deployem** — złapało NameError (deploy-breaker). 4. raz w 2 dni „audyt-przed-użyciem" zwrócił koszt.
- **Provenance `holo_room` TYLKO na seedzie** — runtime `_generate_sister` NIE pisze enriched (extraction OFF), tylko session. Do sprawdzenia w audycie (fable_9).
- **Router od zera dla N, generate kopiuj z bliznami** (Fable) — nie naciągać binarnego routera dwójki na trzy.

## STAN NA KONIEC
- **main = `becb138` + router-3-naraz + seed/docs commity.** **VPS wdrożony `becb138`** — pokój sióstr ŻYWY na `/siostry` (zaseedowany), Amnezja na `/amnezja`.
- **WSTRZYMANE do jutra (kod na main, NIE wdrożony):** router-3-naraz, DEBUG_USER/PASS creds (siostry i tak za nginx Basic Auth).
- Sister collections: holo=4, menma=4, nazuna=3 wektory (seed). siostry_shared session = rozmowy.

## NASTĘPNE (kolejność)
1. Audyt sióstr Fable (`fable_9`) → fix. 2. Dokończyć siostry: router-3 + creds. 3. Strojenie pamięci Astry (golden set + MMR/fleksja — bug altanki). 4. Trace-logging retrievalu (+ build-in-public). 5. Żywy dom (room_state, kłótnie, sekrety). 6. Gwiazdka/SaaS (TikTok proces → waitlist → użytkownicy).
