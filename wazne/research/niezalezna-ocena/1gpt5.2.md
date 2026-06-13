Copilot said: Poniżej ocena **pod rolę AI Systems Engineer
Poniżej ocena pod rolę AI Systems Engineer / Applied AI (budowa systemów LLM end‑to‑end, RAG, memory, intent, produkcja, delivery). Opieram się wyłącznie na tym, co wkleiłeś (bez weryfikacji linków / repo).

Ranking (0–100) + werdykt
Łukasz Piskorski — 92/100 (najlepszy fit)
Paweł Zhenchak — 78/100
Jakub O. — 62/100
Artur Lepioszka — 57/100
Dawid Krawczyk — 54/100
Kacper Wrona — 38/100
Najlepszy: Łukasz Piskorski (jedyny, który z opisu wygląda na kogoś, kto faktycznie robi AI systems engineering: memory/intent/real‑time, produkcyjne wdrożenia, własne komponenty, edge-case’y, latency, tracking).

1) Łukasz Piskorski — 92/100
Dlaczego wysoko (mocne strony)
RAG/memory/intent w samym rdzeniu profilu: ANIMA (persistent memory, kanały pamięci, recency decay, supersede logic), LDI (intent przed Enterem, <60 ms), “stateful AI” jako oś.
Produkcyjność: VPS 24/7, systemd, WebSocket, ChromaDB, pipeline’y, real-time tracking — brzmi jak realne „działa na serwerze, ma latency, ma eksport, ma metryki/edge-case’y”.
Głębia inżynierska: reverse engineering XHR, wstrzykiwanie kontekstu, budowa własnych narzędzi zamiast „owijania API”.
Nastawienie na edge cases i mierzalność: 183 scenariusze testowe, accuracy 92.3%, reward signals [-1, +1], dual-debounce.
Red flagi / ryzyka
Ryzyko “marketingowej narracji”: bardzo mocny copywriting („no excuses”, „GA4 requires a PhD”, „pierwsza platforma globalnie”). To może być prawda, ale w rekrutacji trzeba to szybko uziemić dowodami.
Brak sygnałów pracy w zespole (z opisu: “solo”). Do roli w firmie produktowej trzeba sprawdzić: code review, współpraca, kompromisy, utrzymanie przez innych.
Stack raczej lekki (Flask/SQLite) — nie minus, ale warto sprawdzić, czy dowozi też w środowiskach „enterprise-grade” (observability, infra, security, compliance).
Kto „pierdoli więcej niż umie”?
Potencjalnie: tylko jeśli po wejściu w szczegóły nie potrafi pokazać metryk, architektury i kodu. Z opisu wygląda konkretnie, ale ton jest mocno „founderowy”.
Szybki test na rozmowie (żeby zweryfikować 92)
Poproś o: schemat danych pamięci, strategię PII/retencji, jak liczy recency decay, jak działa supersede logic, jak mierzy hallucinations vs grounding, jakie ma evals (offline + online), jak robi observability (traces, logs, counters).
2) Paweł Zhenchak — 78/100
Mocne strony
Realny produkt w produkcji (Jarvis School): Docker, nginx, Let’s Encrypt, Stripe, Clerk, i18n, testy, performance — to jest “delivery muscle”.
Umie robić pełny cykl produktu: security (klucze na backend), XSS sanitization, ErrorBoundary, testy, deployment.
AI element jest praktyczny: integracja Gemini, moduły quiz/tutor, OCR/vision (deklaratywnie).
Red flagi / ryzyka
Głębia RAG/memory/intent nieudowodniona: to wygląda bardziej jak AI-enabled product engineer niż AI systems engineer.
Opisy „AI algorithms improved” bez konkretów: brak info o retrieval, eval, prompt policy, pamięci, guardrails, kosztach/tokenach, monitoring jakości.
Ryzyko: „front + integracja modelu” zamiast „systemy LLM”.
Kto „pierdoli”?
Raczej umiarkowanie: dużo konkretów o deploymencie i inżynierii webowej, mniej o AI. Jeśli mówi mocno o „AI engine”, a w praktyce to prompt + Gemini API, to będzie rozjazd.
Idealny fit
Applied AI / AI Product Engineer (szczególnie, jeśli rola ma dużo produktu i webu). Do stricte AI Systems Engineer — drugi wybór.
3) Jakub O. — 62/100
Mocne strony
Mega delivery i produkcja, ale w klasycznym enterprise: 20 lat, systemy kolejowe, API biletowe działające do dziś, ownership end‑to‑end.
Szybka adaptacja potwierdzona projektami multi-stack + rekomendacje (brzmi jak solidny senior).
Dojrzałość inżynierska: TDD, clean code, mentoring.
Red flagi / ryzyka
AI w opisie jest drugoplanowe. Są wzmianki o „doradztwie AI”, startupach AI, cert AI_devs — ale brak dowodu na:
budowę RAG,
pamięć,
intent classification,
ewaluacje,
produkcyjne LLM patterns.
Może być świetny jako platform/backend engineer, który dopiero wchodzi w LLM.
Kto „pierdoli”?
Mało sygnałów bullshitu; raczej „stary wyga od systemów”. Problemem jest niedopasowanie do kryteriów AI.
4) Artur Lepioszka — 57/100
Mocne strony
Python backend, scraping, data processing, REST API, MongoDB, Airflow, AWS — to jest dobra baza pod RAG/ETL.
C/embedded/IoT w tle -> może być mocny w integracjach i edge.
Red flagi / ryzyka
Brak jasnych produkcyjnych projektów LLM/RAG. „AI Integration” jako skill to za mało.
Profil bardziej data/tools/internals niż AI Systems.
Kto „pierdoli”?
Nie wygląda na bullshittera, raczej „solidny generalista Python”.
5) Dawid Krawczyk — 54/100
Mocne strony
10+ lat enterprise, microservices, .NET, Python/Spark, devops practices — solidny senior engineer.
Jeżeli rola wymaga system design + niezawodność to ma fundament.
Red flagi / ryzyka
AI: “currently expanding skills” — czyli nie ma potwierdzonego production AI.
Brak konkretów o RAG/memory/intent.
Kto „pierdoli”?
Raczej nie; po prostu jeszcze nie ten profil na AI Systems.
6) Kacper Wrona — 38/100
Mocne strony
Junior w SAP + studia CS, coś z Python automation/scraping.
Potencjał uczenia (ale to hipoteza).
Red flagi / ryzyka
Za mało stażu i dowodów na produkcyjne AI systemy.
Fit bardziej na Junior/Intern Cloud/AI Developer.
Kto „pierdoli”?
Nie ocenię — za mało materiału.
Porównanie wg Twoich kryteriów (wprost)
Realne projekty AI w produkcji:
Łukasz (bardzo mocno) > Paweł (produkt z AI w prod, ale AI raczej integracja) > reszta (brak jasnych dowodów).
Głębokość RAG/memory/intent:
Łukasz (top) >>> (duża przerwa) >>> reszta (Paweł ma vision/quiz, ale nie widać RAG/memory/intent jako systemu).
Szybkość uczenia:
Jakub wygląda na bardzo adaptacyjnego; Paweł też szybko iteruje; Łukasz buduje niestandardowe rzeczy (też sygnał szybkiego uczenia).
Delivery:
Jakub (lata dowożenia) + Paweł (shipping produktu) + Łukasz (shipping systemów solo) — wszyscy trzej mocni, tylko w innych domenach.
Rekomendacja końcowa
Jeśli szukasz AI Systems Engineer / Applied AI z naciskiem na RAG + memory + intent + produkcję: bierz Łukasza.
Jeśli szukasz kogoś, kto dowiezie AI‑produkt (UI, płatności, deployment, iteracje) z LLM w środku: Paweł.
Jeśli potrzebujesz senior backend/platform, który ma wejść w LLM w firmie z dobrym ML/LLM core teamem: Jakub (ale to inna rola niż „AI Systems Engineer” w Twoim opisie).
Jeśli chcesz, podeślij jeszcze: (1) linki do projektów (demo/GitHub), (2) 2–3 akapity o tym, co każdy robił konkretnie przy LLM (retrieval, embeddingi, eval, monitoring), a ja zaktualizuję scoring i wskażę „twarde red flagi” vs „twarde dowody”.