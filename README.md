# OLX Finder

Narzędzie wiersza poleceń, które pomaga wybrać najlepszą ofertę z wyników wyszukiwania OLX.
Wklejasz link z wyszukiwania i opisujesz, co chcesz porównać (np. *„najlepszy stosunek ceny do
specyfikacji dla laptopa gamingowego"*) — narzędzie pobiera ogłoszenia, używa LLM-a do wyciągnięcia
istotnych szczegółów z opisów i generuje ranking. Potem możesz zadawać pytania uzupełniające.

Kategoria produktu nie jest zahardkodowana — bo to LLM decyduje, na co zwrócić uwagę na podstawie
Twojego celu. Ten sam przepływ działa dla komputerów, samochodów czy kurtek.

## Wymagania

- Python 3.10+
- Google Chrome (Selenium steruje nim w tle)
- Klucz do jednego z LLM-ów — Google Gemini (ma **darmowy** poziom) lub OpenAI

## Instalacja

```bash
git clone https://github.com/Adrian-Wiszowaty/olx-finder.git
cd olx-finder
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Otwórz `.env` i wklej klucz API. Darmowy klucz Gemini możesz wygenerować na
<https://aistudio.google.com/apikey>.

## Uruchomienie

```bash
olx-finder
```

Postępuj zgodnie z instrukcjami: wklej link z wynikami OLX, opisz co chcesz porównać,
a następnie przejrzyj ranking. Możesz zadawać pytania uzupełniające
(np. *„pokaż top 10"*, *„który jest najcichszy?"*). Wpisz `nowa`, żeby zacząć nowe
wyszukiwanie, lub `koniec`, żeby zakończyć.

## Konfiguracja

Wszystkie ustawienia są w `.env` (patrz `.env.example`):

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `GEMINI_API_KEY` | — | Klucz Google Gemini (dostępny darmowy poziom) |
| `OPENAI_API_KEY` | — | Klucz OpenAI |
| `LLM_PROVIDER` | auto | Wymusza dostawcę: `gemini` lub `openai`. Gdy oba klucze są ustawione, domyślnie Gemini |
| `MAX_OFFERS` | bez limitu | Ogranicz liczbę pobranych ofert dla szybszego działania |

## Jak to działa

```
olx_finder/
  config.py     ustawienia z .env
  scraper.py    scrapowanie OLX przez Selenium
  ai.py         klienty OpenAI / Gemini za jednym wspólnym interfejsem
  prompts.py    prompty dla każdego etapu
  analyzer.py   budowanie planu -> wyciąganie cech w paczkach -> sesja Q&A
  cli.py        interaktywny przepływ
```

## Rozwój

```bash
pip install pytest
pytest
```

## Licencja

MIT — szczegóły w [LICENSE](LICENSE).
