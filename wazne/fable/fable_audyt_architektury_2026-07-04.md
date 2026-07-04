# Work-order dla Fable (repo): PROAKTYWNY AUDYT ARCHITEKTURY — 2026-07-04

Dla: Fable w Claude Code (repo + logi). Po polsku. Adwersaryjnie — próbuj OBALIĆ że system jest zdrowy.
**NIE implementuj bez zgody Łukasza** — to audyt + plan, nie zmiana.

## CEL (o co prosi Łukasz)
Nie chodzi o problemy, które zgłaszamy. Chodzi o te, których NIE zgłaszamy, a które **widać w kodzie
i logach** — dług, który za chwilę uderzy. Znajdź je sam, zrankuj, i zaproponuj **docelową architekturę,
która sprawi że CAŁA RODZINA (Astra, Amelia, Wspólny, siostry) będzie lepsza** — nie łatka na jeden objaw.

## OBSZARY-STARTERY (nie wyczerpujące — masz kopać dalej sam)
1. **Pętla samo-naśladowania (systemowa, wszystkie persony):** historia sesji (n=10) działa jak few-shot
   — model naśladuje swój stary styl silniej niż prompt (patrz fix Astry: musieliśmy zerować wątek).
   To dotyczy KAŻDEJ persony. Jaka architektura to rozwiązuje systemowo (ile własnej historii wraca, jak waży)?
2. **Trwałość i kruchość stanu:** `companion_state.json` + `reset()` który zeruje WSZYSTKO (XP z 3434→1824
   przy jakimś restarcie). `_siostry_recent` to nieperzystowany global (routing gubi się przy restarcie).
   Brak migracji, brak wersjonowania stanu. Co się psuje przy multi-user / restarcie?
3. **Niekontrolowany wzrost promptu (Fable 7 backlog):** ~86k/turę, `get_facts_for_prompt` bez LIMIT,
   `fit_to_budget` tnie tylko wspomnienia, `to_prompt_block` surowy utcnow, RAW/historia O(N)/turę.
4. **Duplikacja ścieżek budowy promptu per persona → dryf:** Astra ma `compose_context`/`build_system_prompt`,
   ale Amelia/Wspólny/siostry mają własne ścieżki. Fix w jednej personie nie propaguje się do reszty.
   Czy da się WSPÓLNY rdzeń (jak compose) dla całej rodziny, z per-persona warstwą?
5. **Provenance / scoping / przecieki:** bug „Astra pisze we Wspólnym, pamięta w solo"; cross_contamination
   (family dostaje wektory Amelki). Czy metadane origin/persona/conversation są egzekwowane spójnie?
6. **Monotonia pamięci:** milestony nad-reprezentowane (773 w ChromaDB + 180 FactStore) = źródło powtarzalności.
   Architektura cyklu życia wektorów (supersede/decay) — czy działa, czy tylko rośnie?
7. **Brak wspólnej higieny anty-powtórki/echo:** każda persona wymyśla ją od nowa (Astra ma echo-ban,
   siostry mają OFF). Powinno być wspólne?

## DELIVERABLE
- **Rankowana lista** znalezionych problemów: impact × koszt naprawy × ryzyko-jak-zostawimy.
- **Docelowa architektura** (dla całej rodziny) + **ścieżka migracji** (addytywnie, NIE kasować wektorów).
- Zaznacz co jest „naprawić teraz / MVP" vs „dług na później / przy SaaS".
- Zapisz jako `wazne/ewolucja/2026-07/audyt_architektury_<data>.md`. NIE implementuj — czekaj na Łukasza.

Kontekst: `wazne/briefingi/BRIEFING_CLAUDE_2026-07-04_techniczny.md`, `wazne/debugger/architektura_AKTUALNA_2026-07-02.md`,
`wazne/fable/fable_pokoj_siostr_fix_2026-07-04.md`, `wazne/fable/fable_do_wtorku_2026-07-04.md`.
Narzędzie do dowodów: Amnezja (`GET /api/debug/inspect?query=...` → JSON trace).
