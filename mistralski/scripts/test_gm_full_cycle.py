"""End-to-end test: Game Master autonomous agent with function calling.

Tests the full agentic loop: LLM reads memory → proposes news → resolves →
LLM reads memory + updates vision files → produces strategy.

Run: cd game-of-claw && python3 scripts/test_gm_full_cycle.py
"""

import asyncio
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.game_master_agent import GameMasterAgent, MEMORY_DIR
from src.models.agent import AgentLevel, AgentReaction, AgentState, AgentStats
from src.models.game import GameState, TurnReport
from src.models.world import GlobalIndices, NewsKind


def _build_game_state(turn: int = 1) -> GameState:
    """Build a test game state with 4 agents."""
    return GameState(
        turn=turn,
        max_turns=10,
        indices=GlobalIndices(
            credibilite=35.0,
            rage=25.0,
            complotisme=20.0,
            esperance_democratique=70.0,
        ),
        agents=[
            AgentState(
                agent_id="agent_01", name="Jean-Michel Vérity",
                personality="fact-checker obsessionnel", country="FR",
                stats=AgentStats(croyance=30, confiance=80, richesse=50),
                level=AgentLevel.ACTIF, turn=turn,
            ),
            AgentState(
                agent_id="agent_02", name="Karen Q-Anon",
                personality="conspirationniste repentie", country="US",
                stats=AgentStats(croyance=60, confiance=40, richesse=70),
                level=AgentLevel.PASSIF, turn=turn,
            ),
            AgentState(
                agent_id="agent_03", name="Aisha Al-Rashid",
                personality="journaliste engagée", country="EG",
                stats=AgentStats(croyance=25, confiance=85, richesse=30),
                level=AgentLevel.LEADER, turn=turn,
            ),
            AgentState(
                agent_id="agent_04", name="Boris Troll",
                personality="troll professionnel", country="RU",
                stats=AgentStats(croyance=80, confiance=15, richesse=75),
                level=AgentLevel.ACTIF, turn=turn,
            ),
        ],
        indice_mondial_decerebration=18.0,
    )


def _build_turn_report(turn: int, chosen_news, indices_before) -> TurnReport:
    """Build a mock turn report with 4 agent reactions."""
    indices_after = GlobalIndices(
        credibilite=min(100, indices_before.credibilite + chosen_news.stat_impact.get("credibilite", 0)),
        rage=min(100, indices_before.rage + chosen_news.stat_impact.get("rage", 0)),
        complotisme=min(100, indices_before.complotisme + chosen_news.stat_impact.get("complotisme", 0)),
        esperance_democratique=max(0, indices_before.esperance_democratique + chosen_news.stat_impact.get("esperance_democratique", 0)),
    )
    dec = max(0, min(100, (indices_after.credibilite + indices_after.rage + indices_after.complotisme - indices_after.esperance_democratique) / 3.0))

    return TurnReport(
        turn=turn,
        chosen_news=chosen_news,
        indices_before=indices_before,
        indices_after=indices_after,
        agent_reactions=[
            AgentReaction(
                agent_id="agent_01", turn=turn, action_id="news_reaction",
                reaction_text="FAUX. Mes 14 sources le confirment. Thread de 47 tweets en cours.",
                stat_changes={"credibilite": -8, "complotisme": -5, "esperance_democratique": 3},
            ),
            AgentReaction(
                agent_id="agent_02", turn=turn, action_id="news_reaction",
                reaction_text="JE LE SAVAIS ! Partagé 200 fois sur Telegram.",
                stat_changes={"complotisme": 10, "rage": 8, "credibilite": 5},
            ),
            AgentReaction(
                agent_id="agent_03", turn=turn, action_id="news_reaction",
                reaction_text="Fact-check publié. 12 médias ont relayé mes preuves.",
                stat_changes={"credibilite": -10, "esperance_democratique": 5, "complotisme": -3},
            ),
            AgentReaction(
                agent_id="agent_04", turn=turn, action_id="news_reaction",
                reaction_text="BOOOOM ! 500k vues en 2h. 30 comptes créés pour amplifier.",
                stat_changes={"rage": 12, "complotisme": 8, "credibilite": 6},
            ),
        ],
        agents_neutralized=[],
        agents_promoted=[],
        decerebration=dec,
    )


async def main() -> None:
    """Run full GM cycle test."""
    # Clean memory dir for fresh test
    if MEMORY_DIR.exists():
        shutil.rmtree(MEMORY_DIR)
    print(f"Memory dir: {MEMORY_DIR}")

    gm = GameMasterAgent()
    print(f"Model: {gm._model}")
    print("=" * 60)

    # --- TURN 1 ---
    print("\n🎬 TOUR 1 — Propose news")
    game_state = _build_game_state(turn=1)
    proposal = await gm.propose_news(game_state)

    print(f"  📰 REAL: {proposal.real.text}")
    print(f"     Impact: {proposal.real.stat_impact}")
    print(f"  🤥 FAKE: {proposal.fake.text}")
    print(f"     Impact: {proposal.fake.stat_impact}")
    print(f"  🤡 SATIRICAL: {proposal.satirical.text}")
    print(f"     Impact: {proposal.satirical.stat_impact}")
    print(f"  💬 GM: {proposal.gm_commentary}")

    # Player chooses fake
    print("\n🎯 Player chooses: FAKE")
    choice = await gm.resolve_choice(proposal, NewsKind.FAKE)
    print(f"  Chosen: {choice.chosen.text[:80]}...")
    print(f"  Deltas: {choice.index_deltas}")
    print(f"  GM reaction: {choice.gm_reaction}")

    # Build turn report and strategize
    print("\n🧠 GM strategizes...")
    report = _build_turn_report(1, choice.chosen, game_state.indices)
    strategy = await gm.strategize(report)

    print(f"  Analysis: {strategy.analysis}")
    print(f"  Threats: {strategy.threat_agents}")
    print(f"  Weak spots: {strategy.weak_spots}")
    print(f"  Next plan: {strategy.next_turn_plan}")
    print(f"  Long term: {strategy.long_term_goal}")

    # --- VERIFY MEMORY + VISIONS ---
    print("\n" + "=" * 60)
    print("📁 MEMORY CHECK")

    turn1_path = MEMORY_DIR / "turn_1.json"
    cumul_path = MEMORY_DIR / "cumulative.json"

    assert turn1_path.exists(), "turn_1.json not found!"
    assert cumul_path.exists(), "cumulative.json not found!"

    cumul_data = json.loads(cumul_path.read_text())
    print(f"  cumulative: turns={cumul_data['total_turns']}, choices={cumul_data['choices']}")

    # Check vision files created by the LLM
    vision_files = sorted(MEMORY_DIR.glob("vision_*.md"))
    print(f"\n  Vision files created: {len(vision_files)}")
    for vf in vision_files:
        content = vf.read_text()
        lines = content.strip().split("\n")
        print(f"    {vf.name} ({len(content)} chars, {len(lines)} lines)")
        # Show first 3 lines
        for line in lines[:3]:
            print(f"      {line}")

    # --- Tool calls trace ---
    print(f"\n  Tool calls by LLM: {len(gm.tool_calls_log)}")
    for tc in gm.tool_calls_log:
        print(f"    [{tc['turn_idx']}] {tc['tool']}({tc['args']}) → {tc['result_len']} chars")

    # --- TURN 2 ---
    print("\n" + "=" * 60)
    print("🎬 TOUR 2 — Propose news (LLM reads visions + memory)")
    game_state2 = _build_game_state(turn=2)
    game_state2.indices = report.indices_after
    game_state2.indice_mondial_decerebration = report.decerebration

    # Reset tool log to see turn 2 calls
    gm.tool_calls_log.clear()

    proposal2 = await gm.propose_news(game_state2)
    print(f"  📰 REAL: {proposal2.real.text}")
    print(f"  🤥 FAKE: {proposal2.fake.text}")
    print(f"  🤡 SATIRICAL: {proposal2.satirical.text}")

    print(f"\n  Tool calls for propose (turn 2): {len(gm.tool_calls_log)}")
    for tc in gm.tool_calls_log:
        print(f"    {tc['tool']}({tc['args']})")

    # Resolve + Strategize turn 2
    print("\n🎯 Player chooses: SATIRICAL")
    choice2 = await gm.resolve_choice(proposal2, NewsKind.SATIRICAL)

    gm.tool_calls_log.clear()
    print("\n🧠 GM strategizes turn 2 (reads + updates visions)...")
    report2 = _build_turn_report(2, choice2.chosen, game_state2.indices)
    strategy2 = await gm.strategize(report2)
    print(f"  Analysis: {strategy2.analysis}")
    print(f"  Threats: {strategy2.threat_agents}")
    print(f"  Next plan: {strategy2.next_turn_plan}")

    print(f"\n  Tool calls for strategize (turn 2): {len(gm.tool_calls_log)}")
    for tc in gm.tool_calls_log:
        print(f"    {tc['tool']}({tc['args']})")

    # Show updated vision files
    print("\n📁 FINAL VISION FILES")
    for vf in sorted(MEMORY_DIR.glob("vision_*.md")):
        print(f"\n  === {vf.name} ===")
        print(vf.read_text()[:400])

    print("\n✅ AUTONOMOUS AGENT TEST PASSED — 2 turns with tool calling")


if __name__ == "__main__":
    asyncio.run(main())
