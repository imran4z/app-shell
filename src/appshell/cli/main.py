"""App Shell CLI - the canonical business-logic surface (BLUEPRINT.md §0.3).

The API orchestrates by spawning the same CLI a human would type. No logic
exists only behind an HTTP route. Registered as [project.scripts] appshell.
"""

from __future__ import annotations

import os

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from appshell.observability import configure_logging

console = Console()


@click.group()
def cli() -> None:
    """App Shell - clone-and-build app template."""
    load_dotenv(override=True)
    configure_logging(os.environ.get("APPSHELL_LOG_LEVEL", "WARNING"))


# === db ==================================================================


@cli.group()
def db() -> None:
    """Database lifecycle commands."""


@db.command("init")
def db_init() -> None:
    """Apply all pending migrations."""
    from appshell.storage import apply_migrations

    applied = apply_migrations()
    if applied:
        console.print(f"[green]applied:[/green] {', '.join(applied)}")
    else:
        console.print("[dim]nothing to apply - schema is current[/dim]")


@db.command("reset")
@click.option("--yes", is_flag=True, help="Skip the confirmation prompt.")
def db_reset(yes: bool) -> None:
    """DEV ONLY: drop every app table, then re-apply migrations."""
    if not yes:
        click.confirm("Drop ALL app tables and re-migrate?", abort=True)
    from appshell.storage import apply_migrations, drop_all

    drop_all()
    applied = apply_migrations()
    console.print(f"[green]reset complete[/green] - applied {len(applied)} migration(s)")


@db.command("status")
def db_status() -> None:
    """Show connection target and applied migrations."""
    from sqlalchemy import text

    from appshell.storage import build_dsn, connect

    dsn = build_dsn()
    safe = dsn.split("@")[-1] if "@" in dsn else dsn
    console.print(f"target: [bold]{safe}[/bold]")
    try:
        with connect().connect() as conn:
            rows = conn.execute(
                text("SELECT filename, applied_at FROM _migrations ORDER BY filename")
            ).all()
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]unreachable:[/red] {exc}")
        raise SystemExit(1) from exc
    table = Table("migration", "applied_at")
    for r in rows:
        table.add_row(r[0], str(r[1]))
    console.print(table)


# === items (example domain commands - replace per-app) ===================


@cli.group()
def items() -> None:
    """Example-entity commands."""


@items.command("seed")
@click.option("--count", default=12, show_default=True)
def items_seed(count: int) -> None:
    """Insert demo items so the UI has something to show."""
    import random

    from appshell.schemas import Item, ItemState
    from appshell.storage import ItemRepository, session_scope

    titles = [
        "Feed the office capybara",
        "Untangle the llama drama",
        "Polish the disco ball",
        "Recalibrate the snack radar",
        "Teach the roomba to moonwalk",
        "Audit the rubber duck inventory",
        "Water the plastic plants (again)",
        "Rename all the things",
        "Debug the coffee machine",
        "Alphabetize the sticker drawer",
        "Test the emergency confetti cannon",
        "Interview the office goldfish",
        "Refactor the paper airplane fleet",
        "Ship the good-vibes pipeline",
        "Count the invisible sheep",
        "Upgrade the moral support hamster",
    ]
    random.shuffle(titles)
    repo = ItemRepository()
    states = list(ItemState)
    with session_scope() as session:
        for i in range(count):
            title = titles[i] if i < len(titles) else f"Mystery task {i + 1:02d}"
            repo.upsert(
                session,
                Item(
                    title=title,
                    state=random.choice(states),
                    detail={"seed": True, "index": i},
                ),
            )
    console.print(f"[green]seeded {count} items[/green]")


@items.command("list")
@click.option("--limit", default=20, show_default=True)
def items_list(limit: int) -> None:
    from appshell.storage import ItemRepository, session_scope

    with session_scope() as session:
        entries, total = ItemRepository().list(session, limit=max(1, min(limit, 500)))
    table = Table("id", "title", "state", "updated_at")
    for it in entries:
        table.add_row(it.id, it.title, it.state.value, str(it.updated_at or "-"))
    console.print(table)
    console.print(f"[dim]{len(entries)} of {total}[/dim]")


# === profiles (example container entity - replace per-app) ===============


@cli.group()
def profiles() -> None:
    """Example container-entity commands."""


@profiles.command("seed")
@click.option("--count", default=6, show_default=True)
def profiles_seed(count: int) -> None:
    """Insert demo profiles so the UI has something to show."""
    import random

    from appshell.schemas import Profile, ProfileStatus
    from appshell.storage import ProfileRepository, session_scope

    companies = [
        ("Capybara Cafe Co", "hospitality", "Serves suspiciously calm espresso."),
        ("Otter Logistics", "logistics", "Ships anything, holds hands during transit."),
        ("Quokka Games", "gaming", "Every loading screen smiles back."),
        ("Narwhal Media", "media", "The unicorn of the sea, now streaming."),
        ("Axolotl Health", "health", "Regenerates your patience, not just limbs."),
        ("Pangolin Fintech", "fintech", "Rolls into a ball when the market dips."),
        ("Wombat Warehousing", "logistics", "Cube-shaped storage, naturally."),
        ("Puffin Analytics", "media", "Small bird, big dashboards."),
        ("Gecko Grid Energy", "energy", "Sticks to the wall so your power does not."),
        ("Manatee Marine Tours", "hospitality", "Slow travel, taken literally."),
    ]
    random.shuffle(companies)
    repo = ProfileRepository()
    with session_scope() as session:
        for i in range(count):
            name, vertical, blurb = companies[i % len(companies)]
            if i >= len(companies):
                name = f"{name} {i + 1}"
            repo.upsert(
                session,
                Profile(
                    name=name,
                    summary=blurb,
                    status=random.choice(list(ProfileStatus)),
                    tags=[vertical, "demo"],
                    attributes={
                        "vertical": vertical,
                        "region": random.choice(["amer", "emea", "apac"]),
                    },
                ),
            )
    console.print(f"[green]seeded {count} profiles[/green]")


# === users (the app's account directory) =================================


@cli.group()
def users() -> None:
    """User-directory commands."""


@users.command("seed")
@click.option("--count", default=8, show_default=True)
def users_seed(count: int) -> None:
    """Insert demo users so the directory has something to show."""
    import random

    from appshell.schemas import AppUser, UserRole, UserStatus
    from appshell.storage import UserRepository, session_scope

    first = [
        "Waffles",
        "Biscuit",
        "Noodle",
        "Pickle",
        "Mochi",
        "Taco",
        "Ziggy",
        "Pretzel",
        "Churro",
        "Nugget",
    ]
    last = [
        "McOtter",
        "Wombatson",
        "Capybara",
        "Quokka",
        "Platypus",
        "Axolotl",
        "Pangolin",
        "Mongoose",
        "Narwhal",
        "Pufferfish",
    ]
    repo = UserRepository()
    with session_scope() as session:
        for i in range(count):
            name = f"{random.choice(first)} {random.choice(last)}"
            handle = name.lower().replace(" ", ".").replace("..", ".")
            repo.upsert(
                session,
                AppUser(
                    name=name,
                    email=f"{handle}{i}@example.com",
                    role=random.choice(list(UserRole)),
                    status=random.choice(list(UserStatus)),
                ),
            )
    console.print(f"[green]seeded {count} users[/green]")


# === serve ===============================================================


@cli.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8765, show_default=True)
@click.option("--reload", is_flag=True)
def serve(host: str, port: int, reload: bool) -> None:
    """Run the API (serves the built UI too, when ui/dist exists)."""
    import uvicorn

    uvicorn.run("appshell.api.main:app", host=host, port=port, reload=reload)


# === doctor ==============================================================


@cli.command("doctor")
def doctor() -> None:
    """Config preflight: name exactly what's missing."""
    from sqlalchemy import text

    from appshell.storage import connect

    ok = True
    if os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[green]✓[/green] ANTHROPIC_API_KEY set")
    else:
        console.print("[yellow]○[/yellow] ANTHROPIC_API_KEY missing - LLM features disabled")
    try:
        with connect().connect() as conn:
            conn.execute(text("SELECT 1"))
        console.print("[green]✓[/green] postgres reachable")
    except Exception as exc:  # noqa: BLE001
        ok = False
        console.print(f"[red]✗[/red] postgres unreachable - run `just up` ({str(exc)[:120]})")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    cli()
