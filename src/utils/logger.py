"""
Logger setup for the Job Search Agent.
"""
import logging
import os
import sys

def setup_logger(log_file=None, level=logging.INFO):
    """
    Setup logger configuration for the Job Search Agent.
    
    Args:
        log_file (str, optional): Path to the log file.
        level (int, optional): Logging level. Defaults to logging.INFO.
        
    Returns:
        logging.Logger: Logger instance.
    """
    # Create a logger
    logger = logging.getLogger("JobSearchAgent")
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger