"""Command-line interface for Slot Telegram Scraper."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from . import __version__
from .config import TelegramConfig, config
from .exporters import get_exporter
from .filters import MemberFilter
from .scraper import TelegramScraper

# Initialize CLI app
app = typer.Typer(
    name="slot",
    help="🔌 Slot - Telegram Member Scraper & Exporter",
    add_completion=False,
)

console = Console()


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        console.print(f"[bold blue]Slot[/] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit."
    ),
):
    """🔌 Slot - Telegram Member Scraper & Exporter"""
    pass


@app.command()
def auth(
    api_id: int = typer.Option(..., prompt=True, help="Telegram API ID"),
    api_hash: str = typer.Option(..., prompt=True, help="Telegram API Hash"),
    session_name: str = typer.Option("slot_session", help="Session file name"),
):
    """
    🔐 Authenticate with Telegram.
    
    Get your API credentials from https://my.telegram.org
    """
    console.print("\n[bold blue]🔐 Telegram Authentication[/]\n")
    
    # Save credentials
    env_path = Path(".env")
    env_content = f"""# Telegram API Credentials
TELEGRAM_API_ID={api_id}
TELEGRAM_API_HASH={api_hash}
TELEGRAM_SESSION_NAME={session_name}
"""
    env_path.write_text(env_content)
    console.print(f"[green]✓[/] Credentials saved to [cyan]{env_path}[/]")
    
    # Test connection
    async def test_auth():
        temp_config = TelegramConfig(
            api_id=api_id,
            api_hash=api_hash,
            session_name=session_name,
        )
        config.telegram = temp_config
        
        scraper = TelegramScraper(config)
        scraper = TelegramScraper(config)
        console.print("[dim]Connecting to Telegram... (Enter phone number if requested)[/]")
        client = await scraper.connect()
        
        with console.status("[bold blue]Fetching profile...[/]"):
            me = await client.get_me()
        
        console.print(f"[green]✓[/] Logged in as [bold]{me.first_name}[/] (@{me.username})")
        await scraper.disconnect()
    
    try:
        asyncio.run(test_auth())
        console.print("\n[bold green]✅ Authentication successful![/]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Authentication failed:[/] {e}")
        raise typer.Exit(1)


@app.command()
def scrape(
    group: str = typer.Argument(..., help="Group @username, invite link, or ID"),
    output: Path = typer.Option(
        Path("members"), "-o", "--output",
        help="Output file path (without extension)"
    ),
    format: str = typer.Option(
        "csv", "-f", "--format",
        help="Export format: csv, json, xlsx, txt"
    ),
    limit: int | None = typer.Option(
        None, "-l", "--limit",
        help="Maximum members to scrape"
    ),
    filter_status: str | None = typer.Option(
        None, "--filter",
        help="Filter by status: online, recently, within_week, within_month"
    ),
    exclude_bots: bool = typer.Option(
        True, "--exclude-bots/--include-bots",
        help="Exclude bot accounts"
    ),
):
    """
    📥 Scrape members from a Telegram group or channel.
    
    Examples:
    
        slot scrape @mygroup
        
        slot scrape @mygroup -o members -f xlsx
        
        slot scrape @mygroup --filter=recently --limit=1000
    """
    console.print(Panel.fit(
        f"[bold blue]📥 Scraping Members[/]\n"
        f"Group: [cyan]{group}[/]\n"
        f"Output: [cyan]{output}.{format}[/]",
        border_style="blue"
    ))
    
    async def run_scrape():
        if config.telegram is None:
            console.print("[bold red]❌ Not authenticated.[/] Run [cyan]slot auth[/] first.")
            raise typer.Exit(1)
        
        async with TelegramScraper(config) as scraper:
            # Get group info first
            with console.status("[bold blue]Getting group info...[/]"):
                group_info = await scraper.get_group_info(group)
            
            console.print(f"[green]✓[/] Found: [bold]{group_info.title}[/] ({group_info.member_count:,} members)")
            
            # Scrape members with progress
            members = []
            target = limit or group_info.member_count
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Scraping members...", total=target)
                
                async for member in scraper.scrape_members(group, limit):
                    members.append(member)
                    progress.update(task, completed=len(members))
            
            console.print(f"[green]✓[/] Scraped [bold]{len(members):,}[/] members")
            
            # Apply filters
            if filter_status or exclude_bots:
                from .config import FilterConfig
                filter_config = FilterConfig(
                    exclude_bots=exclude_bots,
                    status_include=[filter_status] if filter_status else [],
                )
                member_filter = MemberFilter(filter_config)
                original_count = len(members)
                members = member_filter.filter_members(members)
                console.print(
                    f"[green]✓[/] Filtered: [bold]{len(members):,}[/] / {original_count:,} members"
                )
            
            # Export
            exporter = get_exporter(format)
            output_file = exporter.export(members, output)
            console.print(f"[green]✓[/] Exported to [cyan]{output_file}[/]")
            
            return members
    
    try:
        members = asyncio.run(run_scrape())
        
        # Show summary table
        table = Table(title="Top 10 Members Preview", show_header=True)
        table.add_column("ID", style="dim")
        table.add_column("Username")
        table.add_column("Name")
        table.add_column("Status", style="green")
        
        for member in members[:10]:
            table.add_row(
                str(member.user_id),
                f"@{member.username}" if member.username else "-",
                member.display_name,
                member.status.value,
            )
        
        console.print(table)
        console.print(f"\n[bold green]✅ Done! {len(members):,} members exported.[/]")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/] {e}")
        raise typer.Exit(1)


@app.command()
def info(
    group: str = typer.Argument(..., help="Group @username, invite link, or ID"),
):
    """
    ℹ️ Get information about a Telegram group or channel.
    """
    async def get_info():
        if config.telegram is None:
            console.print("[bold red]❌ Not authenticated.[/] Run [cyan]slot auth[/] first.")
            raise typer.Exit(1)
        
        async with TelegramScraper(config) as scraper:
            with console.status("[bold blue]Getting group info...[/]"):
                info = await scraper.get_group_info(group)
            
            table = Table(title=f"Group: {info.title}", show_header=False)
            table.add_column("Property", style="bold")
            table.add_column("Value")
            
            table.add_row("ID", str(info.group_id))
            table.add_row("Title", info.title)
            table.add_row("Username", f"@{info.username}" if info.username else "-")
            table.add_row("Members", f"{info.member_count:,}")
            table.add_row("Type", "Channel" if info.is_channel else "Group")
            table.add_row("Public", "Yes" if info.is_public else "No")
            
            console.print(table)
    
    try:
        asyncio.run(get_info())
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/] {e}")
        raise typer.Exit(1)


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
):
    """
    🌐 Start the web dashboard.
    
    Opens a browser-based interface for scraping Telegram members.
    
    Examples:
    
        slot web
        
        slot web --port 3000
    """
    console.print(Panel.fit(
        f"[bold blue]🌐 Starting Web Dashboard[/]\n"
        f"URL: [cyan]http://{host}:{port}[/]",
        border_style="blue"
    ))
    
    try:
        import uvicorn

        from .web import app as web_app
        
        console.print("[green]✓[/] Press [bold]Ctrl+C[/] to stop the server\n")
        uvicorn.run(web_app, host=host, port=port)
    except ImportError:
        console.print("[bold red]❌ uvicorn not installed.[/] Run: pip install uvicorn")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
