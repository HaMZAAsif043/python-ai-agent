"""
Scheduler for automated job searches.
This module handles scheduling recurring job searches based on user preferences.
"""
import os
import time
import logging
import schedule
import threading
from datetime import datetime

from src.config import load_config
from src.agent import JobSearchAgent
from src.utils.logger import setup_logger

logger = logging.getLogger(__name__)

class JobSearchScheduler:
    """Scheduler for automated job searches."""
    
    def __init__(self, config_path=None):
        """
        Initialize the job search scheduler.
        
        Args:
            config_path (str, optional): Path to the configuration file.
        """
        self.config = load_config(config_path)
        self.scheduler_config = self.config.get('scheduler', {})
        self.is_running = False
        self._stop_event = threading.Event()
        
        # Set up logging
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.logger = setup_logger(os.path.join(log_dir, f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"))
    
    def setup_schedule(self):
        """Set up the job search schedule based on configuration."""
        if not self.scheduler_config.get('enabled', False):
            logger.info("Scheduler is disabled in configuration.")
            return False
        
        frequency = self.scheduler_config.get('frequency', 'daily').lower()
        time_str = self.scheduler_config.get('time', '09:00')
        
        logger.info(f"Setting up {frequency} job search schedule at {time_str}")
        
        if frequency == 'hourly':
            schedule.every().hour.at(":00").do(self._run_job_search)
        elif frequency == 'daily':
            schedule.every().day.at(time_str).do(self._run_job_search)
        elif frequency == 'weekly':
            schedule.every().monday.at(time_str).do(self._run_job_search)
        else:
            logger.error(f"Unsupported frequency: {frequency}")
            return False
        
        return True
    
    def _run_job_search(self):
        """Run the job search task."""
        try:
            logger.info("Starting scheduled job search")
            
            # Initialize the agent
            agent = JobSearchAgent(self.config)
            
            # Run the search
            results = agent.run()
            
            # Save and process results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            agent.save_results(results, timestamp)
            
            # Log summary
            logger.info(f"Scheduled job search complete. Found {len(results)} opportunities.")
            
            # Send notifications if enabled
            self._send_notifications(results)
            
            return True
        
        except Exception as e:
            logger.exception(f"Error in scheduled job search: {str(e)}")
            return False
    
    def _send_notifications(self, results):
        """
        Send notifications about job search results.
        
        Args:
            results (list): List of job opportunities found.
        """
        if not results:
            return
            
        notification_config = self.config.get('notifications', {})
        
        # Email notifications
        email_config = notification_config.get('email', {})
        if email_config.get('enabled', False):
            try:
                # This would be implemented to send email notifications
                # Not fully implemented in this example
                logger.info(f"Would send email notification to {email_config.get('address')} with {len(results)} jobs")
            except Exception as e:
                logger.error(f"Failed to send email notification: {str(e)}")
        
        # Desktop notifications
        desktop_config = notification_config.get('desktop', {})
        if desktop_config.get('enabled', False):
            try:
                # This would be implemented to send desktop notifications
                # Not fully implemented in this example
                logger.info(f"Would display desktop notification with {len(results)} jobs")
            except Exception as e:
                logger.error(f"Failed to send desktop notification: {str(e)}")
    
    def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running.")
            return
            
        if not self.setup_schedule():
            logger.error("Failed to set up schedule. Scheduler not started.")
            return
            
        self.is_running = True
        self._stop_event.clear()
        
        logger.info("Starting job search scheduler")
        
        # Start the scheduler in a separate thread
        thread = threading.Thread(target=self._run_scheduler)
        thread.daemon = True
        thread.start()
    
    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            logger.warning("Scheduler is not running.")
            return
            
        logger.info("Stopping job search scheduler")
        self._stop_event.set()
        self.is_running = False
        schedule.clear()
    
    def _run_scheduler(self):
        """Run the scheduler loop."""
        logger.info("Scheduler loop started")
        
        while not self._stop_event.is_set():
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
        logger.info("Scheduler loop stopped")