"""
Main entry point for GOVIM simulation
"""

import sys
import logging
from src.utils.logger import setup_logging
from src.orchestrator import Orchestrator


# Setup logging
logger = setup_logging("govim")


def main():
    """Main entry point"""
    logger.info("\n" + "="*70)
    logger.info("GOVIM: GOVERNANCE SIMULATION FRAMEWORK")
    logger.info("="*70)
    
    try:
        # Create orchestrator
        orchestrator = Orchestrator()
        
        # Step 1: Setup infrastructure
        if not orchestrator.setup():
            logger.error("Setup failed")
            return 1
        
        # Step 2: Setup task and assign features
        task_choice = "e-voting"  # ← Change to: "banking", "medical", "supply_chain"
        orchestrator.setup_task(task_choice)
        
        orchestrator.run_simulation(rounds=3)
        results = orchestrator.detect_malicious_commits()
        if results:
            logger.info("[OK] Detection completed successfully")
        logger.info("\n Simulation completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
