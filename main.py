"""
Main entry point for GOVIM simulation with Peer Review Consensus
"""

import sys
import logging
import codecs

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.utils.logger import setup_logging
from src.orchestrator import PeerReviewOrchestrator

# Setup logging
logger = setup_logging("govim")


def main():
    """Main entry point"""
    logger.info("\n" + "="*70)
    logger.info("GOVIM: GOVERNANCE SIMULATION FRAMEWORK")
    logger.info("with Peer Review Consensus + Maintainer Agent")
    logger.info("="*70)
    
    try:
        # Create orchestrator with peer review system
        # byzantine_tolerance=1 means tolerating 1 wrong peer review (needs 3+ benign agents)
        # maintainer_strict_mode=True for more aggressive detection
        orchestrator = PeerReviewOrchestrator(
            byzantine_tolerance=1,
            maintainer_strict_mode=False
        )
        
        # Step 1: Setup infrastructure
        if not orchestrator.setup():
            logger.error("Setup failed")
            return 1
        
        # Step 2: Setup task and assign features
        # Options: "e-voting", "banking", "medical", "supply_chain"
        task_choice = "e-voting"
        orchestrator.setup_task(task_choice)
        
        # Step 3: Run simulation with peer review consensus
        # auto_block=True will automatically block agents with low trust
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