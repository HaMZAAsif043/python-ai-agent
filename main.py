#!/usr/bin/env python3
"""
Job Search Agent - Main entry point
This script initializes and runs the job search agent to find job opportunities
based on configured preferences.
"""
import os
import sys
import logging
import argparse
from datetime import datetime

from src.config import load_config
from src.agent import JobSearchAgent
from src.scheduler import JobSearchScheduler
from src.utils.logger import setup_logger

def main():
    """Main entry point for the job search agent."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Job Search Agent')
    parser.add_argument('--schedule', action='store_true', help='Run in scheduler mode')
    parser.add_argument('--config', type=str, help='Path to custom configuration file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    
    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"job_search_{timestamp}.log")
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger(log_file, level=log_level)
    
    try:
        logger.info("Starting Job Search Agent")
        
        # Load configuration
        config = load_config(args.config)
        if not config:
            logger.error("Failed to load configuration. Exiting.")
            sys.exit(1)
        
        if args.schedule:
            # Run in scheduler mode
            run_scheduler()
        else:
            # Run a one-time job search
            run_one_time_search(config)
        
    except KeyboardInterrupt:
        logger.info("Job Search Agent interrupted by user")
    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        sys.exit(1)
    
    logger.info("Job Search Agent completed successfully")

def run_one_time_search(config):
    """
    Run a one-time job search.
    
    Args:
        config (dict): Configuration dictionary.
    """
    logger = logging.getLogger(__name__)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Initialize the agent
        agent = JobSearchAgent(config)
        
        # Run the agent
        logger.info("Running one-time job search")
        results = agent.run()
        
        # Process and display results
        logger.info(f"Job search complete. Found {len(results)} opportunities.")
        agent.save_results(results, timestamp)
        agent.display_summary(results)
        
    except Exception as e:
        logger.exception(f"Error in one-time job search: {str(e)}")
        raise

def run_scheduler():
    """Run the job search scheduler."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting job search scheduler")
        scheduler = JobSearchScheduler()
        scheduler.start()
        
        print("Job search scheduler started. Press Ctrl+C to stop.")
        
        # Keep the main thread alive
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Scheduler stopping due to user interrupt")
            scheduler.stop()
            
    except Exception as e:
        logger.exception(f"Error in scheduler: {str(e)}")
        raise

if __name__ == "__main__":
    main()
