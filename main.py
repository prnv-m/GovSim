"""
Main entry point for GOVIM simulation with Peer Review Consensus.

Usage
─────
  python main.py --model centralized              # no sybil attack
  python main.py --model decentralized --sybil    # sybil ring attack
  python main.py --all-models                     # all 3 models, no sybil
  python main.py --all-models --sybil             # all 3 models, sybil attack
"""

import sys
import io
import logging
import argparse
from pathlib import Path

# Ensure project root is always on sys.path regardless of working directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from src.utils.logger import setup_logging
from src.orchestrator import PeerReviewOrchestrator, SybilOrchestrator
from config import Config

# Setup logging
logger = setup_logging("govim")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="GOVIM Governance Simulation")
    parser.add_argument(
        "--model",
        choices=["centralized", "decentralized", "hybrid"],
        default=None,
        help="Governance model to use (default: decentralized)",
    )
    parser.add_argument(
        "--all-models",
        action="store_true",
        help="Run all three governance models sequentially",
    )
    parser.add_argument(
        "--sybil",
        action="store_true",
        default=False,
        help="Enable Sybil ring attack mode (3 coordinated attackers, 7 rounds)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Number of rounds to run (default: 5 for normal, 7 for sybil)",
    )
    args = parser.parse_args()

    models_to_run = (
        ["centralized", "decentralized", "hybrid"] if args.all_models
        else [args.model or "decentralized"]
    )

    # Resolve round count: CLI flag > mode defaults
    if args.rounds is not None:
        rounds = args.rounds
    elif args.sybil:
        rounds = 7
    else:
        rounds = 5

    logger.info("\n" + "=" * 70)
    logger.info("GOVIM: GOVERNANCE SIMULATION FRAMEWORK")
    logger.info(f"Sybil mode: {'ON' if args.sybil else 'OFF'} | Rounds: {rounds}")

    try:
        for model in models_to_run:
            logger.info(f"\n{'=' * 70}")
            logger.info(f"Running model: {model.upper()}")
            logger.info("=" * 70)

            if args.sybil:
                logger.info("Mode: SYBIL ATTACK — Advanced Red Team Demonstration")
                logger.info(f"{Config.SYBIL_AGENT_COUNT} coordinated attacker(s) | max 3 PRs/round | {rounds} rounds | model={model}")

                orchestrator = SybilOrchestrator(
                    byzantine_tolerance=1,
                    maintainer_strict_mode=False,
                    governance_model=model,
                )

                if not orchestrator.setup():
                    logger.error("Setup failed")
                    return 1

                orchestrator.setup_task("e-voting")
                orchestrator.run_simulation(rounds=rounds, auto_block=True, agents_per_round=3)

            else:
                logger.info("Mode: STANDARD — Single-agent governance simulation")
                logger.info(f"with Peer Review Consensus + Maintainer Agent | model={model}")

                orchestrator = PeerReviewOrchestrator(
                    byzantine_tolerance=1,
                    maintainer_strict_mode=False,
                    governance_model=model,
                )

                if not orchestrator.setup():
                    logger.error("Setup failed")
                    return 1

                orchestrator.setup_task("e-voting")
                orchestrator.run_simulation(rounds=rounds, auto_block=True)

        logger.info("\n[SUCCESS] All runs completed. Results saved to data/results/")
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())