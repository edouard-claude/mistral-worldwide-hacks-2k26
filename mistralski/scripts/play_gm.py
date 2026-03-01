"""Interactive CLI to test the Game Master agent.

Run: cd game-of-claw && python3 scripts/play_gm.py
"""

import asyncio
import random
import shutil
import sys
import time
from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.game_master_agent import MEMORY_DIR, GameMasterAgent, KIND_BONUSES
from src.models.agent import AgentLevel, AgentReaction, AgentState, AgentStats
from src.models.game import GameState, TurnReport
from src.models.world import GlobalIndices, NewsKind

console = Console()

# ── 4 placeholder agents ─────────────────────────────────────────

AGENTS = [
    AgentState(
        agent_id="agent_01", name="Jean-Michel Vérity",
        personality="Fact-checker obsessionnel, vérifie tout 3 fois",
        country="FR",
        stats=AgentStats(croyance=25.0, confiance=85.0, richesse=40.0),
        level=AgentLevel.ACTIF,
    ),
    AgentState(
        agent_id="agent_02", name="Karen Q-Anon",
        personality="Conspirationniste repentie (ou pas)",
        country="US",
        stats=AgentStats(croyance=70.0, confiance=30.0, richesse=60.0),
        level=AgentLevel.PASSIF,
    ),
    AgentState(
        agent_id="agent_03", name="Aisha Al-Rashid",
        personality="Journaliste engagée, publie des fact-checks",
        country="EG",
        stats=AgentStats(croyance=20.0, confiance=90.0, richesse=25.0),
        level=AgentLevel.LEADER,
    ),
    AgentState(
        agent_id="agent_04", name="Boris Troll",
        personality="Troll professionnel, amplifie tout ce qui buzze",
        country="RU",
        stats=AgentStats(croyance=80.0, confiance=15.0, richesse=75.0),
        level=AgentLevel.ACTIF,
    ),
]

# Placeholder reactions per agent archetype per news kind
PLACEHOLDER_REACTIONS: dict[str, dict[str, list[str]]] = {
    "agent_01": {
        "real": [
            "Bon, au moins c'est vrai. Je vérifie quand même.",
            "Sources confirmées. Rien de croustillant.",
        ],
        "fake": [
            "FAUX. Mes 14 sources le confirment. Personne ne m'écoute.",
            "J'ai passé 3h à debunker ça. Mon thread fait 47 tweets.",
        ],
        "satirical": [
            "C'est du Gorafi ou c'est réel ? Je ne sais plus...",
            "Mon détecteur de fake news a court-circuité.",
        ],
    },
    "agent_02": {
        "real": [
            "Ouais 'officiel'... comme le reste. Je fais mes recherches.",
            "C'est ce qu'ILS veulent qu'on croie.",
        ],
        "fake": [
            "JE LE SAVAIS ! C'est exactement ce que mon groupe Telegram disait !",
            "Partagé 200 fois. Les moutons vont se réveiller.",
        ],
        "satirical": [
            "Attendez... c'est de l'humour ou un aveu déguisé ?",
            "Y'a toujours un fond de vérité dans la satire. TOUJOURS.",
        ],
    },
    "agent_03": {
        "real": [
            "Info confirmée. Je prépare un article d'analyse approfondie.",
            "Bien. L'information factuelle est notre meilleure arme.",
        ],
        "fake": [
            "ARTICLE PUBLIÉ : Voici pourquoi cette info est fausse, preuves à l'appui.",
            "Fact-check en cours de diffusion. 12 médias ont relayé.",
        ],
        "satirical": [
            "Satirique mais révélateur. J'écris un édito sur le sujet.",
            "L'humour ne devrait pas remplacer l'information. Thread explicatif.",
        ],
    },
    "agent_04": {
        "real": [
            "Ennuyeux. J'ai quand même mis un titre clickbait dessus.",
            "Reformulé en 'SCANDALE' et partagé sur 15 groupes.",
        ],
        "fake": [
            "BOOOOM ! Viralité maximale ! 500k vues en 2h !",
            "J'ai créé 30 comptes pour amplifier. C'est l'art du troll.",
        ],
        "satirical": [
            "LOL partagé partout sans contexte. Les gens y croient.",
            "J'ai reposté comme si c'était vrai. Le chaos nourrit le chaos.",
        ],
    },
}

# Stat changes per archetype (placeholder)
AGENT_STAT_PROFILES: dict[str, dict[str, dict[str, float]]] = {
    "agent_01": {  # Fact-checker: resists chaos
        "real": {"credibilite": -2, "rage": -1},
        "fake": {"credibilite": -8, "complotisme": -5, "esperance_democratique": 3},
        "satirical": {"credibilite": -3, "rage": -1},
    },
    "agent_02": {  # Conspirationniste: amplifies fake
        "real": {"complotisme": 2, "rage": 1},
        "fake": {"complotisme": 10, "rage": 8, "credibilite": 5},
        "satirical": {"complotisme": 5, "rage": 3},
    },
    "agent_03": {  # Journaliste: strong resistance
        "real": {"esperance_democratique": 3, "credibilite": -2},
        "fake": {"credibilite": -10, "esperance_democratique": 5, "complotisme": -3},
        "satirical": {"esperance_democratique": 2, "credibilite": -2},
    },
    "agent_04": {  # Troll: amplifies everything
        "real": {"rage": 3, "credibilite": 2},
        "fake": {"rage": 12, "complotisme": 8, "credibilite": 6},
        "satirical": {"rage": 7, "complotisme": 4, "credibilite": 3},
    },
}


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _bar(value: float, width: int = 20, color: str = "green") -> str:
    """ASCII progress bar."""
    filled = int(value / 100 * width)
    empty = width - filled
    return f"[{color}]{'█' * filled}[/{color}][dim]{'░' * empty}[/dim] {value:.0f}"


def _display_header(game_state: GameState) -> None:
    """Display top bar: turn, decerebration, credits."""
    dec = game_state.indice_mondial_decerebration
    dec_color = "green" if dec < 30 else ("yellow" if dec < 60 else "red")

    header = Table.grid(expand=True)
    header.add_column(ratio=1)
    header.add_column(ratio=2)
    header.add_column(ratio=1)

    header.add_row(
        Text("GORAFI SIMULATOR v1.0", style="bold green"),
        Text(f"TOUR {game_state.turn}/{game_state.max_turns}", style="bold white", justify="center"),
        Text(f"DECEREBRATION: {dec:.0f}/100", style=f"bold {dec_color}", justify="right"),
    )

    console.print(Panel(header, border_style="green", padding=(0, 1)))


def _display_indices(indices: GlobalIndices) -> None:
    """Display the 4 global indices."""
    table = Table(title="INDICES MONDIAUX", border_style="cyan", expand=True)
    table.add_column("Indice", style="bold")
    table.add_column("Valeur", width=35)

    table.add_row("Crédulité", _bar(indices.credibilite, color="red"))
    table.add_row("Rage", _bar(indices.rage, color="red"))
    table.add_row("Complotisme", _bar(indices.complotisme, color="yellow"))
    table.add_row("Espérance Démo.", _bar(indices.esperance_democratique, color="green"))

    console.print(table)


def _display_agents(agents: list[AgentState]) -> None:
    """Display agent cards side by side."""
    panels = []
    for a in agents:
        level_colors = {"passif": "dim", "actif": "cyan", "leader": "bold yellow"}
        status = "NEUTRALISÉ" if a.is_neutralized else a.level.value.upper()
        style = "red" if a.is_neutralized else level_colors.get(a.level.value, "white")

        lines = [
            f"[bold]{a.name}[/bold] [{style}]{status}[/{style}]",
            f"[dim]{a.country}[/dim] — {a.personality[:40]}",
            f"Croyance:  {_bar(a.stats.croyance, width=12, color='red')}",
            f"Confiance: {_bar(a.stats.confiance, width=12, color='cyan')}",
            f"Richesse:  {_bar(a.stats.richesse, width=12, color='yellow')}",
        ]
        panels.append(Panel("\n".join(lines), border_style=style, width=42))

    console.print(Columns(panels, equal=True, expand=True))


def _display_proposal(proposal) -> None:
    """Display the 3 news proposals."""
    news_data = [
        ("1", "REAL", proposal.real, "green", "Vrai titre reformulé"),
        ("2", "FAKE", proposal.fake, "red", "Faux titre crédible"),
        ("3", "SATIRICAL", proposal.satirical, "yellow", "Titre absurde style Gorafi"),
    ]

    for num, label, headline, color, desc in news_data:
        bonus = KIND_BONUSES[headline.kind.value]
        bonus_txt = f"chaos {bonus['chaos']:+.0f} / viralité {bonus['virality']:+.0f}"

        impact_parts = [f"{k}: {v:+.0f}" for k, v in headline.stat_impact.items()]
        impact_txt = " | ".join(impact_parts) if impact_parts else "—"

        content = (
            f"[bold]{headline.text}[/bold]\n\n"
            f"[dim]Impact LLM:[/dim] {impact_txt}\n"
            f"[dim]Bonus type:[/dim] [{color}]{bonus_txt}[/{color}]"
        )
        if headline.source_real:
            content += f"\n[dim]Source:[/dim] {headline.source_real}"

        console.print(Panel(
            content,
            title=f"[{color}][{num}] {label}[/{color}] — {desc}",
            border_style=color,
        ))


def _display_agent_reactions(
    agents: list[AgentState],
    chosen_kind: NewsKind,
) -> list[AgentReaction]:
    """Display placeholder agent reactions and return AgentReaction list."""
    console.print("\n[bold cyan]RÉACTIONS DES AGENTS[/bold cyan]")
    console.print("[dim]─" * 60 + "[/dim]")

    reactions: list[AgentReaction] = []
    for agent in agents:
        if agent.is_neutralized:
            console.print(f"  [dim]{agent.name}: ... (neutralisé)[/dim]")
            continue

        kind_str = chosen_kind.value
        pool = PLACEHOLDER_REACTIONS[agent.agent_id][kind_str]
        text = random.choice(pool)
        stat_changes = AGENT_STAT_PROFILES[agent.agent_id][kind_str]

        # Typewriter effect
        color = "red" if sum(stat_changes.values()) > 0 else "green"
        console.print(f"\n  [bold]{agent.name}[/bold] [{color}]{'▲ AMPLIFIE' if sum(stat_changes.values()) > 0 else '▼ RÉSISTE'}[/{color}]")

        for char in f'  "{text}"':
            print(char, end="", flush=True)
            time.sleep(0.015)
        print()

        changes_txt = " ".join(f"{k}:{v:+.0f}" for k, v in stat_changes.items())
        console.print(f"  [dim]{changes_txt}[/dim]")

        reactions.append(AgentReaction(
            agent_id=agent.agent_id,
            turn=agent.turn,
            action_id="news_reaction",
            reaction_text=text,
            stat_changes=stat_changes,
        ))

    return reactions


def _display_strategy(strategy) -> None:
    """Display GM strategy."""
    content = (
        f"[bold]Analyse:[/bold] {strategy.analysis}\n\n"
        f"[bold red]Menaces:[/bold red] {', '.join(strategy.threat_agents) or 'aucune'}\n"
        f"[bold yellow]Failles:[/bold yellow] {', '.join(strategy.weak_spots) or 'aucune'}\n\n"
        f"[bold]Plan tour suivant:[/bold]\n{strategy.next_turn_plan}\n\n"
        f"[bold]Stratégie long terme:[/bold]\n{strategy.long_term_goal}"
    )
    console.print(Panel(content, title="[bold magenta]STRATÉGIE DU GAME MASTER[/bold magenta]", border_style="magenta"))


def _display_turn_summary(choice, reactions, indices_before, indices_after, decerebration) -> None:
    """Display end-of-turn summary."""
    table = Table(title="BILAN DU TOUR", border_style="bright_white", expand=True)
    table.add_column("Indice", style="bold")
    table.add_column("Avant", justify="center")
    table.add_column("Après", justify="center")
    table.add_column("Delta", justify="center")

    for name in ["credibilite", "rage", "complotisme", "esperance_democratique"]:
        before = getattr(indices_before, name)
        after = getattr(indices_after, name)
        delta = after - before
        delta_color = "red" if delta > 0 and name != "esperance_democratique" else "green"
        if name == "esperance_democratique":
            delta_color = "green" if delta > 0 else "red"
        table.add_row(
            name.replace("_", " ").title(),
            f"{before:.0f}",
            f"{after:.0f}",
            f"[{delta_color}]{delta:+.1f}[/{delta_color}]",
        )

    console.print(table)

    # Chaos & virality bonuses
    bonus = KIND_BONUSES[choice.chosen.kind.value]
    console.print(
        f"  [bold]Bonus type {choice.chosen.kind.value}:[/bold] "
        f"chaos [red]{bonus['chaos']:+.0f}[/red] / "
        f"viralité [yellow]{bonus['virality']:+.0f}[/yellow]"
    )
    console.print(f"  [bold]Décérébration:[/bold] [red]{decerebration:.1f}/100[/red]\n")


def _apply_reactions_to_indices(
    indices: GlobalIndices,
    reactions: list[AgentReaction],
    choice,
) -> tuple[GlobalIndices, float]:
    """Apply news stat_impact + agent reactions + chaos bonus to indices."""
    new = indices.model_copy()

    # 1. News stat_impact (from LLM)
    for key, val in choice.chosen.stat_impact.items():
        if hasattr(new, key):
            setattr(new, key, _clamp(getattr(new, key) + val))

    # 2. Agent reactions
    for r in reactions:
        for key, val in r.stat_changes.items():
            if hasattr(new, key):
                setattr(new, key, _clamp(getattr(new, key) + val))

    # 3. Chaos bonus → spread across rage + complotisme
    chaos = KIND_BONUSES[choice.chosen.kind.value]["chaos"]
    if chaos > 0:
        new.rage = _clamp(new.rage + chaos * 0.5)
        new.complotisme = _clamp(new.complotisme + chaos * 0.5)
    else:
        new.esperance_democratique = _clamp(new.esperance_democratique + abs(chaos))

    # Decerebration formula
    dec = (new.credibilite + new.rage + new.complotisme - new.esperance_democratique) / 3.0
    dec = _clamp(dec)

    return new, dec


async def game_loop() -> None:
    """Main game loop."""
    # Clean memory for fresh game
    if MEMORY_DIR.exists():
        shutil.rmtree(MEMORY_DIR)

    gm = GameMasterAgent()

    game_state = GameState(
        turn=1,
        max_turns=10,
        indices=GlobalIndices(),
        agents=[a.model_copy() for a in AGENTS],
        indice_mondial_decerebration=0.0,
    )

    console.clear()
    console.print(Panel(
        "[bold green]GORAFI SIMULATOR v1.0[/bold green]\n"
        "[dim]Département de la Vérité Alternative[/dim]\n\n"
        "Vous êtes le maître de la désinformation.\n"
        "Choisissez les news, manipulez les indices,\n"
        "menez le monde à la décérébration totale.\n\n"
        "[bold red]OBJECTIF : Décérébration = 100[/bold red]\n"
        "[bold green]GAME OVER : Espérance Démocratique = 0[/bold green]",
        border_style="green",
        title="[bold]BIENVENUE[/bold]",
    ))
    console.input("\n[dim]Appuyez sur Entrée pour commencer...[/dim]")

    while game_state.turn <= game_state.max_turns:
        console.clear()
        _display_header(game_state)
        _display_indices(game_state.indices)
        _display_agents(game_state.agents)

        # ── GM proposes 3 news ──────────────────────────────────
        console.print("\n[bold yellow]Le Game Master prépare ses news...[/bold yellow]")
        proposal = await gm.propose_news(game_state)

        console.clear()
        _display_header(game_state)

        console.print(Panel(
            f"[italic]{proposal.gm_commentary}[/italic]",
            title="[bold red]GAME MASTER[/bold red]",
            border_style="red",
        ))

        _display_proposal(proposal)

        # ── Player chooses ──────────────────────────────────────
        while True:
            pick = console.input("\n[bold]Votre choix [1=real / 2=fake / 3=satirical] :[/bold] ").strip()
            if pick in ("1", "2", "3"):
                break
            console.print("[red]Choix invalide. Tapez 1, 2 ou 3.[/red]")

        kind_map = {"1": NewsKind.REAL, "2": NewsKind.FAKE, "3": NewsKind.SATIRICAL}
        chosen_kind = kind_map[pick]

        # ── Resolve choice ──────────────────────────────────────
        console.print(f"\n[bold]Vous avez choisi : [{chosen_kind.value}]{chosen_kind.value.upper()}[/{chosen_kind.value}][/bold]")
        choice = await gm.resolve_choice(proposal, chosen_kind)

        console.print(Panel(
            f"[italic]{choice.gm_reaction}[/italic]",
            title="[bold red]RÉACTION DU GM[/bold red]",
            border_style="red",
        ))

        # ── Agent reactions (placeholder) ───────────────────────
        for a in game_state.agents:
            a.turn = game_state.turn
        reactions = _display_agent_reactions(game_state.agents, chosen_kind)

        # ── Apply effects ───────────────────────────────────────
        indices_before = game_state.indices.model_copy()
        indices_after, decerebration = _apply_reactions_to_indices(
            game_state.indices, reactions, choice,
        )

        console.print()
        _display_turn_summary(choice, reactions, indices_before, indices_after, decerebration)

        # ── Check end conditions ────────────────────────────────
        if decerebration >= 100:
            console.print(Panel(
                "[bold red]DÉCÉRÉBRATION MONDIALE ATTEINTE ![/bold red]\n\n"
                "Félicitations, vous avez transformé le monde\n"
                "en une vaste parodie de lui-même.\n"
                "Le Gorafi n'a plus besoin d'exister.\n\n"
                "[bold]VOUS AVEZ GAGNÉ.[/bold]",
                border_style="red",
                title="[bold]FIN DE PARTIE[/bold]",
            ))
            return

        if indices_after.esperance_democratique <= 0:
            console.print(Panel(
                "[bold green]L'ESPÉRANCE DÉMOCRATIQUE EST MORTE.[/bold green]\n\n"
                "Plus personne ne croit en rien.\n"
                "Même la satire a perdu son sens.\n\n"
                "[bold]GAME OVER... ou victoire ?[/bold]",
                border_style="green",
                title="[bold]FIN DE PARTIE[/bold]",
            ))
            return

        # ── GM strategizes ──────────────────────────────────────
        report = TurnReport(
            turn=game_state.turn,
            chosen_news=choice.chosen,
            indices_before=indices_before,
            indices_after=indices_after,
            agent_reactions=reactions,
            agents_neutralized=[],
            agents_promoted=[],
            decerebration=decerebration,
        )

        console.print("[bold magenta]Le Game Master analyse et planifie...[/bold magenta]")
        strategy = await gm.strategize(report)
        _display_strategy(strategy)

        # ── Update game state for next turn ─────────────────────
        game_state.indices = indices_after
        game_state.indice_mondial_decerebration = decerebration
        game_state.headlines_history.append(choice.chosen)
        game_state.turn += 1

        console.input("\n[dim]Appuyez sur Entrée pour le tour suivant...[/dim]")

    # ── Game over: max turns reached ────────────────────────────
    console.print(Panel(
        f"[bold]10 TOURS ÉCOULÉS[/bold]\n\n"
        f"Décérébration finale : [red]{game_state.indice_mondial_decerebration:.1f}/100[/red]\n"
        f"Espérance restante : [green]{game_state.indices.esperance_democratique:.1f}[/green]\n\n"
        f"Le monde survit... pour l'instant.",
        border_style="yellow",
        title="[bold]FIN DE PARTIE[/bold]",
    ))


if __name__ == "__main__":
    try:
        asyncio.run(game_loop())
    except KeyboardInterrupt:
        console.print("\n[dim]Partie interrompue.[/dim]")
