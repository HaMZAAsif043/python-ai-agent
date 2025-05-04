#!/usr/bin/env python3
"""
Job Search Agent - Main entry point
This script initializes and runs the job search agent to find job opportunities
based on configured preferences.
"""
import os
import sys
import logging
from datetime import datetime

from src.config import load_config
from src.agent import JobSearchAgent
from src.utils.logger import setup_logger

def main():
    """Main entry point for the job search agent."""
    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"job_search_{timestamp}.log")
    logger = setup_logger(log_file)
    
    try:
        logger.info("Starting Job Search Agent")
        
        # Load configuration
        config = load_config()
        if not config:
            logger.error("Failed to load configuration. Exiting.")
            sys.exit(1)
        
        # Initialize the agent
        agent = JobSearchAgent(config)
        
        # Run the agent
        results = agent.run()
        
        # Process and display results
        logger.info(f"Job search complete. Found {len(results)} opportunities.")
        agent.save_results(results, timestamp)
        agent.display_summary(results)
        
    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        sys.exit(1)
    
    logger.info("Job Search Agent completed successfully")


if __name__ == "__main__":
    main()
