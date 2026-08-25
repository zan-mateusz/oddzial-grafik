"""Treść instrukcji obsługi.

Trzymana w kodzie, a nie w osobnym pliku, żeby zawsze była dostępna także
w wersji spakowanej do jednego pliku .exe. Z tego samego źródła powstaje plik
INSTRUKCJA.md w repozytorium (tools/export_manual.py).
"""
from __future__ import annotations

TITLE = "Instrukcja obsługi programu Grafik"

INTRO = """
<p>Program służy do układania miesięcznych grafików dyżurów na oddziale
i do automatycznego liczenia godzin: wypracowanych, nocnych, świątecznych,
urlopowych oraz nadgodzin.</p>
<p>Instrukcja jest podzielona na rozdziały widoczne po lewej stronie.
Pole <b>Szukaj</b> odnajduje słowo w całym tekście.</p>
"""

SECTIONS: list[tuple[str, str, str]] = [

("start", "Pierwsze kroki", """
<h2>Pierwsze kroki</h2>
<p>Po pierwszym uruchomieniu program jest pusty — nie ma jeszcze żadnych
pracowników ani dyżurów. Kolejność działań jest następująca:</p>
<ol>
<li>Przejdź na zakładkę <b>Pracownicy</b> i dodaj zespół przyciskiem
    <b>Dodaj</b>. Przy osobach zatrudnionych na część etatu wybierz właściwy
    wymiar — program uwzględni go przy liczeniu godzin.</li>
<li>Jeśli oddział ma dwa piętra, przypisz każdą osobę do właściwego piętra.</li>
<li>Wejdź w <b>Narzędzia → Ustawienia</b> i wpisz nazwę oddziału. Pojawi się
    ona na wydruku.</li>
<li>Zajrzyj na zakładkę <b>Zasady</b> i sprawdź, czy pora nocna oraz norma
    dobowa zgadzają się z regulaminem pracy na Twoim oddziale.</li>
<li>Wróć na zakładkę <b>Grafik</b> i układaj dyżury.</li>
</ol>
<p>Jeżeli masz dotychczasowy grafik w Excelu albo w LibreOffice, nie musisz
przepisywać go ręcznie — użyj <b>Plik → Importuj z pliku Excel</b>.
Program sam założy brakujących pracowników.</p>
<p><b>Nie ma przycisku „Zapisz”.</b> Każda zmiana zapisuje się natychmiast.</p>
"""),

("okno", "Co jest gdzie", """
<h2>Co jest gdzie</h2>
<p>Program ma cztery zakładki:</p>
<table>
<tr><th>Zakładka</th><th>Do czego służy</th></tr>
<tr><td><b>Grafik</b></td><td>Układanie dyżurów. Główne miejsce pracy.</td></tr>
<tr><td><b>Pracownicy</b></td><td>Dodawanie i edytowanie osób, etaty, piętra,
    kolejność wierszy w grafiku.</td></tr>
<tr><td><b>Zmiany</b></td><td>Definicje kodów dyżurów: godziny, kolory,
    rodzaj wpisu.</td></tr>
<tr><td><b>Zasady</b></td><td>Reguły liczenia godzin wraz z podstawą prawną.</td></tr>
</table>
<p>Na zakładce <b>Grafik</b> od góry znajdują się kolejno: wybór miesiąca
i piętra, pasek z kodami dyżurów do szybkiego wypełniania, sama tabela,
a pod nią podsumowanie miesiąca.</p>
<p>Po prawej stronie tabeli są kolumny z podsumowaniem każdej osoby.
Opisano je w rozdziale <b>Podsumowanie godzin</b>.</p>
"""),

("wpisy", "Wpisywanie dyżurów", """
<h2>Wpisywanie dyżurów</h2>
<p>Kliknij komórkę i zacznij pisać. Nie trzeba nic wcześniej zaznaczać ani
zatwierdzać — wystarczy wpisać treść i nacisnąć <b>Enter</b> albo przejść
do następnej komórki.</p>

<h3>Dyżury całodobowe</h3>
<table>
<tr><th>Wpis</th><th>Znaczenie</th></tr>
<tr><td><code>D</code></td><td>dyżur dzienny, domyślnie 7:00–19:00</td></tr>
<tr><td><code>N</code></td><td>dyżur nocny, domyślnie 19:00–7:00</td></tr>
</table>

<h3>Dyżury krótsze</h3>
<p>Wpisz sam czas trwania. Przecinek i kropka działają tak samo jak dwukropek
— oddzielają minuty, a nie części godziny:</p>
<table>
<tr><th>Wpis</th><th>Znaczenie</th></tr>
<tr><td><code>7:30</code></td><td>7 godzin 30 minut</td></tr>
<tr><td><code>7,3</code></td><td>to samo — 7 godzin 30 minut</td></tr>
<tr><td><code>7,35</code></td><td>7 godzin 35 minut</td></tr>
<tr><td><code>10</code></td><td>10 godzin</td></tr>
<tr><td><code>6:45</code></td><td>6 godzin 45 minut</td></tr>
</table>
<p><b>Program pokazuje, jak zrozumiał wpis.</b> Piszesz <code>7,3</code>,
a w komórce pojawia się <code>7:30</code>. Dzięki temu od razu widać,
czy liczba jest ta, o którą chodziło.</p>
<p>Dyżur podany samym czasem trwania nie ma godziny rozpoczęcia, więc nie
wlicza się do pory nocnej. Jeżeli ma się liczyć, podaj przedział godzin —
np. <code>22-6</code>.</p>

<h3>Przedziały godzin</h3>
<p>Można też wpisać dyżur od–do: <code>8-14</code>, <code>7:30-19:30</code>,
<code>0700-1900</code>. Dyżur kończący się wcześniej, niż się zaczyna,
traktowany jest jako nocny i przechodzi przez północ.</p>

<h3>Nieobecności</h3>
<table>
<tr><th>Wpis</th><th>Znaczenie</th></tr>
<tr><td><code>U</code></td><td>urlop wypoczynkowy</td></tr>
<tr><td><code>UŻ</code></td><td>urlop na żądanie</td></tr>
<tr><td><code>L4</code></td><td>zwolnienie lekarskie</td></tr>
<tr><td><code>OP</code></td><td>opieka nad dzieckiem</td></tr>
<tr><td><code>W</code></td><td>dzień wolny (zwykle wystarczy pusta komórka)</td></tr>
</table>
<p><b>Dzień wolny zostaw pusty</b> — tak jak w zwykłym arkuszu.</p>
<p>Wielkość liter nie ma znaczenia: <code>d</code> znaczy to samo co
<code>D</code>.</p>

<h3>Wpis nierozpoznany</h3>
<p>Jeżeli program nie rozumie wpisu, pokazuje go <b>na czerwono</b>, na
różowym tle. Takie godziny <b>nie są liczone</b>. Najczęstsza przyczyna to
literówka w kodzie. Liczba nierozpoznanych wpisów widnieje też pod tabelą.</p>
"""),

("szybko", "Szybkie wypełnianie", """
<h2>Szybkie wypełnianie</h2>
<p>Wpisywanie dyżurów po jednym trwa długo. Szybciej jest tak:</p>
<ul>
<li><b>Zaznacz kilka komórek</b> myszką (przeciągnij) i kliknij przycisk
    kodu na pasku nad tabelą — wszystkie wypełnią się naraz.</li>
<li><b>Prawy przycisk myszy</b> na zaznaczeniu otwiera tę samą listę kodów.</li>
<li><b>Delete</b> czyści zaznaczone komórki.</li>
<li><b>Grafik → Kopiuj układ z poprzedniego miesiąca</b> przenosi cały
    rozkład dyżurów. Potem wystarczy poprawić weekendy i święta.</li>
</ul>
<p class="warn">Uwaga przy kopiowaniu z poprzedniego miesiąca: dni tygodnia
wypadają inaczej, więc dyżur, który był w sobotę, po skopiowaniu może wypaść
w środku tygodnia. Zawsze sprawdź weekendy i święta.</p>
"""),

("kolory", "Kolory i oznaczenia", """
<h2>Kolory i oznaczenia</h2>
<h3>Nagłówki dni</h3>
<table>
<tr><th>Kolor</th><th>Znaczenie</th></tr>
<tr><td>jasnoniebieski</td><td>sobota</td></tr>
<tr><td>ciemniejszy niebieski</td><td>niedziela</td></tr>
<tr><td>różowy</td><td>święto ustawowo wolne od pracy</td></tr>
</table>
<p>Najedź myszką na nagłówek, aby zobaczyć nazwę święta. Kolory służą tylko
lepszej widoczności — dyżury w te dni planuje się normalnie.</p>

<h3>Komórki</h3>
<table>
<tr><th>Wygląd</th><th>Znaczenie</th></tr>
<tr><td>kolor kodu, pogrubiony</td><td>zwykły dyżur</td></tr>
<tr><td>żółtawe tło</td><td>dyżur wpisany godzinowo, np. <code>7:30</code></td></tr>
<tr><td>czerwony tekst na różowym tle</td><td>wpis nierozpoznany — sprawdź pisownię</td></tr>
<tr><td>szara kursywa</td><td>dyżur na innym piętrze (patrz rozdział o piętrach)</td></tr>
</table>

<h3>Wiersze</h3>
<p>Nazwisko wypisane <b>pomarańczową kursywą ze strzałką ↻</b> oznacza osobę
z innego piętra, wpisaną tu na zastępstwo.</p>
"""),

("pietra", "Dwa piętra i zastępstwa", """
<h2>Dwa piętra i zastępstwa</h2>
<p>Każde piętro ma <b>własny grafik i własny skład</b>. Przełączasz je listą
<b>Piętro</b> nad tabelą. Pracownika przypisujesz do piętra na zakładce
<b>Pracownicy</b>.</p>
<p>Jeśli oddział ma tylko jedno piętro, lista w ogóle się nie pokazuje,
a kolumny opisane niżej znikają.</p>

<h3>Wpisanie zastępstwa</h3>
<ol>
<li>Przejdź na grafik tego piętra, na którym dyżur ma się odbyć.</li>
<li>Kliknij <b>Dodaj zastępstwo…</b> i wybierz osobę z listy. Możesz zaznaczyć
    kilka osób naraz.</li>
<li>Wpisz jej dyżur tak samo jak wszystkim pozostałym.</li>
</ol>
<p>Osoba pojawi się w grafiku pomarańczową kursywą, z nazwą swojego piętra.</p>

<h3>Zabezpieczenie przed podwójnym dyżurem</h3>
<p>Jeżeli ktoś ma danego dnia dyżur na <b>drugim</b> piętrze, jego komórka
pokazuje ten dyżur <b>szarą kursywą</b>. Dzięki temu widać, że ta osoba jest
już zajęta, i nie da się jej przez pomyłkę wpisać drugiego dyżuru tego samego
dnia. Najedź myszką, aby zobaczyć, na którym piętrze pracuje.</p>
<p>Wpisanie czegoś w taką szarą komórkę <b>przenosi</b> dyżur na oglądane
piętro — jedna osoba ma jeden dyżur dziennie.</p>

<h3>Czyszczenie</h3>
<p>Usunięcie zawartości komórki kasuje dyżur <b>tylko z oglądanego piętra</b>.
Dyżur na drugim piętrze zostaje nietknięty.</p>

<h3>Godziny osoby pracującej na dwóch piętrach</h3>
<p>Kolumna <b>Dyż. gł.</b> pokazuje dyżury na macierzystym piętrze pracownika,
a <b>Dyż. zast.</b> — te odbyte na innym piętrze. Podział zależy od osoby,
a nie od tego, który grafik masz otwarty, więc na obu piętrach widać te same
liczby. Razem dają wszystkie dyżury w miesiącu.</p>
<p><b>Wymiar</b> i <b>Bilans</b> obejmują cały miesiąc niezależnie od piętra —
pracownik ma jedną umowę i jeden wymiar czasu pracy. Pełny opis wszystkich
kolumn znajdziesz w rozdziale <b>Podsumowanie godzin</b>.</p>

<h3>Nazwy pięter</h3>
<p>Zmienisz je w <b>Narzędzia → Ustawienia</b>. Tam też dodasz trzecie piętro,
gdyby było potrzebne.</p>
"""),

("podsumowanie", "Podsumowanie godzin", """
<h2>Podsumowanie godzin</h2>
<p>Kolumny po prawej stronie tabeli przeliczają się same po każdej zmianie
w grafiku. Większość podaje <b>liczbę dni i łączny czas</b> w postaci
<code>14 (168:00)</code> — czternaście dyżurów, razem 168 godzin.</p>

<table>
<tr><th>Kolumna</th><th>Co pokazuje</th></tr>
<tr><td><b>Wymiar</b></td><td>ile godzin przypada do przepracowania w tym
    miesiącu, po uwzględnieniu etatu, świąt, urlopów i zwolnień</td></tr>
<tr><td><b>Dyż. gł.</b></td><td>dyżury na własnym piętrze pracownika</td></tr>
<tr><td><b>Dyż. zast.</b></td><td>dyżury na innym piętrze, czyli zastępstwa</td></tr>
<tr><td><b>Bilans</b></td><td>nadgodziny na pomarańczowo, niedogodziny na
    czerwono, równo na zielono</td></tr>
<tr><td><b>Dzień</b></td><td>dyżury dzienne</td></tr>
<tr><td><b>Noc</b></td><td>dyżury nocne, czyli sięgające pory nocnej</td></tr>
<tr><td><b>Święta</b></td><td>dyżury w święta ustawowo wolne od pracy</td></tr>
<tr><td><b>Urlop</b></td><td>zużyty urlop i odpowiadający mu czas pracy</td></tr>
<tr><td><b>L4</b></td><td>zwolnienie lekarskie — kolumna pojawia się tylko
    wtedy, gdy w danym miesiącu jest jakiś taki wpis</td></tr>
</table>

<h3>Dyżury własne i zastępcze</h3>
<p>Podział zależy od <b>pracownika</b>, a nie od tego, który grafik masz
otwarty. Dyżur odbyty na macierzystym piętrze liczy się jako własny, każdy inny
jako zastępstwo — i wygląda tak samo niezależnie od oglądanego piętra.
Razem dają wszystkie dyżury w miesiącu.</p>
<p>Przy jednym piętrze podział nie ma sensu i zostaje jedna kolumna
<b>Dyżury</b>.</p>

<h3>Dzień i noc</h3>
<p>Dyżur uznawany jest za nocny, jeżeli sięga pory nocnej ustawionej na
zakładce <b>Zasady</b> (domyślnie 22:00–6:00). Dyżur <code>N</code> jest więc
nocny, <code>D</code> dzienny, a wpis podany samym czasem trwania
(np. <code>7:30</code>) liczy się jako dzienny, bo nie wiadomo, o której się
zaczyna.</p>
<p>Podpowiedź nad kolumną <b>Noc</b> pokazuje dodatkowo, ile godzin przypadło
na samą porę nocną — to ta liczba jest podstawą dodatku.</p>

<h3>Podpowiedzi</h3>
<p>Najedź myszką na dowolną komórkę podsumowania, a zobaczysz szczegóły:
przyjętą porę nocną, liczbę dyżurów niedzielnych, liczbę pominiętych wpisów
urlopowych albo rozbicie bilansu na godziny wypracowane i wymiar.</p>

<p>Pod tabelą widać liczbę osób w grafiku, sumę godzin, listę świąt w tym
miesiącu oraz obsadę dnia wskazanego kursorem.</p>
"""),

("zasady", "Zasady liczenia godzin", """
<h2>Zasady liczenia godzin</h2>
<p>Zakładka <b>Zasady</b> pokazuje wszystkie reguły, według których program
przelicza grafik na godziny, każdą z podstawą prawną. Można je zmienić, jeśli
na oddziale obowiązują inne ustalenia. Zmiana działa od razu na wszystkich
grafikach, także tych z przeszłości.</p>

<h3>Norma dobowa</h3>
<p>Dla pracowników podmiotów leczniczych wynosi <b>7 godzin 35 minut</b>
(art. 93 ust. 1 ustawy o działalności leczniczej). Poza ochroną zdrowia
obowiązuje 8 godzin.</p>

<h3>Wymiar czasu pracy w miesiącu</h3>
<p>Liczba dni od poniedziałku do piątku pomnożona przez normę dobową,
pomniejszona o każde święto przypadające w dniu innym niż niedziela
(art. 130 § 1 i 2 Kodeksu pracy).</p>
<p class="warn">Święto obniża wymiar <b>także wtedy, gdy ktoś tego dnia
pracuje</b>. Wypracowane wówczas godziny stają się nadgodzinami albo odbiera
się je w innym terminie. To nie jest błąd programu — tak działa przepis.</p>

<h3>Pora nocna</h3>
<p>Kodeks pracy mówi, że pora nocna obejmuje <b>8 godzin mieszczących się
między 21:00 a 7:00</b>, a konkretne godziny ustala pracodawca w regulaminie
pracy (art. 151⁷ § 1). Program przyjmuje <b>22:00–6:00</b>.</p>
<p>Przy tym ustawieniu dyżur nocny 19:00–7:00 daje <b>8 godzin</b> pory
nocnej, a nie 12. Jeśli w regulaminie Twojego oddziału jest inny przedział,
zmień godzinę początkową — koniec wyliczy się sam, bo okno zawsze trwa
8 godzin.</p>

<h3>Urlop</h3>
<p>Urlopu udziela się <b>tylko w dni, które są dla pracownika dniami pracy</b>
(art. 154² § 1). Dlatego wpis <code>U</code> postawiony w sobotę, niedzielę
albo święto <b>nie zużywa urlopu</b>.</p>
<p>Przykład: <code>U</code> wpisane przez 15 kolejnych dni kalendarzowych,
począwszy od poniedziałku, to <b>11 dni urlopu</b> — dwa pełne tygodnie po
pięć dni roboczych plus jeden dzień. Gdyby w tym okresie wypadło święto,
byłoby to 10 dni.</p>
<p>Każdy zużyty dzień urlopu odpowiada normie dobowej i o tyle obniża wymiar
czasu pracy (art. 130 § 3), więc urlop nie tworzy sztucznych niedogodzin.
Tak samo liczone jest zwolnienie lekarskie.</p>

<h3>Praca w niedziele i święta</h3>
<p>Za pracę w niedzielę lub święto przysługuje inny dzień wolny, a gdy jest to
niemożliwe — dodatek (art. 151¹¹). Program zlicza te godziny osobno,
w kolumnie <b>Święta</b> oraz w podpowiedzi nad nią.</p>
"""),

("pracownicy", "Pracownicy", """
<h2>Pracownicy</h2>
<p>Zakładka <b>Pracownicy</b> zawiera listę całego zespołu.</p>
<table>
<tr><th>Przycisk</th><th>Działanie</th></tr>
<tr><td><b>Dodaj</b></td><td>nowa osoba</td></tr>
<tr><td><b>Edytuj</b></td><td>zmiana danych (można też kliknąć dwukrotnie wiersz)</td></tr>
<tr><td><b>Zakończ pracę</b></td><td>osoba znika z nowych grafików, ale
    wszystkie dotychczasowe wpisy zostają</td></tr>
<tr><td><b>Usuń trwale</b></td><td>kasuje osobę <b>razem z całą historią</b></td></tr>
<tr><td><b>▲ ▼</b></td><td>kolejność wierszy w grafiku</td></tr>
</table>
<p class="warn">Gdy ktoś odchodzi z pracy, używaj <b>Zakończ pracę</b>, a nie
<b>Usuń trwale</b>. Zachowasz wtedy dawne grafiki w komplecie. Trwałego
usunięcia nie da się cofnąć.</p>
<p>Zaznacz <b>Pokaż byłych pracowników</b>, aby zobaczyć również osoby,
które już nie pracują.</p>

<h3>Etat</h3>
<p>Przy zatrudnieniu na część etatu wybierz odpowiedni wymiar (np. 1/2, 3/4).
Program proporcjonalnie zmniejszy wymiar czasu pracy tej osoby, więc bilans
nadgodzin będzie liczony prawidłowo.</p>

<h3>Daty zatrudnienia</h3>
<p>Pola <b>Zatrudniona od</b> i <b>do</b> są nieobowiązkowe. Jeśli je
wypełnisz, osoba pojawi się tylko w grafikach z tego okresu.</p>
"""),

("zmiany", "Definicje zmian", """
<h2>Definicje zmian</h2>
<p>Zakładka <b>Zmiany</b> zawiera listę kodów, których używasz w grafiku.
Każdy kod ma nazwę, godziny, rodzaj i kolor.</p>
<p>Możesz dodawać własne kody, zmieniać godziny istniejących i dobierać
kolory. Kolory przenoszą się na wydruk.</p>

<h3>Rodzaj wpisu</h3>
<table>
<tr><th>Rodzaj</th><th>Jak liczy się do godzin</th></tr>
<tr><td><b>Praca</b></td><td>godziny wliczają się do wypracowanych</td></tr>
<tr><td><b>Urlop</b></td><td>zużywa urlop i obniża wymiar</td></tr>
<tr><td><b>Zwolnienie</b></td><td>obniża wymiar</td></tr>
<tr><td><b>Nieobecność</b></td><td>nie liczy się do godzin ani nie obniża wymiaru</td></tr>
<tr><td><b>Wolne</b></td><td>dzień wolny, zero godzin</td></tr>
</table>
<p>Zmiana kończąca się o godzinie wcześniejszej niż początek jest traktowana
jako nocna i przechodzi przez północ — np. 19:00–7:00 to 12 godzin.</p>
<p class="warn">Usunięcie kodu nie kasuje wpisów w dawnych grafikach, ale
przestaną być rozpoznawane i pokażą się na czerwono. Program ostrzeże,
ile razy dany kod został użyty.</p>
"""),

("import", "Wczytanie grafiku z pliku", """
<h2>Wczytanie grafiku z pliku</h2>
<p><b>Plik → Importuj z pliku Excel</b> wczytuje gotowy grafik z arkusza.
Obsługiwane są pliki <code>.xlsx</code> (Excel) oraz <code>.ods</code>
(LibreOffice, OpenOffice).</p>

<h3>Co program robi sam</h3>
<ul>
<li>wybiera arkusz zawierający grafik, pomijając puste;</li>
<li>odczytuje miesiąc z nazwy arkusza (np. „CZERWIEC”);</li>
<li>odnajduje wiersz z numerami dni i kolumnę z nazwiskami;</li>
<li>pomija numerację porządkową nazwisk („1. Kowalska”);</li>
<li>pomija nagłówki sekcji i puste pozycje na liście;</li>
<li>dopasowuje nazwiska do osób już wpisanych do programu.</li>
</ul>

<h3>Co sprawdzić</h3>
<p>W oknie importu widać podgląd arkusza z zaznaczonymi na żółto numerami dni
i na niebiesko kolumną nazwisk. Jeśli program trafił źle, popraw numery
w polach <b>Położenie danych</b> — podgląd od razu się odświeży.</p>
<h3>Dopasowanie nazwisk</h3>
<p>Na dole okna widać, do kogo trafi każdy wiersz. Kolumna <b>Uwaga</b> mówi,
na ile pewne jest dopasowanie:</p>
<table>
<tr><th>Uwaga</th><th>Znaczenie</th></tr>
<tr><td>puste</td><td>zgadza się całe imię i nazwisko</td></tr>
<tr><td>dopasowano po nazwisku</td><td>w arkuszu był zapis skrócony,
    np. „Kowalska A." — warto rzucić okiem</td></tr>
<tr><td>nowy pracownik</td><td>takiej osoby nie ma jeszcze w programie,
    zostanie założona</td></tr>
<tr><td>pasuje kilka osób</td><td>trzeba wskazać, o którą chodzi</td></tr>
</table>
<p>Program nigdy nie połączy dwóch osób o tym samym nazwisku, ale różnych
imionach: <b>Dejnek Aneta</b> i <b>Dejnek Dorota</b> pozostaną osobnymi
pracownikami. Jeżeli w arkuszu jest samo nazwisko, a na oddziale są dwie takie
osoby, program o tym powie i poprosi o wybór zamiast zgadywać.</p>
<p>Przy kilku piętrach wskaż jeszcze, <b>na które piętro</b> wczytać dane.
Grafik pozostałych pięter pozostanie nietknięty.</p>
<p class="warn">Zaznaczona opcja <b>Zastąp istniejące wpisy</b> usuwa
dotychczasowy grafik wybranego miesiąca i piętra. Jeśli chcesz tylko dołożyć
dane, odznacz ją.</p>
"""),

("zdjecie", "Wczytanie ze zdjęcia", """
<h2>Wczytanie ze zdjęcia</h2>
<p><b>Plik → Importuj ze zdjęcia</b> odczytuje tabelę z fotografii grafiku.
Działa tak samo jak wczytywanie z pliku — trafia do tego samego okna
z podglądem.</p>
<p>Funkcja wymaga dodatkowego programu <b>Tesseract OCR</b>. Jeśli nie jest
zainstalowany, program powie, skąd go pobrać. Wczytywanie z Excela działa
niezależnie od tego dodatku.</p>

<h3>Jak zrobić dobre zdjęcie</h3>
<ul>
<li>fotografuj prosto z góry, nie pod kątem;</li>
<li>zadbaj o równomierne światło, bez cienia ręki i bez odblasku;</li>
<li>cała tabela musi mieścić się w kadrze i być ostra.</li>
</ul>
<p class="warn">Odczyt ze zdjęcia bywa niedokładny — program potrafi pomylić
podobne znaki. <b>Zawsze przejrzyj podgląd</b> przed zapisaniem, a po imporcie
sprawdź, czy w grafiku nie ma czerwonych wpisów.</p>
"""),

("eksport", "Wydruk i eksport", """
<h2>Wydruk i eksport</h2>
<p><b>Plik → Eksportuj do Excela</b> zapisuje grafik do pliku
<code>.xlsx</code>, gotowego do wydruku: układ poziomy, format A4,
powtarzany nagłówek na każdej stronie i legenda kolorów pod tabelą.</p>
<p>Każde piętro trafia na <b>osobną kartę</b> w tym samym pliku.</p>
<p>Plik otworzysz zarówno w Excelu, jak i w LibreOffice oraz OpenOffice.
Aby wydrukować, otwórz go i użyj polecenia drukowania w tym programie.</p>
<p>Podsumowania w wyeksportowanym pliku są zwykłymi liczbami, więc można je
dowolnie kopiować i przetwarzać dalej.</p>
"""),

("kopie", "Kopie zapasowe", """
<h2>Kopie zapasowe</h2>
<p>Grafiki zapisują się automatycznie, a co kilka dni program <b>sam robi
kopię zapasową</b> przy uruchomieniu. Przechowuje piętnaście najnowszych.</p>
<table>
<tr><th>Polecenie</th><th>Działanie</th></tr>
<tr><td><b>Plik → Utwórz kopię zapasową</b></td><td>zapisuje kopię w tej chwili</td></tr>
<tr><td><b>Plik → Przywróć z kopii</b></td><td>wraca do wybranej kopii</td></tr>
</table>
<p>Przed przywróceniem program i tak zapisze kopię stanu bieżącego, więc
operacja jest odwracalna. Po przywróceniu program zamyka się — uruchom go
ponownie.</p>
<p>Wszystkie dane leżą w jednym katalogu; jego ścieżkę widać na dole okna.
Przed zmianą komputera skopiuj cały ten katalog.</p>
"""),

("aktualizacja", "Aktualizacja programu", """
<h2>Aktualizacja programu</h2>
<p>Program sam sprawdza, czy jest nowsza wersja — najwyżej raz dziennie,
w tle, zaraz po uruchomieniu. Gdy coś znajdzie, pokaże okno z opisem zmian
i pytaniem, czy pobrać.</p>

<h3>Gdy pojawi się pytanie o aktualizację</h3>
<ol>
<li>Przeczytaj, co się zmieniło.</li>
<li>Kliknij <b>Pobierz i zainstaluj</b>. Pasek pokaże postęp pobierania.</li>
<li>Po pobraniu kliknij <b>Zainstaluj i uruchom ponownie</b>. Program zamknie
    się, a instalator zrobi resztę i uruchomi nową wersję.</li>
</ol>
<p>Jeżeli wybierzesz <b>Nie teraz</b>, program nie będzie o tę wersję pytał
ponownie — zapyta dopiero, gdy pojawi się następna. W każdej chwili możesz
sprawdzić samodzielnie: <b>Pomoc → Sprawdź aktualizacje</b>.</p>

<h3>Czy stracę grafiki</h3>
<p><b>Nie.</b> Aktualizacja zmienia wyłącznie sam program. Grafiki, pracownicy,
definicje zmian i ustawienia leżą w innym miejscu i pozostają nietknięte.</p>
<p>Gdyby nowa wersja musiała zmienić sposób zapisu danych, zrobi to sama,
powiadomi Cię o tym i <b>zostawi kopię sprzed aktualizacji</b>.</p>

<h3>Usunięcie danych po testach</h3>
<p>Jeżeli program był używany do prób i trzeba zacząć od czysta, wybierz
<b>Narzędzia → Usuń wszystkie dane</b>. Można usunąć same grafiki — zostawiając
pracowników i ustawienia — albo wszystko, wracając do stanu jak zaraz po
instalacji.</p>
<p>Przed usunięciem program sam zapisze kopię zapasową, więc operację da się
cofnąć przez <b>Plik → Przywróć z kopii</b>.</p>

<h3>Wersja przenośna</h3>
<p>Jeśli używasz wersji przenośnej (jeden plik, bez instalacji), program też
pobierze nową wersję, ale podmienić plik trzeba samodzielnie: zamknij program
i zastąp stary plik pobranym. Przycisk <b>Pokaż pobrany plik</b> otworzy
katalog, w którym się znajduje.</p>

<h3>Bezpieczeństwo</h3>
<p>Pobrany plik jest sprawdzany sumą kontrolną opublikowaną razem z wydaniem.
Jeżeli się nie zgadza, program go <b>nie uruchomi</b> i poprosi o ponowną
próbę.</p>

<h3>Kiedy program sprawdza</h3>
<p>Przy każdym uruchomieniu, w tle, chwilę po otwarciu okna — ale nie częściej
niż raz na godzinę. Gdy nowszej wersji nie ma, na pasku na dole pojawia się
na moment potwierdzenie, że sprawdzenie się odbyło.</p>
<p>Jeśli chcesz sprawdzić natychmiast — <b>Pomoc → Sprawdź aktualizacje</b>.
To polecenie działa zawsze, niezależnie od tego, kiedy program sprawdzał
ostatnio, i mówi wprost, gdy czegoś nie da się pobrać.</p>
<p>Datę i wynik ostatniego sprawdzenia widać w <b>Pomoc → O programie</b>.</p>

<h3>Wyłączenie sprawdzania</h3>
<p>W <b>Narzędzia → Ustawienia</b> możesz odznaczyć <b>Sprawdzaj aktualizacje
przy uruchomieniu</b>. Program przestanie wtedy łączyć się z internetem;
sprawdzenie ręczne z menu nadal będzie działać.</p>

<p class="warn">Nie wracaj do starszej wersji programu po tym, jak nowsza
przebudowała dane — starszy program odmówi otwarcia pliku, żeby go nie
uszkodzić.</p>
"""),

("klawisze", "Skróty klawiszowe", """
<h2>Skróty klawiszowe</h2>
<table>
<tr><th>Skrót</th><th>Działanie</th></tr>
<tr><td><b>F1</b></td><td>ta instrukcja</td></tr>
<tr><td><b>Delete</b></td><td>wyczyszczenie zaznaczonych komórek</td></tr>
<tr><td><b>Ctrl + ←</b> / <b>Ctrl + →</b></td><td>poprzedni / następny miesiąc</td></tr>
<tr><td><b>Ctrl + E</b></td><td>eksport do Excela</td></tr>
<tr><td><b>Ctrl + I</b></td><td>import z pliku</td></tr>
<tr><td><b>Ctrl + Q</b></td><td>zamknięcie programu</td></tr>
<tr><td><b>Enter</b></td><td>zatwierdzenie wpisu w komórce</td></tr>
<tr><td><b>Esc</b></td><td>porzucenie zmiany w komórce</td></tr>
<tr><td>strzałki</td><td>przechodzenie po komórkach</td></tr>
</table>
<p>Aby zacząć pisać w komórce, wystarczy zaznaczyć ją i wpisać treść —
nie trzeba klikać dwukrotnie.</p>
"""),

("problemy", "Najczęstsze pytania", """
<h2>Najczęstsze pytania</h2>

<h3>Wpis jest czerwony</h3>
<p>Program nie rozpoznał treści komórki i nie liczy tych godzin. Sprawdź
pisownię kodu na zakładce <b>Zmiany</b> albo wpisz czas trwania,
np. <code>7:30</code>.</p>

<h3>Bilans pokazuje nadgodziny, choć grafik wygląda normalnie</h3>
<p>Najczęściej w miesiącu wypadło święto. Święto obniża wymiar czasu pracy
także wtedy, gdy ktoś tego dnia pracuje, więc godziny stają się nadgodzinami.
Sprawdź listę świąt pod tabelą.</p>

<h3>Liczba dni urlopu nie zgadza się z liczbą wpisów</h3>
<p>To prawidłowe. Urlopu udziela się tylko w dni pracy, więc <code>U</code>
wpisane w sobotę, niedzielę lub święto nie zużywa urlopu. Najedź myszką na
kolumnę <b>Urlop</b>, aby zobaczyć, ile wpisów pominięto.</p>

<h3>Godziny nocne wydają się za małe</h3>
<p>Liczy się tylko ta część dyżuru, która przypada na porę nocną — domyślnie
22:00–6:00. Dyżur 19:00–7:00 daje 8 godzin nocnych, nie 12. Przedział
zmienisz na zakładce <b>Zasady</b>.</p>

<h3>Ktoś nie pojawia się w grafiku</h3>
<p>Sprawdź, czy jest przypisany do właściwego piętra, czy ma zaznaczone
<b>Pracuje obecnie</b> i czy daty zatrudnienia obejmują ten miesiąc.</p>

<h3>Nie widzę listy pięter</h3>
<p>Pokazuje się dopiero wtedy, gdy piętra są co najmniej dwa. Dodasz je
w <b>Narzędzia → Ustawienia</b>.</p>

<h3>Program pyta o zastąpienie wpisów przy imporcie</h3>
<p>Zaznaczona opcja <b>Zastąp istniejące wpisy</b> usuwa dotychczasowy grafik
wybranego miesiąca i piętra. Odznacz ją, jeśli chcesz tylko dołożyć dane.</p>

<h3>Program pyta o aktualizację przy każdym uruchomieniu</h3>
<p>Nie powinien. Jeśli raz wybierzesz <b>Nie teraz</b>, o tę wersję już nie
zapyta. Ponowne pytanie oznacza, że pojawiła się kolejna nowa wersja.
Sprawdzanie można wyłączyć w <b>Narzędzia → Ustawienia</b>.</p>

<h3>Aktualizacja nie działa</h3>
<p>Sprawdź w <b>Narzędzia → Ustawienia</b>, czy wypełnione jest pole
<b>Adres aktualizacji</b>. Bez niego program nie wie, skąd pobierać nowe
wersje. Potrzebne jest też połączenie z internetem.</p>

<h3>Chcę usunąć dane testowe i zacząć od nowa</h3>
<p><b>Narzędzia → Usuń wszystkie dane</b>. Wybierz, czy skasować same grafiki,
czy wszystko razem z pracownikami i ustawieniami. Kopia zapasowa powstanie
automatycznie.</p>

<h3>Gdzie są moje dane</h3>
<p>Ścieżkę do pliku widać na pasku na dole okna. Kopie zapasowe leżą
w podkatalogu <code>kopie</code>.</p>
"""),
]
