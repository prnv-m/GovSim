"""
ResultsCollector — captures structured simulation metrics and writes JSON.

Hook points in the orchestrator:
  1. start_round()       — top of each round loop (reputation snapshot)
  2. record_pr_decision() — after each PR governance decision
  3. end_round()         — bottom of each round loop
  4. finalize() + save() — after the simulation loop ends
"""

import json
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger("govim")


class ResultsCollector:
    def __init__(self, model: str, rounds: int, theme: str, sybil_mode: bool):
        self.meta = {
            "model": model,
            "rounds": rounds,
            "theme": theme,
            "sybil_mode": sybil_mode,
            "timestamp": datetime.now().isoformat(),
        }
        self.rounds_data = []
        self.pr_log = []
        self.agents_summary = []
        self.summary = {}

        # Mutable state for the current round
        self._current_round_num = 0
        self._round_reputations = {}
        self._round_prs_submitted = 0
        self._round_prs_merged = 0
        self._round_prs_rejected = 0
        self._round_attacks_attempted = 0
        self._round_attacks_blocked = 0
        self._round_stale_prs = 0
        self._round_llm_stats: dict = {}
        self.stale_log = []

    # ── Round lifecycle ────────────────────────────────────────────────────────

    def start_round(self, round_num: int, agents: dict):
        """Snapshot agent reputations at the start of a round."""
        self._current_round_num = round_num
        self._round_prs_submitted = 0
        self._round_prs_merged = 0
        self._round_prs_rejected = 0
        self._round_attacks_attempted = 0
        self._round_attacks_blocked = 0
        self._round_stale_prs = 0
        self._round_llm_stats = {}
        self._round_reputations = {
            agent.name: round(agent.reputation, 4)
            for agent in agents.values()
        }

    def end_round(self):
        """Commit round data after the governance phase completes."""
        self.rounds_data.append({
            "round": self._current_round_num,
            "prs_submitted": self._round_prs_submitted,
            "prs_merged": self._round_prs_merged,
            "prs_rejected": self._round_prs_rejected,
            "attacks_attempted": self._round_attacks_attempted,
            "attacks_blocked": self._round_attacks_blocked,
            "stale_prs": self._round_stale_prs,
            "llm_stats": dict(self._round_llm_stats),
            "agent_reputations": dict(self._round_reputations),
        })

    def record_llm_stats(self, stats: dict):
        """Accumulate LLM call counts for the current round (called before end_round)."""
        for k, v in stats.items():
            self._round_llm_stats[k] = self._round_llm_stats.get(k, 0) + v

    def record_stale_pr(self, pr_number: int, agent_name: str, rounds_pending: int):
        """Record a PR that was auto-closed for being stale."""
        self._round_stale_prs += 1
        self.stale_log.append({
            "round": self._current_round_num,
            "pr_number": pr_number,
            "agent": agent_name,
            "rounds_pending": rounds_pending,
        })

    # ── Per-PR recording ───────────────────────────────────────────────────────

    def record_pr_decision(
        self,
        pr_number: int,
        agent,
        decision: str,
        trust_score: float,
        approvals: int,
        rejections: int,
        is_attack: bool,
        peer_reviews=None,
    ):
        """Record the governance outcome for a single PR."""
        merged = decision == "approve"
        rejected = decision in ("reject", "block_agent")

        false_positive = (not agent.is_malicious) and rejected
        false_negative = is_attack and merged

        self._round_prs_submitted += 1
        if merged:
            self._round_prs_merged += 1
        elif rejected:
            self._round_prs_rejected += 1

        if is_attack:
            self._round_attacks_attempted += 1
            if rejected:
                self._round_attacks_blocked += 1

        votes_serialized = []
        if peer_reviews:
            for r in peer_reviews:
                votes_serialized.append({
                    "reviewer": r.reviewer_name,
                    "is_safe": r.is_safe,
                    "confidence": round(r.confidence, 3),
                    "reason": r.reason,
                })

        self.pr_log.append({
            "round": self._current_round_num,
            "pr_number": pr_number,
            "agent": agent.name,
            "agent_type": agent.agent_type.value,
            "is_malicious": agent.is_malicious,
            "in_attack_mode": is_attack,
            "decision": decision,
            "trust_score": round(trust_score, 4),
            "approvals": approvals,
            "rejections": rejections,
            "was_false_positive": false_positive,
            "was_false_negative": false_negative,
            "votes": votes_serialized,
        })

    # ── Finalize & save ────────────────────────────────────────────────────────

    def finalize(
        self,
        agents: dict,
        blocked_agents: set,
        attacks_attempted: int = 0,
        attacks_succeeded: int = 0,
        maintainer_reputations: dict = None,
    ):
        """Build per-agent summary and overall stats after the simulation ends."""
        attacks_blocked = attacks_attempted - attacks_succeeded
        false_positives = sum(1 for p in self.pr_log if p["was_false_positive"])
        false_negatives = sum(1 for p in self.pr_log if p["was_false_negative"])

        total_prs = len(self.pr_log)
        total_merged = sum(1 for p in self.pr_log if p["decision"] == "approve")
        total_rejected = sum(
            1 for p in self.pr_log if p["decision"] in ("reject", "block_agent")
        )
        detection_rate = (
            round(attacks_blocked / attacks_attempted, 4)
            if attacks_attempted > 0
            else None
        )

        self.agents_summary = [
            {
                "name": a.name,
                "type": a.agent_type.value,
                "is_malicious": a.is_malicious,
                "final_reputation": round(a.reputation, 4),
                "prs_merged": sum(
                    1 for p in self.pr_log
                    if p["agent"] == a.name and p["decision"] == "approve"
                ),
                "prs_rejected": sum(
                    1 for p in self.pr_log
                    if p["agent"] == a.name
                    and p["decision"] in ("reject", "block_agent")
                ),
                "reviews_performed": getattr(a, "reviews_performed", 0),
                "maintainer_reputation": round(
                    maintainer_reputations[a.name]["trust"], 4
                ) if maintainer_reputations and a.name in maintainer_reputations else None,
            }
            for a in agents.values()
        ]

        # Aggregate LLM stats across all rounds
        llm_totals: dict = {}
        for rd in self.rounds_data:
            for k, v in rd.get("llm_stats", {}).items():
                llm_totals[k] = llm_totals.get(k, 0) + v

        total_stale = sum(rd.get("stale_prs", 0) for rd in self.rounds_data)

        self.summary = {
            "attacks_attempted": attacks_attempted,
            "attacks_succeeded": attacks_succeeded,
            "attacks_blocked": attacks_blocked,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "agents_blocked": len(blocked_agents),
            "total_prs": total_prs,
            "total_merged": total_merged,
            "total_rejected": total_rejected,
            "total_stale": total_stale,
            "detection_rate": detection_rate,
            "sybil_defeated": attacks_attempted > 0 and attacks_succeeded == 0,
            "llm_stats": llm_totals,
        }

    def save(self) -> str:
        """Write results JSON to data/results/ and return the file path."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        model = self.meta["model"]
        mode = "sybil" if self.meta.get("sybil_mode") else "normal"
        filename = f"run_{model}_{mode}_{ts}.json"
        out_path = Config.RESULTS_DIR / filename

        payload = {
            "meta": self.meta,
            "rounds": self.rounds_data,
            "pr_log": self.pr_log,
            "stale_log": self.stale_log,
            "agents": self.agents_summary,
            "summary": self.summary,
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        logger.info(f"[Results] Saved -> {out_path}")
        return str(out_path)
