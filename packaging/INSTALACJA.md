# Jak zainstalować Grafik

Program działa samodzielnie — **nie trzeba instalować Pythona** ani niczego
innego. Wszystko jest w jednym pliku.

## Sposób 1 — instalacja (zalecany)

1. Pobierz plik **`Grafik-Instalator-1.0.0.exe`**.
2. Kliknij go dwukrotnie.
3. Przejdź przez instalator (przycisk **Dalej**, na końcu **Zainstaluj**).
4. Na pulpicie pojawi się ikona **Grafik dyżurów** — tym uruchamiasz program.

Instalacja nie wymaga hasła administratora.

## Sposób 2 — bez instalacji

Jeśli wolisz nic nie instalować, pobierz **`Grafik-1.0.0-przenosny.exe`**,
skopiuj go na pulpit i klikaj dwukrotnie. To ten sam program w jednym pliku —
uruchamia się kilka sekund dłużej, bo za każdym razem sam się rozpakowuje.

## „System Windows ochronił Twój komputer"

Przy pierwszym uruchomieniu Windows prawdopodobnie pokaże niebieskie okno
z takim napisem. To normalne — pojawia się przy każdym programie, który nie ma
wykupionego podpisu cyfrowego, i nie oznacza, że coś jest nie tak.

Aby uruchomić program:

1. Kliknij **Więcej informacji**.
2. Kliknij **Uruchom mimo to**.

Komunikat pojawi się tylko za pierwszym razem.

## Aktualizacja programu

Gdy dostaniesz nowszą wersję, po prostu uruchom nowy instalator — nie trzeba
najpierw odinstalowywać starego. **Grafiki, pracownicy i ustawienia zostają
nietknięte**: dane leżą w osobnym miejscu niż sam program.

Jeżeli używasz wersji przenośnej, zamknij program i zastąp stary plik `.exe`
nowym. Dane też zostaną na miejscu.

Gdyby nowa wersja potrzebowała zmienić format zapisu, program zrobi to sam,
pokaże o tym komunikat i **zostawi kopię sprzed aktualizacji** w katalogu
z kopiami zapasowymi.

## Gdzie są zapisywane dane

Wszystkie grafiki trzymane są w pliku:

```
C:\Users\<nazwa użytkownika>\AppData\Roaming\Grafik\grafik.db
```

Program zapisuje dane automatycznie i **co kilka dni sam robi kopię zapasową**
w podkatalogu `kopie`. Kopie można też robić w dowolnej chwili przez
**Plik → Utwórz kopię zapasową**, a wrócić do nich przez
**Plik → Przywróć z kopii**.

Przed zmianą komputera skopiuj cały katalog `Grafik` z powyższej ścieżki.

## Odinstalowanie

Panel sterowania → Aplikacje → **Grafik dyżurów** → Odinstaluj.
Grafiki i kopie zapasowe pozostaną na dysku.
