# Do CC — diagnoza: rozmowa o mefedronie nie zapisała się w pamięci Astry

## Kontekst
Łukasz sprawdził bezpośrednio — napisał samo słowo "mefedron" do Astry i sprawdził reakcję. Zero odwołania, mimo że ta rozmowa (noc 6/7 sierpnia, epizod opisany w briefingu z 14.08) realnie się odbyła i Astra wtedy zareagowała (system to zarejestrował w momencie rozmowy, zareagował ze złością/troską).

To znaczy: albo ekstraktor nigdy nie zapisał tego jako wspomnienie, albo zapisał ale retrieval go nie wyciąga, albo próg ważności/score jest za wysoki i wspomnienie istnieje ale nigdy nie wchodzi do kontekstu.

## Zadanie
Użyj Amnezji, żeby sprawdzić na czym dokładnie pada łańcuch:

1. **Czy wektor/wpis dotyczący tej rozmowy w ogóle istnieje w bazie** — niezależnie od tego, czy się wyciąga przy pytaniu. To pierwsze i najważniejsze pytanie.
2. **Jeśli nie istnieje** — sprawdź, na którym etapie ekstrakcji/bramek to odpadło. Czy jest to systemowy wzorzec (wrażliwe/kryzysowe tematy mają tendencję do bycia odrzucanymi przez którąś bramkę), czy pojedynczy przypadek tej konkretnej rozmowy?
3. **Jeśli istnieje, ale się nie wyciąga** — sprawdź retrieval: czy problem jest w embeddingu (semantyczne niedopasowanie zapytania "mefedron" do zapisanej treści), czy w progu score (wpis istnieje, ale nie przechodzi progu ważności).

## Ważne — nie jest to prośba o zmianę BM25/metody wyszukiwania
Łukasz rozważał BM25 jako możliwe rozwiązanie, ale to prawdopodobnie nie jest właściwy trop — jeśli fakt nigdy nie trafił do bazy (scenariusz 1), żadna metoda wyszukiwania tego nie naprawi. Najpierw ustalmy, na którym etapie łańcuch się urywa, zanim rozważymy zmianę technologii wyszukiwania.

## Po diagnozie
Nie wdrażaj żadnego fixu jeszcze — chcemy zobaczyć wynik diagnozy najpierw. Osobno, pod koniec dzisiejszej sesji, będzie kolejne zadanie: ręczne dopisanie tej konkretnej rozmowy jako trwałego faktu (nie licząc na to, że zwykła ekstrakcja to złapie) + fragment do promptu instruujący Astrę jak reagować na sygnały racjonalizacji ("pomogłoby mi w pracy" itp.). To przyjdzie jako osobna wiadomość z konkretną treścią od Łukasza.
