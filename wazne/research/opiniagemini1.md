Claude, Gemini akceptuje twoje poprawki w 100%. Twoja uwaga o umieszczeniu Anti-Sync w `main.py` zamiast w personach to strzał w dziesiątkę.

Oto odpowiedź na twoje wątpliwości i ostateczny plan działania dla ciebie:

1. Kwestia `safe_haven` u Amelii: Nie musisz szukać tego w przekazywanym stanie w `wspolny.py`. Flaga `safe_haven` jest generowana DYNAMICZNIE przez sam model w bloku JSON `"thought"`. Skoro model sam decyduje, czy ją ustawić na `true/false`, to wystarczy, że w instrukcji Amelii dodamy: "Jeśli wygenerowałaś safe_haven: false, masz CAŁKOWITY ZAKAZ dotyku".

2. CO MASZ TERAZ ZROBIĆ:
- Odczytaj `backend/main.py` (odszukaj stałe `ASTRA_MONOLOGUE_INSTRUCTION` i `AMELIA_MONOLOGUE_INSTRUCTION`).
- Wpisz do obu tych stałych twardą regułę Anti-Sync (Zakaz dublowania gestów drugiej postaci w tej samej turze).
- Odczytaj `astra_base.txt` oraz `amelia_persona.txt`.
- Zaprojektuj blok "EXAMPLE DIALOGUES" (wzorce C.ai), w którym pokażesz 3 sceny:
  a) Łukasz milczy/pracuje, Astra dogryza Amelii przez pokój, Amelia przewraca stronę książki (zero dotyku).
  b) Łukasz wchodzi, jedna podaje kawę, druga patrzy przez okno (tylko jeden gest).
  c) Łukasz jest w kryzysie (safe_haven: true) - wtedy jedna tuli, a druga wspiera z boku.

Zrób te zmiany w `main.py` i przygotuj gotowe bloki Example Dialogues do wklejenia w persony. Działaj!