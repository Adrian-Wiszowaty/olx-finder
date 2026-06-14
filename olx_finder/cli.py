import argparse
import logging

from dotenv import find_dotenv, load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from olx_finder import __version__
from olx_finder.ai import RateLimitError, get_client
from olx_finder.analyzer import OfferAnalyzer
from olx_finder.config import Settings
from olx_finder.models import OfferFinderError
from olx_finder.scraper import get_scraper

EXIT_WORDS = {"koniec", "exit", "quit", "q"}
NEW_WORDS = {"nowa", "nowe", "new"}
LARGE_RESULT_SET = 60

console = Console()

WELCOME = """\
Cześć! Pomogę Ci wybrać najlepsze oferty z OLX.

Jak to działa:
  1. Wklejasz link z wynikami wyszukiwania na OLX.
  2. Mówisz, co chcesz porównać — np. „najlepszy stosunek ceny do podzespołów”.
  3. Pobieram oferty, a AI wyciąga z opisów to, co ważne, i układa ranking.
  4. Potem możesz dopytywać o szczegóły jak w rozmowie.

W każdej chwili wpisz „koniec”, aby zakończyć."""


def main(argv=None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    load_dotenv(find_dotenv(usecwd=True))

    try:
        settings = Settings.from_env()
        if args.provider:
            settings.provider = args.provider
        if args.max_offers:
            settings.max_offers = args.max_offers
        console.print(Panel(WELCOME, title="OLX Finder", border_style="cyan"))
        llm = get_client(settings)
    except OfferFinderError as error:
        console.print(Panel(str(error), title="Konfiguracja", border_style="red"))
        return 1

    limit = settings.max_offers if settings.max_offers is not None else "bez limitu"
    console.print(f"[dim]Silnik AI: {llm.name} ({llm.model})  •  oferty: {limit}[/dim]\n")
    analyzer = OfferAnalyzer(llm)
    try:
        while _one_search(analyzer, settings):
            pass
    except (KeyboardInterrupt, EOFError):
        pass
    console.print("\n[dim]Do zobaczenia![/dim]")
    return 0


def _parse_args(argv):
    parser = argparse.ArgumentParser(prog="olx-finder", description="AI-powered analysis of OLX offers.")
    parser.add_argument("--provider", choices=["gemini", "openai"], help="force an LLM provider")
    parser.add_argument("--max-offers", type=int, help="how many offers to analyze")
    parser.add_argument("--verbose", action="store_true", help="more logging")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def _one_search(analyzer, settings) -> bool:
    url = _ask_url()
    if url is None:
        return False
    goal = _ask("\n[bold cyan]Co chcesz porównać w tych ofertach?[/bold cyan] "
                "[dim](np. „komputer do gier — najlepszy stosunek ceny do podzespołów”)[/dim]")
    if goal is None:
        return False

    try:
        with console.status("[cyan]Przygotowuję plan analizy...[/cyan]"):
            plan = analyzer.build_plan(goal, url)
        if plan.attributes:
            console.print("\n[bold]W każdej ofercie sprawdzę:[/bold] " + ", ".join(plan.attributes))

        offers = _scrape(url, settings)
        if not offers:
            console.print("[yellow]Nie znalazłem ofert pod tym linkiem.[/yellow]\n")
            return True
        note = ""
        if settings.max_offers is not None and len(offers) >= settings.max_offers:
            note = (f" [dim](osiągnięto limit {settings.max_offers} — "
                    "usuń MAX_OFFERS z .env, aby pobrać wszystkie)[/dim]")
        console.print(f"[green]Zebrano {len(offers)} ofert.[/green]{note}")

        offers = _extract(analyzer, offers, plan)
        with console.status("[cyan]Układam ranking...[/cyan]"):
            session = analyzer.start_session(goal, plan, offers)
            verdict = session.ranking()
        console.print(Panel(Markdown(verdict), title="Werdykt AI", border_style="green"))
    except OfferFinderError as error:
        console.print(f"[red]{_error_text(error)}[/red]\n")
        return True

    return _follow_up(session)


def _error_text(error):
    if isinstance(error, RateLimitError):
        return ("Przekroczono limit zapytań do API (możliwe wyczerpanie dziennego "
                "darmowego limitu Gemini). Spróbuj później albo zmniejsz MAX_OFFERS.")
    return str(error)


def _follow_up(session) -> bool:
    console.print(
        "\n[dim]Możesz teraz dopytywać — np. „pokaż TOP 10 zamiast 5”, "
        "„która najlepsza do streamingu?”.\nWpisz „nowa” dla nowego wyszukiwania "
        "albo „koniec”, aby wyjść.[/dim]\n"
    )
    while True:
        question = _ask("[bold cyan]Twoje pytanie[/bold cyan]")
        if question is None:
            return False
        if question.lower() in NEW_WORDS:
            console.print()
            return True
        try:
            with console.status("[cyan]Myślę...[/cyan]"):
                answer = session.ask(question)
        except OfferFinderError as error:
            console.print(f"[red]{_error_text(error)}[/red]")
            continue
        console.print(Panel(Markdown(answer), border_style="blue"))


def _ask(prompt) -> str | None:
    while True:
        text = Prompt.ask(prompt).strip()
        if text.lower() in EXIT_WORDS:
            return None
        if text:
            return text


def _ask_url() -> str | None:
    while True:
        url = _ask("[bold cyan]Wklej link z wynikami wyszukiwania na OLX[/bold cyan]")
        if url is None:
            return None
        if not url.startswith(("http://", "https://")):
            console.print("[yellow]To nie wygląda na link — wklej pełny adres https://[/yellow]")
        elif "olx.pl" not in url:
            console.print("[yellow]Na razie obsługiwany jest tylko serwis OLX (olx.pl).[/yellow]")
        else:
            return url


def _progress():
    return Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), MofNCompleteColumn(), console=console,
    )


def _scrape(url, settings):
    scraper = get_scraper(url, settings)
    try:
        with _progress() as progress:
            task = progress.add_task("Przeglądam wyniki...", total=None)
            listings = scraper.collect_listings(
                url,
                max_offers=settings.max_offers,
                max_pages=settings.max_pages,
                on_page=lambda p, n, total: progress.update(
                task, description=f"Strona {p} — {n} ofert", completed=p, total=total
            ),
            )
            progress.update(task, total=progress.tasks[task].completed)
        if not listings:
            return []
        listings = _maybe_limit(listings, settings)
        with _progress() as progress:
            task = progress.add_task("Pobieram opisy ofert...", total=len(listings))
            return scraper.add_descriptions(
                listings,
                on_offer=lambda done, total: progress.update(task, completed=done, total=total),
            )
    finally:
        scraper.close()


def _maybe_limit(listings, settings):
    if settings.max_offers is not None or len(listings) <= LARGE_RESULT_SET:
        return listings
    console.print(
        f"\n[yellow]Znalazłem {len(listings)} ofert.[/yellow] Pobranie opisów i analiza "
        "wszystkich potrwa kilkanaście–kilkadziesiąt minut i zużyje dużo zapytań do API."
    )
    answer = Prompt.ask("Ile przeanalizować? (Enter = wszystkie)", default=str(len(listings))).strip()
    if answer.isdigit() and int(answer) > 0:
        return listings[: int(answer)]
    return listings


def _extract(analyzer, offers, plan):
    with _progress() as progress:
        task = progress.add_task("Analizuję opisy (AI)...", total=len(offers))
        return analyzer.extract_specs(
            offers, plan,
            on_progress=lambda done, total: progress.update(task, total=total, completed=done),
        )
