import argparse
import logging

from dotenv import find_dotenv, load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from olx_finder import __version__
from olx_finder.ai import get_client
from olx_finder.analyzer import OfferAnalyzer
from olx_finder.config import Settings
from olx_finder.models import OfferFinderError
from olx_finder.scraper import get_scraper

EXIT_WORDS = {"koniec", "exit", "quit", "q"}
NEW_WORDS = {"nowa", "nowe", "new"}

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
        if args.max_offers:
            settings.max_offers = args.max_offers
        console.print(Panel(WELCOME, title="OLX Finder", border_style="cyan"))
        llm = get_client(settings)
    except OfferFinderError as error:
        console.print(Panel(str(error), title="Konfiguracja", border_style="red"))
        return 1

    console.print(f"[dim]Silnik AI: {llm.name} ({llm.model})  •  oferty: {settings.max_offers}[/dim]\n")
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
        console.print(f"[green]Zebrano {len(offers)} ofert.[/green]")

        offers = _extract(analyzer, offers, plan)
        with console.status("[cyan]Układam ranking...[/cyan]"):
            session = analyzer.start_session(goal, plan, offers)
            verdict = session.ranking()
        console.print(Panel(Markdown(verdict), title="Werdykt AI", border_style="green"))
    except OfferFinderError as error:
        console.print(f"[red]{error}[/red]\n")
        return True

    return _follow_up(session)


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
            console.print(f"[red]{error}[/red]")
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
    with get_scraper(url, settings) as scraper, _progress() as progress:
        pages = progress.add_task("Przeglądam wyniki...", total=None)
        details = progress.add_task("Pobieram opisy ofert...", total=None)
        return scraper.fetch_offers(
            url,
            max_offers=settings.max_offers,
            max_pages=settings.max_pages,
            on_page=lambda p, n: progress.update(pages, description=f"Strona {p} — {n} ofert"),
            on_offer=lambda done, total: progress.update(details, total=total, completed=done),
        )


def _extract(analyzer, offers, plan):
    with _progress() as progress:
        task = progress.add_task("Analizuję opisy (AI)...", total=None)
        return analyzer.extract_specs(
            offers, plan,
            on_progress=lambda done, total: progress.update(task, total=total, completed=done),
        )
