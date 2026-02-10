"""Tracker configuration management."""

import shutil
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

console = Console()

CONFIG_DIR = Path.home() / ".config" / "mitmios" / "trackers"
BUILTIN_CONFIGS = Path(__file__).parent.parent / "configs"


def ensure_config_dir():
    """Create config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def manage_config(action: str, path: str | None):
    """Handle config subcommands."""
    if action == "list":
        list_configs()
    elif action == "add":
        if not path:
            console.print("[red]Usage:[/red] mitmios config add <path/to/config.yaml>")
            raise typer.Exit(1)
        add_config(Path(path))
    elif action == "validate":
        if not path:
            console.print("[red]Usage:[/red] mitmios config validate <path/to/config.yaml>")
            raise typer.Exit(1)
        validate_config(Path(path))
    elif action == "example":
        show_example()
    else:
        console.print(f"[red]Unknown action:[/red] {action}")
        console.print("Available: list, add, validate, example")
        raise typer.Exit(1)


def list_configs():
    """List all tracker configurations."""
    ensure_config_dir()

    table = Table(title="Tracker Configurations")
    table.add_column("Name", style="bold")
    table.add_column("Matchers", justify="right")
    table.add_column("Source", style="dim")
    table.add_column("Description")

    def add_config_row(f: Path, source: str):
        try:
            data = yaml.safe_load(f.read_text())
            name = data.get("name", f.stem)
            n_matchers = str(len(data.get("matchers", [])))
            desc = data.get("description", "")
            table.add_row(name, n_matchers, source, desc)
        except yaml.YAMLError:
            table.add_row(f.stem, "?", source, "[red]parse error[/red]")

    # Built-in configs
    if BUILTIN_CONFIGS.exists():
        for f in sorted(BUILTIN_CONFIGS.glob("*.yaml")):
            add_config_row(f, "built-in")

    # User configs
    for f in sorted(CONFIG_DIR.glob("*.yaml")):
        add_config_row(f, "user")

    console.print(table)
    console.print()
    console.print(f"[dim]Built-in: {BUILTIN_CONFIGS}[/dim]")
    console.print(f"[dim]User:     {CONFIG_DIR}[/dim]")


def add_config(path: Path):
    """Add a tracker config file."""
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    validate_config(path, quiet=True)

    ensure_config_dir()
    dest = CONFIG_DIR / path.name
    shutil.copy(path, dest)
    console.print(f"[green]Config added:[/green] {dest}")


REQUIRED_ROOT_FIELDS = {"name", "description", "matchers", "display"}
REQUIRED_MATCHER_FIELDS = {"id", "label", "color", "host", "path_pattern"}
VALID_EXTRACTOR_SOURCES = {
    "request.query", "request.body", "response.body",
    "request.header", "response.header",
}
VALID_COLUMN_TYPES = {"text", "code", "badge", "timestamp", "status_code"}


def validate_config(path: Path, quiet: bool = False):
    """Validate a tracker config against the TrackerConfig schema."""
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        console.print(f"[red]Invalid YAML:[/red] {e}")
        raise typer.Exit(1)

    errors = []
    if not isinstance(data, dict):
        errors.append("Root must be a mapping")
    else:
        # Root required fields
        missing = REQUIRED_ROOT_FIELDS - set(data.keys())
        if missing:
            for f in sorted(missing):
                errors.append(f"Missing required field: {f}")

        # Matchers validation
        matchers = data.get("matchers")
        if matchers is not None:
            if not isinstance(matchers, list):
                errors.append("matchers must be a list")
            else:
                for i, m in enumerate(matchers):
                    m_missing = REQUIRED_MATCHER_FIELDS - set(m.keys())
                    for f in sorted(m_missing):
                        errors.append(f"matchers[{i}]: missing '{f}'")

        # Extractors validation
        extractors = data.get("extractors")
        if extractors is not None and isinstance(extractors, list):
            for i, ex in enumerate(extractors):
                if "source" not in ex:
                    errors.append(f"extractors[{i}]: missing 'source'")
                elif ex["source"] not in VALID_EXTRACTOR_SOURCES:
                    errors.append(f"extractors[{i}]: invalid source '{ex['source']}'")
                if "field" not in ex:
                    errors.append(f"extractors[{i}]: missing 'field'")
                if "display_name" not in ex:
                    errors.append(f"extractors[{i}]: missing 'display_name'")

        # Display validation
        display = data.get("display")
        if display is not None and isinstance(display, dict):
            columns = display.get("columns")
            if columns is not None and isinstance(columns, list):
                for i, col in enumerate(columns):
                    if "field" not in col:
                        errors.append(f"display.columns[{i}]: missing 'field'")
                    if "label" not in col:
                        errors.append(f"display.columns[{i}]: missing 'label'")
                    if "type" not in col:
                        errors.append(f"display.columns[{i}]: missing 'type'")
                    elif col["type"] not in VALID_COLUMN_TYPES:
                        errors.append(f"display.columns[{i}]: invalid type '{col['type']}'")

    if errors:
        console.print(f"[red]Validation errors in {path.name}:[/red]")
        for e in errors:
            console.print(f"  - {e}")
        raise typer.Exit(1)

    if not quiet:
        name = data.get("name", "unnamed")
        n_matchers = len(data.get("matchers", []))
        n_extractors = len(data.get("extractors", []))
        console.print(f"[green]Valid:[/green] {path.name} ({name}, {n_matchers} matchers, {n_extractors} extractors)")


def show_example():
    """Print an example tracker config matching the TrackerConfig schema."""
    example = """\
[bold]# Example: Track a custom analytics endpoint[/bold]
[dim]# Save as ~/.config/mitmios/trackers/my-analytics.yaml[/dim]

name: "My App Analytics"
description: "Custom analytics event tracking"

matchers:
  - id: "event_post"
    label: "Event"
    color: "#8b5cf6"
    host: "analytics.myapp.com"
    path_pattern: "/v1/events(\\\\?|$)"
  - id: "identify"
    label: "Identify"
    color: "#3b82f6"
    host: "analytics.myapp.com"
    path_pattern: "/v1/identify"

extractors:
  - source: "request.query"
    field: "event_name"
    display_name: "Event Name"
  - source: "request.header"
    field: "x-api-key"
    display_name: "API Key"

display:
  type: "event_table"
  columns:
    - { field: "Event Name", label: "Event", type: "badge" }
    - { field: "matcher_label", label: "Type", type: "badge" }
    - { field: "timestamp", label: "Time", type: "timestamp" }
    - { field: "API Key", label: "API Key", type: "code" }
    - { field: "status_code", label: "Status", type: "status_code" }
"""
    console.print(example)
    console.print()
    console.print("[dim]Extractor sources: request.query, request.header, response.header, request.body, response.body[/dim]")
    console.print("[dim]Column types: text, code, badge, timestamp, status_code[/dim]")
