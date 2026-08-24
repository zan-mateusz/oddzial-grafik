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

Kliknij komórkę i pisz. Program rozumie:

| Wpis | Znaczenie |
|---|---|
| `D` | dyżur dzienny 7:00–19:00 |
| `N` | dyżur nocny 19:00–7:00 |
| `U` | urlop wypoczynkowy |
| `L4` | zwolnienie lekarskie |
| `8-14` | dyżur od 8:00 do 14:00 (6 godzin) |
| `7:30-19:30` | dyżur z dokładnością do minut |
| `7,5` | sama liczba godzin, bez podawania pory |

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

## Podsumowanie po prawej stronie

| Kolumna | Znaczenie |
|---|---|
| **Godziny** | ile godzin faktycznie wypracowano |
| **Wymiar** | ile godzin przypada do przepracowania (etat, urlopy, święta) |
| **Bilans** | nadgodziny na pomarańczowo, niedogodziny na czerwono |
| **Dyż.** | liczba dyżurów |
| **Noc** | godziny w porze nocnej (21:00–7:00) |
| **Urlop**, **L4** | liczba dni |

Wymiar zmniejsza się automatycznie za każde święto wypadające poza niedzielą
oraz za dni urlopu i zwolnienia.

## Zapisywanie i wydruk

Dane zapisują się **automatycznie** — nie ma przycisku „Zapisz”.

**Plik → Eksportuj do Excela** tworzy arkusz gotowy do wydruku (poziomo, A4,
z legendą). Otworzy się w Excelu i w LibreOffice/OpenOffice.

## Wczytanie istniejącego grafiku

**Plik → Importuj z pliku Excel** — program sam znajduje wiersz z numerami dni
i kolumnę z nazwiskami. Jeśli trafi źle, popraw numery w polach *Położenie
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
