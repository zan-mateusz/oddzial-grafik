# Grafik — instrukcja obsługi

## Pierwsze uruchomienie

1. Zainstaluj program i uruchom go skrótem **Grafik dyżurów**.
2. Przejdź na zakładkę **Pracownicy** i dodaj zespół (przycisk **Dodaj**).
   Przy osobach na część etatu wybierz odpowiedni wymiar — program uwzględni to
   przy liczeniu godzin.
3. Wróć na zakładkę **Grafik** i układaj dyżury.

W **Narzędzia → Ustawienia** wpisz nazwę oddziału (pojawi się na wydruku)
i sprawdź dobową normę czasu pracy — dla pielęgniarek jest to 7 godz. 35 min.

## Wpisywanie dyżurów

Kliknij komórkę i pisz.

**Dyżury całodobowe** — wpisz kod:

| Wpis | Znaczenie |
|---|---|
| `D` | dyżur dzienny 7:00–19:00 |
| `N` | dyżur nocny 19:00–7:00 |

**Dyżury krótsze** — wpisz sam czas trwania:

| Wpis | Znaczenie |
|---|---|
| `7:30` | 7 godzin 30 minut |
| `7,3` | to samo — przecinek działa jak dwukropek |
| `7,35` | 7 godzin 35 minut |
| `10` | 10 godzin |
| `6:45` | 6 godzin 45 minut |

Program wpisuje z powrotem odczytaną wartość — piszesz `7,3`, a w komórce
pojawia się `7:30`. Dzięki temu od razu widać, czy zrozumiał tak, jak trzeba.

**Nieobecności:**

| Wpis | Znaczenie |
|---|---|
| `U` | urlop wypoczynkowy |
| `UŻ` | urlop na żądanie |
| `L4` | zwolnienie lekarskie |
| `OP` | opieka nad dzieckiem |

**Dzień wolny zostaw pusty** — tak jak w dotychczasowym arkuszu.

Wielkość liter nie ma znaczenia — `d` znaczy to samo co `D`.

Pełną listę kodów zobaczysz na zakładce **Zmiany**. Możesz tam dodawać własne,
zmieniać godziny i kolory.

### Szybciej

- Zaznacz myszką kilka komórek i kliknij przycisk zmiany nad tabelą —
  wypełnią się wszystkie naraz.
- Prawy przycisk myszy na zaznaczeniu otwiera tę samą listę.
- Klawisz **Delete** czyści zaznaczone komórki.
- **Grafik → Kopiuj układ z poprzedniego miesiąca** przenosi cały rozkład;
  potem wystarczy poprawić weekendy i święta.

Wpis, którego program nie rozpoznał, wyświetla się **na czerwono** — to sygnał,
że jest literówka i te godziny nie są liczone.

## Kolory dni

- **Sobota i niedziela** — odcienie niebieskiego.
- **Święto ustawowe** — różowy. Najedź myszką na nagłówek, żeby zobaczyć nazwę.

Kolory są tylko po to, żeby te dni rzucały się w oczy przy układaniu obsady.
Dyżury planuje się w nie normalnie.

## Dwa piętra

Każde piętro ma osobny grafik i własny skład. Przełączasz je listą **Piętro**
nad tabelą. Pracownika przypisujesz do piętra na zakładce **Pracownicy**.

### Zastępstwa

Gdy ktoś z jednego piętra ma pracować na drugim:

1. Przejdź na grafik tego piętra, na którym ma być dyżur.
2. Kliknij **Dodaj zastępstwo…** i wybierz osobę z listy.
3. Wpisz jej dyżur tak samo jak wszystkim innym.

Osoby na zastępstwie widać kursywą, w kolorze pomarańczowym, ze strzałką ↻
i nazwą swojego piętra.

Jeśli ktoś ma tego dnia dyżur na **drugim** piętrze, jego komórka pokazuje ten
dyżur **na szaro**. To zabezpieczenie przed wpisaniem komuś dwóch dyżurów
jednocześnie. Wpisanie czegoś w taką komórkę przeniesie dyżur na oglądane
piętro.

Usunięcie zawartości komórki kasuje dyżur **tylko z oglądanego piętra** —
dyżur na drugim piętrze zostaje nietknięty.

Nazwy pięter zmienisz w **Narzędzia → Ustawienia**; tam też dodasz trzecie,
jeśli będzie potrzebne.

## Podsumowanie po prawej stronie

| Kolumna | Znaczenie |
|---|---|
| **Godz. tu** | godziny wypracowane **na oglądanym piętrze** |
| **Dyż. tu** | liczba dyżurów na oglądanym piętrze |
| **Godziny** | ile godzin wypracowano **w całym miesiącu**, razem z zastępstwami |
| **Wymiar** | ile godzin przypada do przepracowania (etat, urlopy, święta) |
| **Bilans** | nadgodziny na pomarańczowo, niedogodziny na czerwono |
| **Dyż.** | liczba dyżurów |
| **Noc** | godziny w porze nocnej (domyślnie 22:00–6:00) |
| **Święta** | godziny przepracowane w święta ustawowo wolne od pracy |
| **Urlop**, **L4** | liczba **zużytych** dni (patrz niżej) |

Wymiar zmniejsza się automatycznie za każde święto wypadające poza niedzielą
oraz za dni urlopu i zwolnienia.

Kolumny **Godziny**, **Wymiar** i **Bilans** liczą cały miesiąc niezależnie od
piętra — pracownik ma jedną umowę i jeden wymiar czasu pracy. Kolumny z „tu"
pokazują, ile z tego przypadło na oglądane piętro. Przy jednym piętrze kolumny
„tu" w ogóle się nie pojawiają.

## Zasady liczenia godzin

Zakładka **Zasady** pokazuje wszystkie reguły, według których program przelicza
grafik na godziny, razem z podstawą prawną. Każdą z nich można zmienić.

### Pora nocna

Kodeks pracy mówi, że pora nocna to **8 godzin mieszczących się między 21:00
a 7:00**, a konkretne godziny ustala pracodawca w regulaminie pracy
(art. 151⁷ § 1). Program przyjmuje **22:00–6:00**. Dyżur nocny 19:00–7:00 daje
przy tym ustawieniu 8 godzin pory nocnej — nie 12.

Jeśli na oddziale obowiązuje inny przedział, zmień godzinę początkową; koniec
wyliczy się sam, bo okno zawsze trwa 8 godzin.

### Urlop

Urlopu udziela się **tylko w dni, które są dla pracownika dniami pracy**
(art. 154² § 1). Dlatego wpis `U` postawiony w sobotę, niedzielę albo święto
**nie zużywa urlopu**.

Przykład: `U` wpisane przez 15 kolejnych dni kalendarzowych, od poniedziałku,
to **11 dni urlopu** — dwa pełne tygodnie po 5 dni roboczych plus jeden dzień.
Gdyby w tym okresie wypadło święto, byłoby to 10 dni.

Każdy zużyty dzień urlopu to **7 godz. 35 min** i o tyle obniża się wymiar
czasu pracy do przepracowania (art. 130 § 3). Dzięki temu urlop nie tworzy
sztucznych niedogodzin. W kolumnie **Urlop** widać liczbę zużytych dni;
najedź myszką, żeby zobaczyć, ile wpisów pominięto jako przypadające
w dni wolne.

Tak samo liczone jest zwolnienie lekarskie.

### Praca w święta

Godziny przepracowane w święta ustawowo wolne od pracy są zliczane w osobnej
kolumnie **Święta**, bo przysługuje za nie dzień wolny albo dodatek
(art. 151¹¹). Godziny niedzielne pokazuje podpowiedź nad tą kolumną.

Pamiętaj: święto obniża wymiar czasu pracy nawet wtedy, gdy ktoś tego dnia
pracuje — wypracowane godziny stają się wówczas nadgodzinami.

## Zapisywanie i wydruk

Dane zapisują się **automatycznie** — nie ma przycisku „Zapisz”.

**Plik → Eksportuj do Excela** tworzy arkusz gotowy do wydruku (poziomo, A4,
z legendą). Każde piętro trafia na osobną kartę w tym samym pliku. Otworzy się
w Excelu i w LibreOffice/OpenOffice.

## Wczytanie istniejącego grafiku

**Plik → Importuj z pliku Excel** — obsługuje pliki `.xlsx` oraz `.ods`
z LibreOffice/OpenOffice. Program sam wybiera arkusz z grafikiem (pomijając
puste), odczytuje miesiąc z jego nazwy i znajduje wiersz z numerami dni oraz
kolumnę z nazwiskami. Wskaż jeszcze, **na które piętro** wczytać dane —
grafik drugiego piętra pozostanie nietknięty. Jeśli trafi źle, popraw numery w polach *Położenie
danych*; podgląd od razu pokazuje, co zostanie wczytane. Na dole dopasujesz
nazwiska z pliku do pracowników w programie.

**Plik → Importuj ze zdjęcia** działa tak samo, tylko źródłem jest fotografia
tabeli. Wymaga dodatku Tesseract OCR — jeśli go nie ma, program powie, jak go
zainstalować. Odczyt ze zdjęcia bywa niedokładny, więc **zawsze przejrzyj
podgląd** przed zapisaniem. Zdjęcie rób prosto z góry, w dobrym świetle.

## Pracownicy

- **Zakończ pracę** — osoba znika z nowych grafików, ale wszystkie dotychczasowe
  wpisy zostają. Tego używaj, gdy ktoś odchodzi.
- **Usuń trwale** — kasuje pracownika razem z całą historią. Bez odwrotu.
- Strzałki **▲ ▼** ustawiają kolejność wierszy w grafiku.

## Kopie zapasowe

**Plik → Utwórz kopię zapasową** zapisuje migawkę wszystkich danych.
**Plik → Przywróć z kopii** cofa do wybranej migawki (przed przywróceniem
program i tak robi kopię bezpieczeństwa).
