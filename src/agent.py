"""
Job Search Agent implementation.
This module contains the main agent class that coordinates job searches
across multiple platforms.
"""
import os
import csv
import json
import logging
import pandas as pd
from datetime import datetime
from importlib import import_module

logger = logging.getLogger(__name__)

class JobSearchAgent:
    """Job Search Agent that searches for job opportunities based on user preferences."""
    
    def __init__(self, config):
        """
        Initialize the Job Search Agent.
        
        Args:
            config (dict): Configuration dictionary with user preferences and platform settings.
        """
        self.config = config
        self.user_profile = config['user_profile']
        self.job_search = config['job_search']
        self.platforms = {}
        self._load_platforms()
        
    def _load_platforms(self):
        """Load and initialize job search platform connectors."""
        for platform_name, settings in self.config['platforms'].items():
            if not settings.get('enabled', False):
                logger.info(f"Platform {platform_name} is disabled, skipping")
                continue
                
            try:
                # Import platform connector dynamically
                module_path = f"src.platforms.{platform_name}"
                platform_module = import_module(module_path)
                
                # Create platform connector instance
                connector_class = getattr(platform_module, f"{platform_name.capitalize()}Connector")
                connector = connector_class(settings)
                
                self.platforms[platform_name] = connector
                logger.info(f"Successfully loaded platform: {platform_name}")
                
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to load platform {platform_name}: {str(e)}")
    
    def run(self):
        """
        Run the job search across all enabled platforms.
        
        Returns:
            list: List of job opportunities found across all platforms.
        """
        all_results = []
        
        for platform_name, connector in self.platforms.items():
            try:
                logger.info(f"Starting job search on {platform_name}")
                
                # Perform job search
                keywords = self.job_search.get('keywords', [])
                locations = self.job_search.get('locations', [])
                job_types = self.job_search.get('job_types', [])
                
                results = connector.search_jobs(
                    keywords=keywords,
                    locations=locations,
                    job_types=job_types,
                    remote=self.job_search.get('remote', False),
                    experience_levels=self.job_search.get('experience_level', [])
                )
                
                # Filter results based on exclusion criteria
                filtered_results = self._filter_results(results)
                
                # Add platform name to each result
                for result in filtered_results:
                    result['platform'] = platform_name
                
                all_results.extend(filtered_results)
                logger.info(f"Found {len(filtered_results)} matching jobs on {platform_name}")
                
            except Exception as e:
                logger.error(f"Error searching on platform {platform_name}: {str(e)}")
        
        # Sort results by relevance or date
        all_results.sort(key=lambda x: x.get('date_posted', ''), reverse=True)
        
        return all_results
    
    def _filter_results(self, results):
        """
        Filter job results based on exclusion criteria.
        
        Args:
            results (list): List of job postings to filter.
            
        Returns:
            list: Filtered list of job postings.
        """
        exclude_keywords = self.job_search.get('exclude_keywords', [])
        
        if not exclude_keywords:
            return results
            
        filtered_results = []
        for job in results:
            # Check if any exclusion keyword appears in the job title or description
            title = job.get('title', '').lower()
            description = job.get('description', '').lower()
            
            if not any(kw.lower() in title or kw.lower() in description for kw in exclude_keywords):
                filtered_results.append(job)
        
        return filtered_results
    
    def save_results(self, results, timestamp=None):
        """
        Save job search results to CSV and JSON files.
        
        Args:
            results (list): List of job opportunities to save.
            timestamp (str, optional): Timestamp to include in the filenames.
        """
        if not results:
            logger.warning("No results to save")
            return
            
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # Save as CSV
        csv_path = os.path.join(reports_dir, f"job_search_{timestamp}.csv")
        try:
            df = pd.DataFrame(results)
            df.to_csv(csv_path, index=False)
            logger.info(f"Saved {len(results)} job opportunities to {csv_path}")
        except Exception as e:
            logger.error(f"Error saving results to CSV: {str(e)}")
        
        # Save as JSON
        json_path = os.path.join(reports_dir, f"job_search_{timestamp}.json")
        try:
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=4)
            logger.info(f"Saved {len(results)} job opportunities to {json_path}")
        except Exception as e:
            logger.error(f"Error saving results to JSON: {str(e)}")
    
    def display_summary(self, results):
        """
        Display a summary of job search results.
        
        Args:
            results (list): List of job opportunities to display.
        """
        if not results:
            print("No matching job opportunities found.")
            return
            
        print(f"\n=== Job Search Results Summary ===")
        print(f"Total opportunities found: {len(results)}")
        
        # Group by platform
        platform_counts = {}
        for job in results:
            platform = job.get('platform', 'Unknown')
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            
        print("\nResults by Platform:")
        for platform, count in platform_counts.items():
            print(f"- {platform}: {count} jobs")
            
        # Group by job type
        job_type_counts = {}
        for job in results:
            job_type = job.get('job_type', 'Unknown')
            job_type_counts[job_type] = job_type_counts.get(job_type, 0) + 1
            
        print("\nResults by Job Type:")
        for job_type, count in job_type_counts.items():
            print(f"- {job_type}: {count} jobs")
            
        # Display top 5 most recent jobs
        print("\nMost Recent Job Opportunities:")
        recent_jobs = sorted(results, key=lambda x: x.get('date_posted', ''), reverse=True)[:5]
        
        for i, job in enumerate(recent_jobs, start=1):
            print(f"\n{i}. {job.get('title', 'No title')} - {job.get('company', 'Unknown Company')}")
            print(f"   Platform: {job.get('platform', 'Unknown')}")
            print(f"   Location: {job.get('location', 'Unknown')}")
            print(f"   Date Posted: {job.get('date_posted', 'Unknown')}")
            print(f"   URL: {job.get('url', 'No URL provided')}")
            
        print(f"\nDetails for all {len(results)} job opportunities are available in the reports folder.")
    
    def submit_application(self, job_id, customize_application=True):
        """
        Submit an application for a specific job.
        
        Args:
            job_id (str): ID of the job to apply for.
            customize_application (bool): Whether to customize the application based on job details.
            
        Returns:
            bool: True if application was submitted successfully, False otherwise.
        """
        # This method would be implemented to handle automatic job applications
        # Not fully implemented in this example for safety reasons
        # Full implementation would include:
        # - Finding the job by ID from saved results
        # - Generating a customized cover letter using templates
        # - Submitting application through the appropriate platform connector
        # - Recording the application in a tracking system
        
        logger.warning("Automatic job application is not fully implemented")
        return False