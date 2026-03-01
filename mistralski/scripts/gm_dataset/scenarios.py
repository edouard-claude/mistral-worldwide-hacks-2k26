"""Deterministic scenario generation for GM dataset.

Generates 240 scenarios (200 train + 40 val) with coverage matrix:
- 15 countries, 20 actions, 10 agents, 3 game phases
- 4 GM types x 60 each (50 train + 10 val)
- Deterministic via random seed 42

Per type (50 train):
- Early (turns 1-3): 15 examples
- Mid (turns 4-6): 20 examples
- Late (turns 7-10): 15 examples
"""

import json
import random

from scripts.gm_dataset.constants import (
    ACTION_CATEGORIES,
    ACTION_COSTS,
    ACTION_EFFECTS,
    ACTION_IDS,
    ACTION_LABELS,
    AGENT_DATA,
    COUNTRY_CODES,
    COUNTRY_NAMES,
    EARLY_TURNS,
    GM_TYPES,
    LATE_TURNS,
    MID_TURNS,
)
from scripts.gm_dataset.seed_headlines import REAL_NEWS_HEADLINES


def _random_indices(rng: random.Random, turn: int) -> dict[str, float]:
    """Generate plausible global indices for a given turn."""
    # Indices drift with game progress
    progress = turn / 10.0
    return {
        "credibilite": round(rng.uniform(30, 30 + 50 * progress), 1),
        "rage": round(rng.uniform(10, 10 + 60 * progress), 1),
        "complotisme": round(rng.uniform(15, 15 + 55 * progress), 1),
        "esperance_democratique": round(
            rng.uniform(max(10, 85 - 70 * progress), 85 - 30 * progress), 1,
        ),
    }


def _random_decerebration(indices: dict[str, float]) -> float:
    """Derive decerebration from indices."""
    return round(
        (indices["credibilite"] + indices["rage"] + indices["complotisme"]
         - indices["esperance_democratique"]) / 3.0,
        1,
    )


def _pick_real_news(rng: random.Random, n: int = 2) -> list[str]:
    """Pick n random real news headlines."""
    return [h.text for h in rng.sample(REAL_NEWS_HEADLINES, min(n, len(REAL_NEWS_HEADLINES)))]


def _pick_agents_summary(rng: random.Random, n: int = 3) -> list[dict[str, str]]:
    """Pick n random agents as summary."""
    agents = rng.sample(AGENT_DATA, min(n, len(AGENT_DATA)))
    return [
        {"id": a["id"], "name": a["name"], "country": a["country"], "level": a["level"]}
        for a in agents
    ]


def _pick_action(rng: random.Random) -> dict[str, str | int | dict[str, float]]:
    """Pick a random action with full details."""
    action_id = rng.choice(ACTION_IDS)
    return {
        "id": action_id,
        "label": ACTION_LABELS[action_id],
        "category": ACTION_CATEGORIES[action_id],
        "target": rng.choice(COUNTRY_CODES + ["MONDIAL"]),
        "cost": ACTION_COSTS[action_id],
        "base_effects": ACTION_EFFECTS[action_id],
    }


def _pick_countries(rng: random.Random, n: int, bias: str = "random") -> list[str]:
    """Pick n countries, with optional bias towards chaos/stable."""
    return rng.sample(COUNTRY_CODES, min(n, len(COUNTRY_CODES)))


def _generate_temperature_scenario(
    rng: random.Random,
    scenario_id: int,
) -> dict:
    """Generate a gm_temperature scenario."""
    turn = 0  # Temperature is at game start
    indices = _random_indices(rng, turn=1)
    return {
        "type": "gm_temperature",
        "scenario_id": scenario_id,
        "game_state": {
            "turn": 0,
            "indices": indices,
            "decerebration": _random_decerebration(indices),
            "date_context": rng.choice([
                "Lundi matin, les marchés ouvrent dans la panique",
                "Mercredi après-midi, le calme avant la tempête",
                "Vendredi soir, personne ne lit les communiqués du vendredi soir",
                "Mardi, jour de grève préventive",
                "Jeudi, lendemain d'une nuit de tweets présidentiels",
                "Samedi, les journalistes sont en RTT",
                "Dimanche, même la propagande se repose",
            ]),
        },
        "real_news_sample": _pick_real_news(rng),
    }


def _generate_headlines_scenario(
    rng: random.Random,
    scenario_id: int,
    turn: int,
) -> dict:
    """Generate a gm_headlines scenario."""
    indices = _random_indices(rng, turn)
    recent_countries = _pick_countries(rng, rng.randint(1, 4))
    last_actions = [_pick_action(rng) for _ in range(rng.randint(1, 3))]
    return {
        "type": "gm_headlines",
        "scenario_id": scenario_id,
        "game_state": {
            "turn": turn,
            "indices": indices,
            "decerebration": _random_decerebration(indices),
            "countries_targeted_recently": recent_countries,
            "last_actions": last_actions,
            "active_agents_summary": _pick_agents_summary(rng),
            "temperature_du_jour": rng.choice([
                "Paranoïa ambiante",
                "Calme trompeur",
                "Hystérie médiatique",
                "Apathie généralisée",
                "Indignation sélective",
                "Euphorie artificielle",
                "Suspicion chronique",
            ]),
        },
        "real_news_sample": _pick_real_news(rng),
    }


def _generate_reaction_scenario(
    rng: random.Random,
    scenario_id: int,
    turn: int,
) -> dict:
    """Generate a gm_reaction scenario."""
    indices = _random_indices(rng, turn)
    action = _pick_action(rng)
    affected = _pick_agents_summary(rng, rng.randint(1, 4))
    return {
        "type": "gm_reaction",
        "scenario_id": scenario_id,
        "game_state": {
            "turn": turn,
            "indices": indices,
            "decerebration": _random_decerebration(indices),
            "action": action,
            "affected_agents": affected,
            "temperature_du_jour": rng.choice([
                "Panique contrôlée",
                "Frénésie informationnelle",
                "Déni collectif",
                "Rage sourde",
                "Résignation joyeuse",
                "Complotisme ambiant",
                "Sidération générale",
            ]),
        },
        "real_news_sample": _pick_real_news(rng),
    }


def _generate_narrative_scenario(
    rng: random.Random,
    scenario_id: int,
    turn: int,
) -> dict:
    """Generate a gm_narrative scenario."""
    indices = _random_indices(rng, turn)
    n_chaos = rng.randint(1, min(5, turn + 1))
    n_stable = rng.randint(1, 4)
    countries_chaos = _pick_countries(rng, n_chaos)
    remaining = [c for c in COUNTRY_CODES if c not in countries_chaos]
    countries_stable = rng.sample(remaining, min(n_stable, len(remaining)))

    neutralized = rng.sample(AGENT_DATA, rng.randint(0, min(2, turn)))
    leaders = rng.sample(
        [a for a in AGENT_DATA if a not in neutralized],
        rng.randint(1, 3),
    )

    actions_history = [_pick_action(rng) for _ in range(rng.randint(3, 8))]

    return {
        "type": "gm_narrative",
        "scenario_id": scenario_id,
        "game_state": {
            "turn": turn,
            "indices": indices,
            "decerebration": _random_decerebration(indices),
            "countries_in_chaos": countries_chaos,
            "countries_stable": countries_stable,
            "neutralized_agents": [
                {"id": a["id"], "name": a["name"]} for a in neutralized
            ],
            "leader_agents": [
                {"id": a["id"], "name": a["name"], "country": a["country"]}
                for a in leaders
            ],
            "actions_history": actions_history,
        },
        "real_news_sample": _pick_real_news(rng, 3),
    }


def _distribute_turns(
    rng: random.Random,
    n_total: int,
    early: int = 15,
    mid: int = 20,
    late: int = 15,
) -> list[int]:
    """Distribute n_total scenarios across game phases.

    Args:
        rng: Random generator.
        n_total: Total scenarios to generate.
        early: Count for early phase.
        mid: Count for mid phase.
        late: Count for late phase.

    Returns:
        List of turn numbers.
    """
    assert early + mid + late == n_total
    turns: list[int] = []
    turns.extend(rng.choices(list(EARLY_TURNS), k=early))
    turns.extend(rng.choices(list(MID_TURNS), k=mid))
    turns.extend(rng.choices(list(LATE_TURNS), k=late))
    rng.shuffle(turns)
    return turns


def generate_all_scenarios(
    seed: int = 42,
) -> tuple[list[dict], list[dict]]:
    """Generate all 240 scenarios split into train/val.

    Args:
        seed: Random seed for reproducibility.

    Returns:
        (train_scenarios, val_scenarios) — 200 train + 40 val.
    """
    rng = random.Random(seed)
    train: list[dict] = []
    val: list[dict] = []
    scenario_id = 0

    generators = {
        "gm_temperature": _generate_temperature_scenario,
        "gm_headlines": _generate_headlines_scenario,
        "gm_reaction": _generate_reaction_scenario,
        "gm_narrative": _generate_narrative_scenario,
    }

    for gm_type in GM_TYPES:
        gen_fn = generators[gm_type]

        # Train: 50 examples
        if gm_type == "gm_temperature":
            # Temperature doesn't use turns, just generate 50
            for _ in range(50):
                scenario_id += 1
                train.append(gen_fn(rng, scenario_id))
        else:
            turns = _distribute_turns(rng, 50)
            for turn in turns:
                scenario_id += 1
                train.append(gen_fn(rng, scenario_id, turn))

        # Val: 10 examples
        if gm_type == "gm_temperature":
            for _ in range(10):
                scenario_id += 1
                val.append(gen_fn(rng, scenario_id))
        else:
            val_turns = _distribute_turns(rng, 10, early=3, mid=4, late=3)
            for turn in val_turns:
                scenario_id += 1
                val.append(gen_fn(rng, scenario_id, turn))

    return train, val


def scenario_to_user_message(scenario: dict) -> str:
    """Convert a scenario dict to a JSON string for the user message.

    Args:
        scenario: Scenario dict from generate_all_scenarios.

    Returns:
        JSON string of the game_state input.
    """
    payload = {
        "type": scenario["type"],
        "game_state": scenario["game_state"],
        "real_news_sample": scenario["real_news_sample"],
    }
    return json.dumps(payload, ensure_ascii=False)
