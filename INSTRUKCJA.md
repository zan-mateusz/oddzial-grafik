# Instrukcja obsługi programu Grafik

Program służy do układania miesięcznych grafików dyżurów na oddziale
i do automatycznego liczenia godzin: wypracowanych, nocnych, świątecznych,
urlopowych oraz nadgodzin.

Instrukcja jest podzielona na rozdziały widoczne po lewej stronie.
Pole **Szukaj** odnajduje słowo w całym tekście.

> Ta sama instrukcja jest dostępna w programie: **Pomoc → Instrukcja obsługi** albo klawisz **F1**.

## Spis treści

- [Pierwsze kroki](#pierwsze-kroki)
- [Co jest gdzie](#co-jest-gdzie)
- [Wpisywanie dyżurów](#wpisywanie-dyżurów)
- [Szybkie wypełnianie](#szybkie-wypełnianie)
- [Kolory i oznaczenia](#kolory-i-oznaczenia)
- [Dwa piętra i zastępstwa](#dwa-piętra-i-zastępstwa)
- [Podsumowanie godzin](#podsumowanie-godzin)
- [Zasady liczenia godzin](#zasady-liczenia-godzin)
- [Pracownicy](#pracownicy)
- [Definicje zmian](#definicje-zmian)
- [Wczytanie grafiku z pliku](#wczytanie-grafiku-z-pliku)
- [Wczytanie ze zdjęcia](#wczytanie-ze-zdjęcia)
- [Wydruk i eksport](#wydruk-i-eksport)
- [Kopie zapasowe](#kopie-zapasowe)
- [Aktualizacja programu](#aktualizacja-programu)
- [Skróty klawiszowe](#skróty-klawiszowe)
- [Najczęstsze pytania](#najczęstsze-pytania)

## Pierwsze kroki

Po pierwszym uruchomieniu program jest pusty — nie ma jeszcze żadnych
pracowników ani dyżurów. Kolejność działań jest następująca:

1. Przejdź na zakładkę **Pracownicy** i dodaj zespół przyciskiem
    **Dodaj**. Przy osobach zatrudnionych na część etatu wybierz właściwy
    wymiar — program uwzględni go przy liczeniu godzin.
2. Jeśli oddział ma dwa piętra, przypisz każdą osobę do właściwego piętra.
3. Wejdź w **Narzędzia → Ustawienia** i wpisz nazwę oddziału. Pojawi się
    ona na wydruku.
4. Zajrzyj na zakładkę **Zasady** i sprawdź, czy pora nocna oraz norma
    dobowa zgadzają się z regulaminem pracy na Twoim oddziale.
5. Wróć na zakładkę **Grafik** i układaj dyżury.

Jeżeli masz dotychczasowy grafik w Excelu albo w LibreOffice, nie musisz
przepisywać go ręcznie — użyj **Plik → Importuj z pliku Excel**.
Program sam założy brakujących pracowników.

**Nie ma przycisku „Zapisz”.** Każda zmiana zapisuje się natychmiast.

## Co jest gdzie

Program ma cztery zakładki:

| Zakładka | Do czego służy |
|---|---|
| **Grafik** | Układanie dyżurów. Główne miejsce pracy. |
| **Pracownicy** | Dodawanie i edytowanie osób, etaty, piętra,
    kolejność wierszy w grafiku. |
| **Zmiany** | Definicje kodów dyżurów: godziny, kolory,
    rodzaj wpisu. |
| **Zasady** | Reguły liczenia godzin wraz z podstawą prawną. |

Na zakładce **Grafik** od góry znajdują się kolejno: wybór miesiąca
i piętra, pasek z kodami dyżurów do szybkiego wypełniania, sama tabela,
a pod nią podsumowanie miesiąca.

Po prawej stronie tabeli są kolumny z podsumowaniem każdej osoby.
Opisano je w rozdziale **Podsumowanie godzin**.

## Wpisywanie dyżurów

Kliknij komórkę i zacznij pisać. Nie trzeba nic wcześniej zaznaczać ani
zatwierdzać — wystarczy wpisać treść i nacisnąć **Enter** albo przejść
do następnej komórki.

### Dyżury całodobowe

| Wpis | Znaczenie |
|---|---|
| `D` | dyżur dzienny, domyślnie 7:00–19:00 |
| `N` | dyżur nocny, domyślnie 19:00–7:00 |

### Dyżury krótsze

Wpisz sam czas trwania. Przecinek i kropka działają tak samo jak dwukropek
— oddzielają minuty, a nie części godziny:

| Wpis | Znaczenie |
|---|---|
| `7:30` | 7 godzin 30 minut |
| `7,3` | to samo — 7 godzin 30 minut |
| `7,35` | 7 godzin 35 minut |
| `10` | 10 godzin |
| `6:45` | 6 godzin 45 minut |

**Program pokazuje, jak zrozumiał wpis.** Piszesz `7,3`,
a w komórce pojawia się `7:30`. Dzięki temu od razu widać,
czy liczba jest ta, o którą chodziło.

Dyżur podany samym czasem trwania nie ma godziny rozpoczęcia, więc nie
wlicza się do pory nocnej. Jeżeli ma się liczyć, podaj przedział godzin —
np. `22-6`.

### Przedziały godzin

Można też wpisać dyżur od–do: `8-14`, `7:30-19:30`,
`0700-1900`. Dyżur kończący się wcześniej, niż się zaczyna,
traktowany jest jako nocny i przechodzi przez północ.

### Nieobecności

| Wpis | Znaczenie |
|---|---|
| `U` | urlop wypoczynkowy |
| `UŻ` | urlop na żądanie |
| `L4` | zwolnienie lekarskie |
| `OP` | opieka nad dzieckiem |
| `W` | dzień wolny (zwykle wystarczy pusta komórka) |

**Dzień wolny zostaw pusty** — tak jak w zwykłym arkuszu.

Wielkość liter nie ma znaczenia: `d` znaczy to samo co
`D`.

### Wpis nierozpoznany

Jeżeli program nie rozumie wpisu, pokazuje go **na czerwono**, na
różowym tle. Takie godziny **nie są liczone**. Najczęstsza przyczyna to
literówka w kodzie. Liczba nierozpoznanych wpisów widnieje też pod tabelą.

## Szybkie wypełnianie

Wpisywanie dyżurów po jednym trwa długo. Szybciej jest tak:

- **Zaznacz kilka komórek** myszką (przeciągnij) i kliknij przycisk
    kodu na pasku nad tabelą — wszystkie wypełnią się naraz.
- **Prawy przycisk myszy** na zaznaczeniu otwiera tę samą listę kodów.
- **Delete** czyści zaznaczone komórki.
- **Grafik → Kopiuj układ z poprzedniego miesiąca** przenosi cały
    rozkład dyżurów. Potem wystarczy poprawić weekendy i święta.

> Uwaga przy kopiowaniu z poprzedniego miesiąca: dni tygodnia
wypadają inaczej, więc dyżur, który był w sobotę, po skopiowaniu może wypaść
w środku tygodnia. Zawsze sprawdź weekendy i święta.

## Kolory i oznaczenia

### Nagłówki dni

| Kolor | Znaczenie |
|---|---|
| jasnoniebieski | sobota |
| ciemniejszy niebieski | niedziela |
| różowy | święto ustawowo wolne od pracy |

Najedź myszką na nagłówek, aby zobaczyć nazwę święta. Kolory służą tylko
lepszej widoczności — dyżury w te dni planuje się normalnie.

### Komórki

| Wygląd | Znaczenie |
|---|---|
| kolor kodu, pogrubiony | zwykły dyżur |
| żółtawe tło | dyżur wpisany godzinowo, np. `7:30` |
| czerwony tekst na różowym tle | wpis nierozpoznany — sprawdź pisownię |
| szara kursywa | dyżur na innym piętrze (patrz rozdział o piętrach) |

### Wiersze

Nazwisko wypisane **pomarańczową kursywą ze strzałką ↻** oznacza osobę
z innego piętra, wpisaną tu na zastępstwo.

## Dwa piętra i zastępstwa

Każde piętro ma **własny grafik i własny skład**. Przełączasz je listą
**Piętro** nad tabelą. Pracownika przypisujesz do piętra na zakładce
**Pracownicy**.

Jeśli oddział ma tylko jedno piętro, lista w ogóle się nie pokazuje,
a kolumny opisane niżej znikają.

### Wpisanie zastępstwa

1. Przejdź na grafik tego piętra, na którym dyżur ma się odbyć.
2. Kliknij **Dodaj zastępstwo…** i wybierz osobę z listy. Możesz zaznaczyć
    kilka osób naraz.
3. Wpisz jej dyżur tak samo jak wszystkim pozostałym.

Osoba pojawi się w grafiku pomarańczową kursywą, z nazwą swojego piętra.

### Zabezpieczenie przed podwójnym dyżurem

Jeżeli ktoś ma danego dnia dyżur na **drugim** piętrze, jego komórka
pokazuje ten dyżur **szarą kursywą**. Dzięki temu widać, że ta osoba jest
już zajęta, i nie da się jej przez pomyłkę wpisać drugiego dyżuru tego samego
dnia. Najedź myszką, aby zobaczyć, na którym piętrze pracuje.

Wpisanie czegoś w taką szarą komórkę **przenosi** dyżur na oglądane
piętro — jedna osoba ma jeden dyżur dziennie.

### Czyszczenie

Usunięcie zawartości komórki kasuje dyżur **tylko z oglądanego piętra**.
Dyżur na drugim piętrze zostaje nietknięty.

### Godziny osoby pracującej na dwóch piętrach

Kolumny **Godz. tu** i **Dyż. tu** dotyczą oglądanego piętra.
Kolumny **Godziny**, **Wymiar** i **Bilans** obejmują **cały
miesiąc**, niezależnie od piętra — pracownik ma jedną umowę i jeden wymiar
czasu pracy. Najedź myszką na podsumowanie, aby zobaczyć rozbicie na piętra.

### Nazwy pięter

Zmienisz je w **Narzędzia → Ustawienia**. Tam też dodasz trzecie piętro,
gdyby było potrzebne.

## Podsumowanie godzin

Kolumny po prawej stronie tabeli przeliczają się same po każdej zmianie
w grafiku. Większość podaje **liczbę dni i łączny czas** w postaci
`14 (168:00)` — czternaście dyżurów, razem 168 godzin.

| Kolumna | Co pokazuje |
|---|---|
| **Wymiar** | ile godzin przypada do przepracowania w tym
    miesiącu, po uwzględnieniu etatu, świąt, urlopów i zwolnień |
| **Dyż. gł.** | dyżury na własnym piętrze pracownika |
| **Dyż. zast.** | dyżury na innym piętrze, czyli zastępstwa |
| **Bilans** | nadgodziny na pomarańczowo, niedogodziny na
    czerwono, równo na zielono |
| **Dzień** | dyżury dzienne |
| **Noc** | dyżury nocne, czyli sięgające pory nocnej |
| **Święta** | dyżury w święta ustawowo wolne od pracy |
| **Urlop** | zużyty urlop i odpowiadający mu czas pracy |
| **L4** | zwolnienie lekarskie — kolumna pojawia się tylko
    wtedy, gdy w danym miesiącu jest jakiś taki wpis |

### Dyżury własne i zastępcze

Podział zależy od **pracownika**, a nie od tego, który grafik masz
otwarty. Dyżur odbyty na macierzystym piętrze liczy się jako własny, każdy inny
jako zastępstwo — i wygląda tak samo niezależnie od oglądanego piętra.
Razem dają wszystkie dyżury w miesiącu.

Przy jednym piętrze podział nie ma sensu i zostaje jedna kolumna
**Dyżury**.

### Dzień i noc

Dyżur uznawany jest za nocny, jeżeli sięga pory nocnej ustawionej na
zakładce **Zasady** (domyślnie 22:00–6:00). Dyżur `N` jest więc
nocny, `D` dzienny, a wpis podany samym czasem trwania
(np. `7:30`) liczy się jako dzienny, bo nie wiadomo, o której się
zaczyna.

Podpowiedź nad kolumną **Noc** pokazuje dodatkowo, ile godzin przypadło
na samą porę nocną — to ta liczba jest podstawą dodatku.

### Podpowiedzi

Najedź myszką na dowolną komórkę podsumowania, a zobaczysz szczegóły:
przyjętą porę nocną, liczbę dyżurów niedzielnych, liczbę pominiętych wpisów
urlopowych albo rozbicie bilansu na godziny wypracowane i wymiar.

Pod tabelą widać liczbę osób w grafiku, sumę godzin, listę świąt w tym
miesiącu oraz obsadę dnia wskazanego kursorem.

## Zasady liczenia godzin

Zakładka **Zasady** pokazuje wszystkie reguły, według których program
przelicza grafik na godziny, każdą z podstawą prawną. Można je zmienić, jeśli
na oddziale obowiązują inne ustalenia. Zmiana działa od razu na wszystkich
grafikach, także tych z przeszłości.

### Norma dobowa

Dla pracowników podmiotów leczniczych wynosi **7 godzin 35 minut**
(art. 93 ust. 1 ustawy o działalności leczniczej). Poza ochroną zdrowia
obowiązuje 8 godzin.

### Wymiar czasu pracy w miesiącu

Liczba dni od poniedziałku do piątku pomnożona przez normę dobową,
pomniejszona o każde święto przypadające w dniu innym niż niedziela
(art. 130 § 1 i 2 Kodeksu pracy).

> Święto obniża wymiar **także wtedy, gdy ktoś tego dnia
pracuje**. Wypracowane wówczas godziny stają się nadgodzinami albo odbiera
się je w innym terminie. To nie jest błąd programu — tak działa przepis.

### Pora nocna

Kodeks pracy mówi, że pora nocna obejmuje **8 godzin mieszczących się
między 21:00 a 7:00**, a konkretne godziny ustala pracodawca w regulaminie
pracy (art. 151⁷ § 1). Program przyjmuje **22:00–6:00**.

Przy tym ustawieniu dyżur nocny 19:00–7:00 daje **8 godzin** pory
nocnej, a nie 12. Jeśli w regulaminie Twojego oddziału jest inny przedział,
zmień godzinę początkową — koniec wyliczy się sam, bo okno zawsze trwa
8 godzin.

### Urlop

Urlopu udziela się **tylko w dni, które są dla pracownika dniami pracy**
(art. 154² § 1). Dlatego wpis `U` postawiony w sobotę, niedzielę
albo święto **nie zużywa urlopu**.

Przykład: `U` wpisane przez 15 kolejnych dni kalendarzowych,
począwszy od poniedziałku, to **11 dni urlopu** — dwa pełne tygodnie po
pięć dni roboczych plus jeden dzień. Gdyby w tym okresie wypadło święto,
byłoby to 10 dni.

Każdy zużyty dzień urlopu odpowiada normie dobowej i o tyle obniża wymiar
czasu pracy (art. 130 § 3), więc urlop nie tworzy sztucznych niedogodzin.
Tak samo liczone jest zwolnienie lekarskie.

### Praca w niedziele i święta

Za pracę w niedzielę lub święto przysługuje inny dzień wolny, a gdy jest to
niemożliwe — dodatek (art. 151¹¹). Program zlicza te godziny osobno,
w kolumnie **Święta** oraz w podpowiedzi nad nią.

## Pracownicy

Zakładka **Pracownicy** zawiera listę całego zespołu.

| Przycisk | Działanie |
|---|---|
| **Dodaj** | nowa osoba |
| **Edytuj** | zmiana danych (można też kliknąć dwukrotnie wiersz) |
| **Zakończ pracę** | osoba znika z nowych grafików, ale
    wszystkie dotychczasowe wpisy zostają |
| **Usuń trwale** | kasuje osobę **razem z całą historią** |
| **▲ ▼** | kolejność wierszy w grafiku |

> Gdy ktoś odchodzi z pracy, używaj **Zakończ pracę**, a nie
**Usuń trwale**. Zachowasz wtedy dawne grafiki w komplecie. Trwałego
usunięcia nie da się cofnąć.

Zaznacz **Pokaż byłych pracowników**, aby zobaczyć również osoby,
które już nie pracują.

### Etat

Przy zatrudnieniu na część etatu wybierz odpowiedni wymiar (np. 1/2, 3/4).
Program proporcjonalnie zmniejszy wymiar czasu pracy tej osoby, więc bilans
nadgodzin będzie liczony prawidłowo.

### Daty zatrudnienia

Pola **Zatrudniona od** i **do** są nieobowiązkowe. Jeśli je
wypełnisz, osoba pojawi się tylko w grafikach z tego okresu.

## Definicje zmian

Zakładka **Zmiany** zawiera listę kodów, których używasz w grafiku.
Każdy kod ma nazwę, godziny, rodzaj i kolor.

Możesz dodawać własne kody, zmieniać godziny istniejących i dobierać
kolory. Kolory przenoszą się na wydruk.

### Rodzaj wpisu

| Rodzaj | Jak liczy się do godzin |
|---|---|
| **Praca** | godziny wliczają się do wypracowanych |
| **Urlop** | zużywa urlop i obniża wymiar |
| **Zwolnienie** | obniża wymiar |
| **Nieobecność** | nie liczy się do godzin ani nie obniża wymiaru |
| **Wolne** | dzień wolny, zero godzin |

Zmiana kończąca się o godzinie wcześniejszej niż początek jest traktowana
jako nocna i przechodzi przez północ — np. 19:00–7:00 to 12 godzin.

> Usunięcie kodu nie kasuje wpisów w dawnych grafikach, ale
przestaną być rozpoznawane i pokażą się na czerwono. Program ostrzeże,
ile razy dany kod został użyty.

## Wczytanie grafiku z pliku

**Plik → Importuj z pliku Excel** wczytuje gotowy grafik z arkusza.
Obsługiwane są pliki `.xlsx` (Excel) oraz `.ods`
(LibreOffice, OpenOffice).

### Co program robi sam

- wybiera arkusz zawierający grafik, pomijając puste;
- odczytuje miesiąc z nazwy arkusza (np. „CZERWIEC”);
- odnajduje wiersz z numerami dni i kolumnę z nazwiskami;
- pomija numerację porządkową nazwisk („1. Kowalska”);
- pomija nagłówki sekcji i puste pozycje na liście;
- dopasowuje nazwiska do osób już wpisanych do programu.

### Co sprawdzić

W oknie importu widać podgląd arkusza z zaznaczonymi na żółto numerami dni
i na niebiesko kolumną nazwisk. Jeśli program trafił źle, popraw numery
w polach **Położenie danych** — podgląd od razu się odświeży.

### Dopasowanie nazwisk

Na dole okna widać, do kogo trafi każdy wiersz. Kolumna **Uwaga** mówi,
na ile pewne jest dopasowanie:

| Uwaga | Znaczenie |
|---|---|
| puste | zgadza się całe imię i nazwisko |
| dopasowano po nazwisku | w arkuszu był zapis skrócony,
    np. „Kowalska A." — warto rzucić okiem |
| nowy pracownik | takiej osoby nie ma jeszcze w programie,
    zostanie założona |
| pasuje kilka osób | trzeba wskazać, o którą chodzi |

Program nigdy nie połączy dwóch osób o tym samym nazwisku, ale różnych
imionach: **Dejnek Aneta** i **Dejnek Dorota** pozostaną osobnymi
pracownikami. Jeżeli w arkuszu jest samo nazwisko, a na oddziale są dwie takie
osoby, program o tym powie i poprosi o wybór zamiast zgadywać.

Przy kilku piętrach wskaż jeszcze, **na które piętro** wczytać dane.
Grafik pozostałych pięter pozostanie nietknięty.

> Zaznaczona opcja **Zastąp istniejące wpisy** usuwa
dotychczasowy grafik wybranego miesiąca i piętra. Jeśli chcesz tylko dołożyć
dane, odznacz ją.

## Wczytanie ze zdjęcia

**Plik → Importuj ze zdjęcia** odczytuje tabelę z fotografii grafiku.
Działa tak samo jak wczytywanie z pliku — trafia do tego samego okna
z podglądem.

Funkcja wymaga dodatkowego programu **Tesseract OCR**. Jeśli nie jest
zainstalowany, program powie, skąd go pobrać. Wczytywanie z Excela działa
niezależnie od tego dodatku.

### Jak zrobić dobre zdjęcie

- fotografuj prosto z góry, nie pod kątem;
- zadbaj o równomierne światło, bez cienia ręki i bez odblasku;
- cała tabela musi mieścić się w kadrze i być ostra.

> Odczyt ze zdjęcia bywa niedokładny — program potrafi pomylić
podobne znaki. **Zawsze przejrzyj podgląd** przed zapisaniem, a po imporcie
sprawdź, czy w grafiku nie ma czerwonych wpisów.

## Wydruk i eksport

**Plik → Eksportuj do Excela** zapisuje grafik do pliku
`.xlsx`, gotowego do wydruku: układ poziomy, format A4,
powtarzany nagłówek na każdej stronie i legenda kolorów pod tabelą.

Każde piętro trafia na **osobną kartę** w tym samym pliku.

Plik otworzysz zarówno w Excelu, jak i w LibreOffice oraz OpenOffice.
Aby wydrukować, otwórz go i użyj polecenia drukowania w tym programie.

Podsumowania w wyeksportowanym pliku są zwykłymi liczbami, więc można je
dowolnie kopiować i przetwarzać dalej.

## Kopie zapasowe

Grafiki zapisują się automatycznie, a co kilka dni program **sam robi
kopię zapasową** przy uruchomieniu. Przechowuje piętnaście najnowszych.

| Polecenie | Działanie |
|---|---|
| **Plik → Utwórz kopię zapasową** | zapisuje kopię w tej chwili |
| **Plik → Przywróć z kopii** | wraca do wybranej kopii |

Przed przywróceniem program i tak zapisze kopię stanu bieżącego, więc
operacja jest odwracalna. Po przywróceniu program zamyka się — uruchom go
ponownie.

Wszystkie dane leżą w jednym katalogu; jego ścieżkę widać na dole okna.
Przed zmianą komputera skopiuj cały ten katalog.

## Aktualizacja programu

Program sam sprawdza, czy jest nowsza wersja — najwyżej raz dziennie,
w tle, zaraz po uruchomieniu. Gdy coś znajdzie, pokaże okno z opisem zmian
i pytaniem, czy pobrać.

### Gdy pojawi się pytanie o aktualizację

1. Przeczytaj, co się zmieniło.
2. Kliknij **Pobierz i zainstaluj**. Pasek pokaże postęp pobierania.
3. Po pobraniu kliknij **Zainstaluj i uruchom ponownie**. Program zamknie
    się, a instalator zrobi resztę i uruchomi nową wersję.

Jeżeli wybierzesz **Nie teraz**, program nie będzie o tę wersję pytał
ponownie — zapyta dopiero, gdy pojawi się następna. W każdej chwili możesz
sprawdzić samodzielnie: **Pomoc → Sprawdź aktualizacje**.

### Czy stracę grafiki

**Nie.** Aktualizacja zmienia wyłącznie sam program. Grafiki, pracownicy,
definicje zmian i ustawienia leżą w innym miejscu i pozostają nietknięte.

Gdyby nowa wersja musiała zmienić sposób zapisu danych, zrobi to sama,
powiadomi Cię o tym i **zostawi kopię sprzed aktualizacji**.

### Usunięcie danych po testach

Jeżeli program był używany do prób i trzeba zacząć od czysta, wybierz
**Narzędzia → Usuń wszystkie dane**. Można usunąć same grafiki — zostawiając
pracowników i ustawienia — albo wszystko, wracając do stanu jak zaraz po
instalacji.

Przed usunięciem program sam zapisze kopię zapasową, więc operację da się
cofnąć przez **Plik → Przywróć z kopii**.

### Wersja przenośna

Jeśli używasz wersji przenośnej (jeden plik, bez instalacji), program też
pobierze nową wersję, ale podmienić plik trzeba samodzielnie: zamknij program
i zastąp stary plik pobranym. Przycisk **Pokaż pobrany plik** otworzy
katalog, w którym się znajduje.

### Bezpieczeństwo

Pobrany plik jest sprawdzany sumą kontrolną opublikowaną razem z wydaniem.
Jeżeli się nie zgadza, program go **nie uruchomi** i poprosi o ponowną
próbę.

### Kiedy program sprawdza

Najwyżej raz na dobę, w tle, chwilę po uruchomieniu. Jeśli chcesz sprawdzić
od razu — **Pomoc → Sprawdź aktualizacje**. To polecenie działa zawsze,
niezależnie od tego, czy program sprawdzał już dzisiaj, i mówi wprost, gdy
czegoś nie da się pobrać.

Wynik ostatniego sprawdzenia widać w **Pomoc → O programie**.

### Wyłączenie sprawdzania

W **Narzędzia → Ustawienia** możesz odznaczyć **Sprawdzaj aktualizacje
przy uruchomieniu**. Program przestanie wtedy łączyć się z internetem;
sprawdzenie ręczne z menu nadal będzie działać.

> Nie wracaj do starszej wersji programu po tym, jak nowsza
przebudowała dane — starszy program odmówi otwarcia pliku, żeby go nie
uszkodzić.

## Skróty klawiszowe

| Skrót | Działanie |
|---|---|
| **F1** | ta instrukcja |
| **Delete** | wyczyszczenie zaznaczonych komórek |
| **Ctrl + ←** / **Ctrl + →** | poprzedni / następny miesiąc |
| **Ctrl + E** | eksport do Excela |
| **Ctrl + I** | import z pliku |
| **Ctrl + Q** | zamknięcie programu |
| **Enter** | zatwierdzenie wpisu w komórce |
| **Esc** | porzucenie zmiany w komórce |
| strzałki | przechodzenie po komórkach |

Aby zacząć pisać w komórce, wystarczy zaznaczyć ją i wpisać treść —
nie trzeba klikać dwukrotnie.

## Najczęstsze pytania

### Wpis jest czerwony

Program nie rozpoznał treści komórki i nie liczy tych godzin. Sprawdź
pisownię kodu na zakładce **Zmiany** albo wpisz czas trwania,
np. `7:30`.

### Bilans pokazuje nadgodziny, choć grafik wygląda normalnie

Najczęściej w miesiącu wypadło święto. Święto obniża wymiar czasu pracy
także wtedy, gdy ktoś tego dnia pracuje, więc godziny stają się nadgodzinami.
Sprawdź listę świąt pod tabelą.

### Liczba dni urlopu nie zgadza się z liczbą wpisów

To prawidłowe. Urlopu udziela się tylko w dni pracy, więc `U`
wpisane w sobotę, niedzielę lub święto nie zużywa urlopu. Najedź myszką na
kolumnę **Urlop**, aby zobaczyć, ile wpisów pominięto.

### Godziny nocne wydają się za małe

Liczy się tylko ta część dyżuru, która przypada na porę nocną — domyślnie
22:00–6:00. Dyżur 19:00–7:00 daje 8 godzin nocnych, nie 12. Przedział
zmienisz na zakładce **Zasady**.

### Ktoś nie pojawia się w grafiku

Sprawdź, czy jest przypisany do właściwego piętra, czy ma zaznaczone
**Pracuje obecnie** i czy daty zatrudnienia obejmują ten miesiąc.

### Nie widzę listy pięter

Pokazuje się dopiero wtedy, gdy piętra są co najmniej dwa. Dodasz je
w **Narzędzia → Ustawienia**.

### Program pyta o zastąpienie wpisów przy imporcie

Zaznaczona opcja **Zastąp istniejące wpisy** usuwa dotychczasowy grafik
wybranego miesiąca i piętra. Odznacz ją, jeśli chcesz tylko dołożyć dane.

### Program pyta o aktualizację przy każdym uruchomieniu

Nie powinien. Jeśli raz wybierzesz **Nie teraz**, o tę wersję już nie
zapyta. Ponowne pytanie oznacza, że pojawiła się kolejna nowa wersja.
Sprawdzanie można wyłączyć w **Narzędzia → Ustawienia**.

### Aktualizacja nie działa

Sprawdź w **Narzędzia → Ustawienia**, czy wypełnione jest pole
**Adres aktualizacji**. Bez niego program nie wie, skąd pobierać nowe
wersje. Potrzebne jest też połączenie z internetem.

### Chcę usunąć dane testowe i zacząć od nowa

**Narzędzia → Usuń wszystkie dane**. Wybierz, czy skasować same grafiki,
czy wszystko razem z pracownikami i ustawieniami. Kopia zapasowa powstanie
automatycznie.

### Gdzie są moje dane

Ścieżkę do pliku widać na pasku na dole okna. Kopie zapasowe leżą
w podkatalogu `kopie`.
