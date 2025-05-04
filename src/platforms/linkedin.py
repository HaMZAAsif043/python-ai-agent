"""
LinkedIn connector for job searching.
This module provides functionality to search for jobs on LinkedIn.
"""
import time
import logging
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from src.platforms.base import BaseConnector

logger = logging.getLogger(__name__)

class LinkedinConnector(BaseConnector):
    """Connector for searching jobs on LinkedIn."""
    
    def __init__(self, settings):
        """Initialize the LinkedIn connector."""
        super().__init__(settings)
        self.base_url = "https://www.linkedin.com"
        self.search_url = f"{self.base_url}/jobs/search"
        self._driver = None
    
    def authenticate(self):
        """
        Authenticate with LinkedIn.
        
        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        try:
            # Setup Chrome options
            chrome_options = Options()
            if not self.settings.get('show_browser', False):
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # Initialize Chrome driver
            self._driver = webdriver.Chrome(options=chrome_options)
            
            # Navigate to LinkedIn login page
            self._driver.get(f"{self.base_url}/login")
            
            # Wait for the page to load
            WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            
            # Fill in login credentials
            username_field = self._driver.find_element(By.ID, "username")
            password_field = self._driver.find_element(By.ID, "password")
            
            username_field.send_keys(self.credentials.get('username', ''))
            password_field.send_keys(self.credentials.get('password', ''))
            
            # Submit login form
            password_field.submit()
            
            # Wait for login to complete
            WebDriverWait(self._driver, 10).until(
                EC.url_contains("feed")
            )
            
            logger.info("Successfully logged in to LinkedIn")
            return True
            
        except Exception as e:
            logger.error(f"Failed to authenticate with LinkedIn: {str(e)}")
            if self._driver:
                self._driver.quit()
                self._driver = None
            return False
    
    def search_jobs(self, keywords, locations, job_types, remote=False, experience_levels=None):
        """
        Search for job opportunities on LinkedIn.
        
        Args:
            keywords (list): List of keywords to search for.
            locations (list): List of locations to search in.
            job_types (list): List of job types.
            remote (bool): Whether to search for remote jobs.
            experience_levels (list): List of experience levels to search for.
            
        Returns:
            list: List of job opportunities found on LinkedIn.
        """
        results = []
        
        try:
            if not self._driver:
                if not self.authenticate():
                    return results
            
            # Process each keyword
            for keyword in keywords:
                for location in locations:
                    logger.info(f"Searching LinkedIn for '{keyword}' in '{location}'")
                    
                    # Build search URL
                    search_query = f"{keyword}"
                    search_params = f"?keywords={search_query}&location={location}"
                    
                    if remote:
                        search_params += "&f_WT=2"  # LinkedIn's remote filter
                    
                    # Add job type filters
                    job_type_params = self._get_job_type_params(job_types)
                    if job_type_params:
                        search_params += job_type_params
                    
                    # Add experience level filters
                    exp_level_params = self._get_experience_level_params(experience_levels)
                    if exp_level_params:
                        search_params += exp_level_params
                    
                    # Set date posted filter (e.g., past week)
                    post_days = self.search_criteria.get('post_days', 7)
                    date_posted_param = self._get_date_posted_param(post_days)
                    if date_posted_param:
                        search_params += date_posted_param
                    
                    # Navigate to search URL
                    search_url = f"{self.search_url}{search_params}"
                    self._driver.get(search_url)
                    
                    # Wait for search results to load
                    WebDriverWait(self._driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "jobs-search__results-list"))
                    )
                    
                    # Extract job listings
                    time.sleep(2)  # Allow dynamic content to load
                    page_results = self._extract_job_listings()
                    results.extend(page_results)
                    
                    # Pagination - get more pages of results if available
                    try:
                        max_pages = 3  # Limit to prevent too many requests
                        current_page = 1
                        
                        while current_page < max_pages:
                            next_button = self._driver.find_element(By.XPATH, "//button[@aria-label='Next']")
                            if next_button and next_button.is_enabled():
                                next_button.click()
                                time.sleep(2)  # Wait for page to load
                                
                                WebDriverWait(self._driver, 10).until(
                                    EC.presence_of_element_located((By.CLASS_NAME, "jobs-search__results-list"))
                                )
                                
                                page_results = self._extract_job_listings()
                                results.extend(page_results)
                                current_page += 1
                            else:
                                break
                    except Exception as e:
                        logger.warning(f"Pagination error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error searching LinkedIn jobs: {str(e)}")
        
        finally:
            if self._driver:
                self._driver.quit()
                self._driver = None
        
        return results
    
    def get_job_details(self, job_id):
        """
        Get detailed information about a specific LinkedIn job.
        
        Args:
            job_id (str): LinkedIn job ID.
            
        Returns:
            dict: Detailed information about the job.
        """
        job_url = f"{self.base_url}/jobs/view/{job_id}"
        
        try:
            if not self._driver:
                if not self.authenticate():
                    return {}
            
            self._driver.get(job_url)
            
            WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "jobs-unified-top-card"))
            )
            
            # Extract job details
            title_element = self._driver.find_element(By.CLASS_NAME, "jobs-unified-top-card__job-title")
            company_element = self._driver.find_element(By.CLASS_NAME, "jobs-unified-top-card__company-name")
            location_element = self._driver.find_element(By.CLASS_NAME, "jobs-unified-top-card__bullet")
            
            description_element = self._driver.find_element(By.CLASS_NAME, "jobs-description-content__text")
            
            job_details = {
                'id': job_id,
                'title': title_element.text,
                'company': company_element.text,
                'location': location_element.text,
                'description': description_element.text,
                'url': job_url,
            }
            
            # Try to get additional information if available
            try:
                job_criteria_elements = self._driver.find_elements(By.CLASS_NAME, "job-criteria-item")
                
                for element in job_criteria_elements:
                    header = element.find_element(By.CLASS_NAME, "job-criteria-subheader").text
                    value = element.find_element(By.CLASS_NAME, "job-criteria-text").text
                    
                    if "Seniority" in header:
                        job_details['experience_level'] = value
                    elif "Employment type" in header:
                        job_details['job_type'] = value
                    elif "Industry" in header:
                        job_details['industry'] = value
                
            except Exception as e:
                logger.debug(f"Could not extract additional job details: {str(e)}")
            
            return self._normalize_job_data(job_details)
            
        except Exception as e:
            logger.error(f"Error getting LinkedIn job details: {str(e)}")
            return {}
        
        finally:
            if self._driver:
                self._driver.quit()
                self._driver = None
    
    def apply_to_job(self, job_id, application_data):
        """
        Apply to a specific job on LinkedIn.
        
        Args:
            job_id (str): LinkedIn job ID.
            application_data (dict): Application data including cover letter, etc.
            
        Returns:
            bool: True if application was submitted successfully, False otherwise.
        """
        # NOTE: Implementing a full automated application process requires careful handling
        # This is a partial implementation for demonstration purposes
        logger.warning("Automated LinkedIn applications are not fully implemented")
        return False
    
    def _extract_job_listings(self):
        """
        Extract job listings from the current search results page.
        
        Returns:
            list: List of job data dictionaries.
        """
        job_results = []
        
        try:
            job_cards = self._driver.find_elements(By.CSS_SELECTOR, ".jobs-search__results-list li")
            
            for card in job_cards:
                try:
                    # Extract basic job information from card
                    title_element = card.find_element(By.CSS_SELECTOR, "h3.base-search-card__title")
                    company_element = card.find_element(By.CSS_SELECTOR, "h4.base-search-card__subtitle")
                    location_element = card.find_element(By.CSS_SELECTOR, ".job-search-card__location")
                    link_element = card.find_element(By.CSS_SELECTOR, "a.base-card__full-link")
                    
                    job_url = link_element.get_attribute('href')
                    job_id = job_url.split('/')[-1]
                    
                    # Try to get posted date if available
                    date_posted = ""
                    try:
                        date_element = card.find_element(By.CSS_SELECTOR, "time.job-search-card__listdate")
                        date_posted = date_element.get_attribute('datetime')
                    except:
                        pass
                    
                    job_data = {
                        'id': job_id,
                        'title': title_element.text,
                        'company': company_element.text,
                        'location': location_element.text,
                        'url': job_url,
                        'date_posted': date_posted,
                    }
                    
                    job_results.append(self._normalize_job_data(job_data))
                    
                except Exception as e:
                    logger.debug(f"Error extracting job card data: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error extracting job listings: {str(e)}")
        
        return job_results
    
    def _get_job_type_params(self, job_types):
        """Convert job type list to LinkedIn filter parameters."""
        params = ""
        
        # LinkedIn job type parameter mapping
        job_type_map = {
            "Full-time": "F",
            "Part-time": "P", 
            "Contract": "C",
            "Temporary": "T",
            "Volunteer": "V",
            "Internship": "I"
        }
        
        for job_type in job_types:
            if job_type in job_type_map:
                params += f"&f_JT={job_type_map[job_type]}"
        
        return params
    
    def _get_experience_level_params(self, experience_levels):
        """Convert experience level list to LinkedIn filter parameters."""
        if not experience_levels:
            return ""
            
        params = ""
        
        # LinkedIn experience level parameter mapping
        exp_level_map = {
            "Internship": "1",
            "Entry level": "2",
            "Associate": "3",
            "Mid-level": "4",
            "Senior": "5",
            "Director": "6",
            "Executive": "7"
        }
        
        for level in experience_levels:
            if level in exp_level_map:
                params += f"&f_E={exp_level_map[level]}"
        
        return params
    
    def _get_date_posted_param(self, days):
        """Convert days to LinkedIn date posted parameter."""
        # LinkedIn date posted parameter mapping
        if days <= 1:
            return "&f_TPR=r86400"  # Past 24 hours
        elif days <= 7:
            return "&f_TPR=r604800"  # Past week
        elif days <= 30:
            return "&f_TPR=r2592000"  # Past month
        else:
            return ""  # Any time