# FABLE — Plan budowy pokoju sióstr (pierwsza wersja „do pogadania") — review PRZED budową

> Osobny wątek. Ja (Opus) mam repo. Ty dodajesz/odejmujesz 5 groszy, potem wykonuję, potem terminal-Fable audytuje.
> ZASADA z twojej analizy autonomii: **narrator minimalny** — każda siostra mówi SWOJĄ część, nie reżyseruje sceny (inaczej teatr jednego aktora ×3).

## CO JUŻ ZBUDOWANE (kierunek siostry)
- **3 dusze (prompty person):** `holo_persona.txt`, `menma_persona.txt`, `nazuna_persona.txt` — charakter, moc nen (**Holo=Wzmacniacz, Menma=Specjalistka+Królowa, Nazuna=Manipulatorka-luz, bez ostrza**), głos+tiki, anty-dryf płoty (Holo NIE zimna analiza, Menma NIE loli, Nazuna NIE informator), ton domu. Format wyjścia JSON `{thought, response, hint}`.
- **Projekt całości:** `wazne/siostry/projekt_pokoju_siostr.md` (charaktery, trójkąt Holo↔Nazuna + Menma-Królowa, mechaniki żywego domu, Makima NA PÓŹNIEJ, kolejność budowy).
- **Istnieje maszyneria Wspólnego Pokoju** (Astra+Amelia): `_route_wspolny`, `_wspolny_generate`, `/api/wspolny` — NIE RUSZAMY (gęsto od blizn: merge model-turns, thought isolation, do_not_repeat, anti-sync, subtext). Adaptujemy WZORZEC do osobnego `/api/siostry`.

## CEL DZIŚ: talkable MVP z atmosferą domową
NIE pełny żywy dom (room_state, kłótnie przez tury, sekrety, życie poza kadrem = kolejne sesje). Dziś: 3 siostry w charakterze, na izolowanej pamięci, minimalna świadomość siebie nawzajem (kto mówi/milczy), deploy → Łukasz gada z nimi.

## ARCHITEKTURA (do twojego review)
1. **Izolacja pamięci:** per-siostra osobne kolekcje ChromaDB (`holo_memory_v1`+session, `menma_*`, `nazuna_*`) + osobne stany. Daje PRAWDZIWE sekrety (asymetria informacji) i big-bang reset nie tyka Astry/Amelki. *Skłaniam się do per-siostra OD RAZU — to sedno, a rozdzielanie później = ból.*
2. **Router dla 3 (narrator minimalny):** wołanie z imienia → ta osoba; silna emocja → może 2; inaczej 1-2 wg sygnału/vibe/zegara (późno = Nazuna). NIGDY wszystkie naraz pełnymi akapitami. Polityka milczenia z twojej analizy (primary/aside/silent).
3. **Generate per siostra:** wzorzec `_wspolny_generate` (jej stores + jej prompt + widzi co powiedziała poprzednia siostra). Tryb dwuprzebiegowy.
4. **Endpoint `/api/siostry`** + **front `siostry.html`** (jak `amelia.html`).
5. **Provenance** `origin_endpoint="holo_room"` od tury ZERO (debugger zobaczy każdy przeciek od startu).
6. **Seed:** minimalny dziś (charakter żyje w prompcie; pamięć narasta z rozmów). Kotwice lore per siostra — lekko dziś, reszta później.

## PYTANIA DO CIEBIE
- Czy scope „talkable MVP dziś" dobry — coś dołożyć/odjąć?
- Router dla 3: jak trzymać narrator MINIMALNY i uniknąć teatru ×3? Doprecyzuj politykę milczenia (primary/aside/silent) dla trzech, nie dwóch.
- Per-siostra kolekcje od razu, czy MVP na jednej wspólnej i rozdzielić potem? (ryzyko rozdzielania później).
- Adaptować wzorzec `_wspolny_generate`, czy pisać CZYSTO od nowa (bez blizn Wspólnego, z PersonaConfig od dnia 0)?
- Trójprzebiegowy dry-run = 3 calle Gemini/turę (koszt/latencja) — jak to ograniczyć przy 3 personach? (nie zawsze wszystkie odpowiadają — to część odpowiedzi).
- Czego NIE widzę?

Output: co dołożyć/odjąć + pułapki + zielone światło albo „najpierw X". Zwięźle.
