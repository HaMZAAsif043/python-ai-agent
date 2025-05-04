"""
Base connector class for job search platforms.
All platform-specific connectors should inherit from this class.
"""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseConnector(ABC):
    """Base class for all job platform connectors."""
    
    def __init__(self, settings):
        """
        Initialize the connector with platform-specific settings.
        
        Args:
            settings (dict): Platform-specific settings including credentials and search criteria.
        """
        self.settings = settings
        self.credentials = settings.get('credentials', {})
        self.search_criteria = settings.get('search_criteria', {})
        self._session = None
    
    @abstractmethod
    def authenticate(self):
        """
        Authenticate with the platform API or website.
        
        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def search_jobs(self, keywords, locations, job_types, remote=False, experience_levels=None):
        """
        Search for job opportunities on the platform.
        
        Args:
            keywords (list): List of keywords to search for.
            locations (list): List of locations to search in.
            job_types (list): List of job types (full-time, part-time, contract, etc.).
            remote (bool): Whether to search for remote jobs.
            experience_levels (list): List of experience levels to search for.
            
        Returns:
            list: List of job opportunities found on the platform.
        """
        pass
    
    @abstractmethod
    def get_job_details(self, job_id):
        """
        Get detailed information about a specific job.
        
        Args:
            job_id (str): ID of the job to retrieve details for.
            
        Returns:
            dict: Detailed information about the job.
        """
        pass
    
    @abstractmethod
    def apply_to_job(self, job_id, application_data):
        """
        Apply to a specific job opportunity.
        
        Args:
            job_id (str): ID of the job to apply to.
            application_data (dict): Application data including resume, cover letter, etc.
            
        Returns:
            bool: True if application was submitted successfully, False otherwise.
        """
        pass
    
    def _normalize_job_data(self, raw_job):
        """
        Normalize job data to ensure consistent structure across platforms.
        
        Args:
            raw_job (dict): Raw job data from the platform.
            
        Returns:
            dict: Normalized job data.
        """
        # Default implementation can be overridden by platform-specific connectors
        return {
            'id': raw_job.get('id', ''),
            'title': raw_job.get('title', ''),
            'company': raw_job.get('company', ''),
            'location': raw_job.get('location', ''),
            'description': raw_job.get('description', ''),
            'url': raw_job.get('url', ''),
            'salary': raw_job.get('salary', ''),
            'date_posted': raw_job.get('date_posted', ''),
            'job_type': raw_job.get('job_type', ''),
            'experience_level': raw_job.get('experience_level', ''),
            'skills': raw_job.get('skills', []),
            'is_remote': raw_job.get('is_remote', False),
        }