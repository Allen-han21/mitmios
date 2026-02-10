"""Certificate installation helpers for mitmios."""

import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()


def run_setup():
    """Guide user through certificate installation."""
    console.print("[bold green]mitmios Setup[/bold green]")
    console.print()

    cert_dir = Path.home() / ".mitmproxy"
    cert_file = cert_dir / "mitmproxy-ca-cert.pem"

    # Step 1: Check/generate certificate
    if cert_file.exists():
        console.print(f"[green]CA certificate found:[/green] {cert_file}")
    else:
        console.print("Generating mitmproxy CA certificate...")
        try:
            subprocess.run(
                ["mitmdump", "--version"],
                capture_output=True, timeout=10,
            )
            if cert_file.exists():
                console.print(f"[green]Certificate generated:[/green] {cert_file}")
            else:
                console.print("[yellow]Certificate not auto-generated. Run mitmios start once first.[/yellow]")
                return
        except FileNotFoundError:
            console.print("[red]mitmproxy not found.[/red] Install with: pip install mitmproxy")
            raise typer.Exit(1)

    console.print()

    # Step 2: Trust in macOS system keychain
    console.print("[bold]Adding CA to macOS trusted certificates...[/bold]")
    try:
        result = subprocess.run(
            [
                "security", "add-trusted-cert", "-d",
                "-r", "trustRoot",
                "-k", "/Library/Keychains/System.keychain",
                str(cert_file),
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            console.print("  [green]Added to system keychain (may require password)[/green]")
        else:
            console.print(f"  [yellow]Could not auto-add: {result.stderr.strip()}[/yellow]")
            console.print("  Run manually with sudo if needed:")
            console.print(f"  [cyan]sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain {cert_file}[/cyan]")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        console.print("  [yellow]security command not available[/yellow]")

    console.print()

    # Step 3: Install to iOS simulator keychain
    from mitmios.proxy import get_booted_simulators
    simulators = get_booted_simulators()

    if simulators:
        console.print("[bold]Installing certificate to simulators...[/bold]")
        for sim in simulators:
            udid = sim["udid"]
            name = sim["name"]
            try:
                result = subprocess.run(
                    ["xcrun", "simctl", "keychain", udid, "add-root-cert", str(cert_file)],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    console.print(f"  [green]Installed to {name}[/green]")
                else:
                    console.print(f"  [yellow]{name}: {result.stderr.strip()}[/yellow]")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                console.print(f"  [yellow]{name}: simctl keychain not available[/yellow]")
    else:
        console.print("[yellow]No booted simulators found for cert installation.[/yellow]")

    console.print()

    # Step 4: Manual instructions fallback
    console.print(Panel(
        "[bold]Manual Certificate Installation[/bold]\n\n"
        "If automatic installation didn't work:\n\n"
        "1. Open Safari in the simulator\n"
        "2. Navigate to: [cyan]http://mitm.it[/cyan]\n"
        "3. Download and install the iOS profile\n"
        "4. Settings > General > VPN & Device Management > Install mitmproxy\n"
        "5. Settings > General > About > Certificate Trust Settings > Enable mitmproxy\n",
        title="Fallback Instructions",
        border_style="yellow",
    ))

    console.print("[green]Setup complete![/green] Run [bold]mitmios start[/bold] to begin debugging.")
