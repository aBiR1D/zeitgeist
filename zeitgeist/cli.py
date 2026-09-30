"""Zeitgeist CLI — Beautiful terminal interface for trend predictions."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from zeitgeist.models import TrendPrediction, TrendReport

app = typer.Typer(
    name="zeitgeist",
    help="🔮 AI that predicts trending topics BEFORE they trend.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║  ███████╗███████╗██╗████████╗ ██████╗ ███████╗██╗███████╗████████╗  ║
║  ╚══███╔╝██╔════╝██║╚══██╔══╝██╔════╝ ██╔════╝██║██╔════╝╚══██╔══╝  ║
║    ███╔╝ █████╗  ██║   ██║   ██║  ███╗█████╗  ██║███████╗   ██║     ║
║   ███╔╝  ██╔══╝  ██║   ██║   ██║   ██║██╔══╝  ██║╚════██║   ██║     ║
║  ███████╗███████╗██║   ██║   ╚██████╔╝███████╗██║███████║   ██║     ║
║  ╚══════╝╚══════╝╚═╝   ╚═╝    ╚═════╝ ╚══════╝╚═╝╚══════╝   ╚═╝     ║
║                                                                      ║
║  Google Trends tells you NOW.  Zeitgeist tells you TOMORROW.         ║
╚══════════════════════════════════════════════════════════════╝
"""


def _get_sources(use_mock: bool = False):
    """Build the list of signal collectors."""
    from zeitgeist.sources import GitHubCollector, HackerNewsCollector, MockCollector, RedditCollector

    if use_mock:
        return [MockCollector()]
    return [HackerNewsCollector(), RedditCollector(), GitHubCollector()]


def _confidence_bar(confidence: float, width: int = 20) -> Text:
    """Render a color-coded confidence bar."""
    filled = int(confidence * width)
    empty = width - filled

    if confidence >= 0.8:
        color = "bold green"
    elif confidence >= 0.6:
        color = "bold yellow"
    elif confidence >= 0.4:
        color = "yellow"
    else:
        color = "red"

    bar = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * empty, style="dim")
    bar.append(f" {confidence:.0%}", style=color)
    return bar


def _render_prediction(pred: TrendPrediction, index: int) -> Panel:
    """Render a single prediction as a Rich Panel."""
    if pred.confidence >= 0.8:
        border = "bold green"
        icon = "🔥"
    elif pred.confidence >= 0.6:
        border = "bold yellow"
        icon = "📈"
    elif pred.confidence >= 0.4:
        border = "yellow"
        icon = "👀"
    else:
        border = "dim"
        icon = "🌱"

    content = Text()
    content.append("Confidence: ", style="bold")
    content.append_text(_confidence_bar(pred.confidence))
    content.append("\n")

    content.append("Category:   ", style="bold")
    content.append(pred.category.value.replace("_", "/"), style="cyan")
    content.append("\n")

    content.append("Velocity:   ", style="bold")
    content.append(f"{pred.velocity:.1f}", style="magenta")
    content.append(f"  ({pred.current_signals_count} signals)")
    content.append("\n")

    if pred.predicted_peak_date:
        delta = pred.predicted_peak_date - datetime.now(timezone.utc)
        hours = max(0, int(delta.total_seconds() / 3600))
        content.append("Peak in:    ", style="bold")
        content.append(f"~{hours}h", style="bold cyan")
        content.append("\n")

    content.append("\n")
    content.append(pred.explanation or "No explanation available.", style="italic")

    if pred.recommended_actions:
        content.append("\n\n")
        content.append("Actions:\n", style="bold")
        for action in pred.recommended_actions:
            content.append(f"  → {action}\n", style="green")

    return Panel(
        content,
        title=f"{icon} #{index} {pred.topic}",
        border_style=border,
        expand=True,
    )


def _render_report(report: TrendReport) -> None:
    """Render a full trend report to the console."""
    console.print(BANNER, style="bold cyan")

    console.print(
        f"[dim]Report generated: {report.generated_at:%Y-%m-%d %H:%M UTC} "
        f"| Horizon: {report.time_horizon_hours}h "
        f"| Predictions: {len(report.predictions)}[/dim]\n"
    )

    if report.meta_trends:
        meta = Table(title="🌐 Meta-Trends", show_header=False, border_style="dim")
        meta.add_column("Trend", style="italic cyan")
        for mt in report.meta_trends:
            meta.add_row(mt)
        console.print(meta)
        console.print()

    if not report.predictions:
        console.print("[yellow]No predictions available. Try running a scan first.[/yellow]")
        return

    for i, pred in enumerate(report.predictions, 1):
        console.print(_render_prediction(pred, i))
        console.print()


@app.command()
def scan(
    mock: bool = typer.Option(False, "--mock", "-m", help="Use mock data instead of live APIs"),
    horizon: int = typer.Option(48, "--horizon", "-H", help="Prediction horizon in hours"),
) -> None:
    """🔍 Scan all sources and generate trend predictions NOW."""
    from zeitgeist.analyzer import run_full_scan
    from zeitgeist.store import ZeitgeistStore

    sources = _get_sources(use_mock=mock)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Scanning sources and analyzing trends...", total=None)
        report = asyncio.run(run_full_scan(sources))

    report.time_horizon_hours = horizon

    async def _persist():
        store = ZeitgeistStore()
        await store.initialize()
        await store.store_report(report)

    asyncio.run(_persist())

    _render_report(report)


@app.command()
def predict(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of predictions to show"),
) -> None:
    """📊 Show current trend predictions from the latest scan."""
    from zeitgeist.store import ZeitgeistStore

    async def _load():
        store = ZeitgeistStore()
        await store.initialize()
        return await store.get_recent_predictions(limit=limit)

    predictions = asyncio.run(_load())

    if not predictions:
        console.print(BANNER, style="bold cyan")
        console.print("[yellow]No predictions yet. Run 'zeitgeist scan' first.[/yellow]")
        raise typer.Exit()

    report = TrendReport(predictions=predictions)
    _render_report(report)


@app.command()
def sources() -> None:
    """📡 List configured signal sources."""
    console.print(BANNER, style="bold cyan")

    table = Table(title="Signal Sources", border_style="cyan")
    table.add_column("Source", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Description")

    source_info = [
        ("HackerNews", "hackernews", "✅ Active", "Top & new stories via Firebase API"),
        ("Reddit", "reddit", "✅ Active", "Rising posts from tech subreddits"),
        ("GitHub", "github", "✅ Active", "Trending repositories via search API"),
        ("ArXiv", "arxiv", "🔜 Coming", "Recent ML/CS paper submissions"),
        ("Patents", "patents", "🔜 Coming", "New patent filings in tech"),
        ("Jobs", "jobs", "🔜 Coming", "Emerging skills in job postings"),
        ("Mock", "mock", "🧪 Testing", "Realistic sample data for testing"),
    ]

    for name, stype, status, desc in source_info:
        table.add_row(name, stype, status, desc)

    console.print(table)


@app.command()
def history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records to show"),
) -> None:
    """📜 Show past predictions and their accuracy."""
    from zeitgeist.store import ZeitgeistStore

    console.print(BANNER, style="bold cyan")

    async def _load():
        store = ZeitgeistStore()
        await store.initialize()
        preds = await store.get_recent_predictions(limit=limit)
        acc = await store.get_prediction_accuracy()
        return preds, acc

    predictions, accuracy_records = asyncio.run(_load())

    if not predictions and not accuracy_records:
        console.print("[yellow]No history yet. Run 'zeitgeist scan' to generate predictions.[/yellow]")
        raise typer.Exit()

    if predictions:
        table = Table(title="Recent Predictions", border_style="cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Topic", style="bold", max_width=50)
        table.add_column("Confidence", justify="center")
        table.add_column("Category", style="cyan")
        table.add_column("Velocity", justify="right", style="magenta")

        for i, pred in enumerate(predictions, 1):
            conf_text = _confidence_bar(pred.confidence, width=10)
            table.add_row(
                str(i),
                pred.topic[:50],
                conf_text,
                pred.category.value,
                f"{pred.velocity:.1f}",
            )
        console.print(table)

    if accuracy_records:
        console.print()
        acc_table = Table(title="Accuracy Tracking", border_style="green")
        acc_table.add_column("Topic", style="bold")
        acc_table.add_column("Predicted", style="dim")
        acc_table.add_column("Actual Peak", style="cyan")
        acc_table.add_column("Accuracy", justify="center")

        for rec in accuracy_records:
            score_str = f"{rec.accuracy_score:.0%}" if rec.accuracy_score is not None else "—"
            acc_table.add_row(
                rec.topic[:40],
                rec.predicted_at.strftime("%Y-%m-%d %H:%M"),
                rec.actual_peak.strftime("%Y-%m-%d %H:%M") if rec.actual_peak else "—",
                score_str,
            )
        console.print(acc_table)


def main() -> None:
    """Entry point for `python -m zeitgeist`."""
    app()


if __name__ == "__main__":
    main()
