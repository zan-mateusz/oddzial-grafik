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

## Gdzie są zapisywane dane

Wszystkie grafiki trzymane są w pliku:

```
C:\Users\<nazwa użytkownika>\AppData\Roaming\Grafik\grafik.db
```

Program zapisuje dane automatycznie. Warto od czasu do czasu użyć
**Plik → Utwórz kopię zapasową**, a przed zmianą komputera skopiować cały
katalog `Grafik` z powyższej ścieżki.

## Odinstalowanie

Panel sterowania → Aplikacje → **Grafik dyżurów** → Odinstaluj.
Grafiki i kopie zapasowe pozostaną na dysku.
