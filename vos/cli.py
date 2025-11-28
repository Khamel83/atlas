from typing import Optional

import typer

from vos.ingestion import backlog as backlog_ingestion
from vos.ingestion.gmail import poll_gmail
from vos.ingestion.rss import poll_rss
from vos.ingestion.url import enqueue_url
from vos.monitoring import queue_summary
from vos.worker.processor import run as run_worker

app = typer.Typer(name="vos")


@app.command()
def worker(
    max_iterations: Optional[int] = typer.Option(
        None, help="Limit job processing iterations for testing"
    ),
):
    """Run the vOS worker loop."""
    run_worker(max_iterations=max_iterations)


@app.command()
def poll_gmail_command():
    """Poll Gmail for Atlas labels."""
    count = poll_gmail()
    typer.echo(f"polled Gmail, {count} jobs enqueued")


@app.command()
def poll_rss_command():
    """Poll configured RSS feeds."""
    count = poll_rss()
    typer.echo(f"polled RSS, {count} jobs created")


@app.command()
def process_backlog():
    """Process backlog staging files."""
    backlog_ingestion.process_backlog()
    typer.echo("backlog processing completed")


@app.command()
def ingest_url(
    url: str,
    source: Optional[str] = typer.Option(None, help="Origin label for the job"),
):
    """Enqueue a URL for ingestion."""
    enqueue_url(url, source=source or "cli")
    typer.echo(f"queued {url}")


@app.command()
def status():
    """Show vOS queue summary."""
    summary = queue_summary()
    for stage, count in summary.items():
        typer.echo(f"{stage}: {count}")


if __name__ == "__main__":
    app()
