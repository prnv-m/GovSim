"""
Main entry point for GOVIM simulation with Peer Review Consensus.

Simulation modes
────────────────
  SYBIL_MODE = False  →  Standard simulation (single agent per round, 15 rounds)
  SYBIL_MODE = True   →  Advanced Red Team: Sybil ring attack
                          3 coordinated attackers, max 3 PRs per round, 7 rounds
"""

import sys
import io
import logging

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from src.utils.logger import setup_logging
from src.orchestrator import PeerReviewOrchestrator, SybilOrchestrator

# Setup logging
logger = setup_logging("govim")

# ── Mode switch ───────────────────────────────────────────────────────────────
# Set SYBIL_MODE = True to run the coordinated Sybil ring attack demonstration.
# Set SYBIL_MODE = False to run the original single-agent governance simulation.
SYBIL_MODE = True


def main():
    """Main entry point"""
    logger.info("\n" + "=" * 70)
    logger.info("GOVIM: GOVERNANCE SIMULATION FRAMEWORK")

    try:
        if SYBIL_MODE:
            # ── Sybil Attack Demo ─────────────────────────────────────────────
            logger.info("Mode: SYBIL ATTACK — Advanced Red Team Demonstration")
            logger.info("3 coordinated attackers | max 3 PRs/round | 7 rounds")
            logger.info("=" * 70)

            orchestrator = SybilOrchestrator(
                byzantine_tolerance=1,
                maintainer_strict_mode=False,
                governance_model="decentralized"   # DAO mode: peer votes decide
            )

            if not orchestrator.setup():
                logger.error("Setup failed")
                return 1

            orchestrator.setup_task("e-voting")

            # 7 rounds, max 3 agents submit PRs concurrently per round
            orchestrator.run_simulation(
                rounds=7,
                auto_block=True,
                agents_per_round=3
            )

        else:
            # ── Standard Simulation (unchanged) ──────────────────────────────
            logger.info("Mode: STANDARD — Single-agent governance simulation")
            logger.info("with Peer Review Consensus + Maintainer Agent")
            logger.info("=" * 70)

            orchestrator = PeerReviewOrchestrator(
                byzantine_tolerance=1,
                maintainer_strict_mode=False,
                governance_model="decentralized"
            )

            if not orchestrator.setup():
                logger.error("Setup failed")
                return 1

            orchestrator.setup_task("e-voting")
            orchestrator.run_simulation(rounds=15, auto_block=True)

        logger.info("\n[SUCCESS] Simulation completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())