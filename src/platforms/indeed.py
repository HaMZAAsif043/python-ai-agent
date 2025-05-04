"""
Indeed connector for job searching.
This module provides functionality to search for jobs on Indeed.
"""
import time
import logging
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.platforms.base import BaseConnector

logger = logging.getLogger(__name__)

class IndeedConnector(BaseConnector):
    """Connector for searching jobs on Indeed."""
    
    def __init__(self, settings):
        """Initialize the Indeed connector."""
        super().__init__(settings)
        self.base_url = "https://www.indeed.com"
        self._driver = None
    
    def authenticate(self):
        """
        Set up the Indeed connection.
        
        Returns:
            bool: True if setup was successful, False otherwise.
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
            self._driver.get(self.base_url)
            
            # Wait for page to load
            WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.ID, "jobsearch"))
            )
            
            logger.info("Successfully connected to Indeed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up Indeed connection: {str(e)}")
            if self._driver:
                self._driver.quit()
                self._driver = None
            return False
    
    def search_jobs(self, keywords, locations, job_types, remote=False, experience_levels=None):
        """
        Search for job opportunities on Indeed.
        
        Args:
            keywords (list): List of keywords to search for.
            locations (list): List of locations to search in.
            job_types (list): List of job types.
            remote (bool): Whether to search for remote jobs.
            experience_levels (list): List of experience levels to search for.
            
        Returns:
            list: List of job opportunities found on Indeed.
        """
        results = []
        
        try:
            if not self._driver:
                if not self.authenticate():
                    return results
            
            # Process each keyword
            for keyword in keywords:
                for location in locations:
                    location_query = location
                    if remote and location.lower() == 'remote':
                        location_query = ""  # We'll use Indeed's remote filter instead
                    
                    logger.info(f"Searching Indeed for '{keyword}' in '{location}'")
                    
                    # Navigate to search page and enter search parameters
                    self._driver.get(self.base_url)
                    
                    # Wait for search form to load
                    WebDriverWait(self._driver, 10).until(
                        EC.presence_of_element_located((By.ID, "text-input-what"))
                    )
                    
                    # Enter job keyword
                    what_input = self._driver.find_element(By.ID, "text-input-what")
                    what_input.clear()
                    what_input.send_keys(keyword)
                    
                    # Enter location if not remote
                    where_input = self._driver.find_element(By.ID, "text-input-where")
                    where_input.clear()
                    if location_query:
                        where_input.send_keys(location_query)
                    elif remote:
                        # If searching for remote jobs, clear the location field
                        where_input.send_keys(Keys.CONTROL + "a")
                        where_input.send_keys(Keys.DELETE)
                    
                    # Submit search form
                    what_input.submit()
                    
                    # Wait for search results
                    WebDriverWait(self._driver, 10).until(
                        EC.presence_of_element_located((By.ID, "mosaic-provider-jobcards"))
                    )
                    
                    # Apply filters if needed
                    if remote:
                        self._apply_remote_filter()
                        
                    if job_types:
                        self._apply_job_type_filters(job_types)
                    
                    if experience_levels:
                        self._apply_experience_filters(experience_levels)
                    
                    # Apply date posted filter
                    post_days = self.search_criteria.get('post_days', 14)
                    self._apply_date_filter(post_days)
                    
                    # Extract job listings
                    time.sleep(2)  # Allow any dynamic content to load
                    page_results = self._extract_job_listings()
                    results.extend(page_results)
                    
                    # Check for more pages, up to a reasonable limit
                    max_pages = 3
                    current_page = 1
                    
                    try:
                        while current_page < max_pages:
                            # Look for "Next" pagination button
                            next_button = None
                            try:
                                next_button = self._driver.find_element(By.CSS_SELECTOR, "[data-testid='pagination-page-next']")
                            except NoSuchElementException:
                                break
                                
                            if next_button and next_button.is_enabled():
                                next_button.click()
                                time.sleep(2)  # Wait for page to load
                                
                                # Wait for job cards to load
                                WebDriverWait(self._driver, 10).until(
                                    EC.presence_of_element_located((By.ID, "mosaic-provider-jobcards"))
                                )
                                
                                page_results = self._extract_job_listings()
                                results.extend(page_results)
                                current_page += 1
                            else:
                                break
                                
                    except Exception as e:
                        logger.warning(f"Error during pagination: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error searching Indeed jobs: {str(e)}")
        
        finally:
            if self._driver:
                self._driver.quit()
                self._driver = None
        
        return results
    
    def get_job_details(self, job_id):
        """
        Get detailed information about a specific Indeed job.
        
        Args:
            job_id (str): Indeed job ID.
            
        Returns:
            dict: Detailed information about the job.
        """
        job_url = f"{self.base_url}/viewjob?jk={job_id}"
        
        try:
            if not self._driver:
                if not self.authenticate():
                    return {}
            
            self._driver.get(job_url)
            
            # Wait for job details to load
            WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.ID, "viewJobSSRRoot"))
            )
            
            # Extract job details
            job_details = {}
            
            try:
                job_details['id'] = job_id
                job_details['url'] = job_url
                
                # Get job title
                title_element = self._driver.find_element(By.CSS_SELECTOR, "h1.jobsearch-JobInfoHeader-title")
                job_details['title'] = title_element.text
                
                # Get company name
                company_element = self._driver.find_element(By.CSS_SELECTOR, "div[data-company-name='true']")
                job_details['company'] = company_element.text
                
                # Get location
                location_element = self._driver.find_element(By.CSS_SELECTOR, "div[data-testid='inlineHeader-companyLocation']")
                job_details['location'] = location_element.text
                
                # Get job description
                description_element = self._driver.find_element(By.ID, "jobDescriptionText")
                job_details['description'] = description_element.text
                
                # Try to get salary if available
                try:
                    salary_element = self._driver.find_element(By.CSS_SELECTOR, "div[data-testid='attribute_snippet_compensation']")
                    job_details['salary'] = salary_element.text
                except NoSuchElementException:
                    job_details['salary'] = ""
                    
                # Try to get job type if available
                try:
                    job_type_element = self._driver.find_element(By.CSS_SELECTOR, "div[data-testid='attribute_snippet_job_type']")
                    job_details['job_type'] = job_type_element.text
                except NoSuchElementException:
                    job_details['job_type'] = ""
                
            except Exception as e:
                logger.debug(f"Could not extract some job details: {str(e)}")
            
            return self._normalize_job_data(job_details)
            
        except Exception as e:
            logger.error(f"Error getting Indeed job details: {str(e)}")
            return {}
        
        finally:
            if self._driver:
                self._driver.quit()
                self._driver = None
    
    def apply_to_job(self, job_id, application_data):
        """
        Apply to a specific job on Indeed.
        
        Args:
            job_id (str): Indeed job ID.
            application_data (dict): Application data including cover letter, etc.
            
        Returns:
            bool: True if application was submitted successfully, False otherwise.
        """
        # NOTE: Implementing a full automated application process requires careful handling
        # This is a partial implementation for demonstration purposes
        logger.warning("Automated Indeed applications are not fully implemented")
        return False
    
    def _extract_job_listings(self):
        """
        Extract job listings from the current search results page.
        
        Returns:
            list: List of job data dictionaries.
        """
        job_results = []
        
        try:
            # Wait for job cards to appear
            WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='jobCard']"))
            )
            
            # Get all job cards
            job_cards = self._driver.find_elements(By.CSS_SELECTOR, "[data-testid='jobCard']")
            
            for card in job_cards:
                try:
                    # Extract job data from card
                    
                    # Get job title and URL
                    title_element = card.find_element(By.CSS_SELECTOR, "h2.jobTitle")
                    title_link = title_element.find_element(By.TAG_NAME, "a")
                    job_title = title_element.text
                    job_url = title_link.get_attribute('href')
                    
                    # Extract job ID from URL
                    job_id = ""
                    jk_match = re.search(r'jk=([^&]+)', job_url)
                    if jk_match:
                        job_id = jk_match.group(1)
                    
                    # Get company name
                    company_element = card.find_element(By.CSS_SELECTOR, "span.companyName")
                    company_name = company_element.text
                    
                    # Get location
                    location_element = card.find_element(By.CSS_SELECTOR, "div.companyLocation")
                    location = location_element.text
                    
                    # Try to get salary if available
                    salary = ""
                    try:
                        salary_element = card.find_element(By.CSS_SELECTOR, "div.salary-snippet")
                        salary = salary_element.text
                    except NoSuchElementException:
                        pass
                    
                    # Try to get job snippet/description
                    description = ""
                    try:
                        description_element = card.find_element(By.CSS_SELECTOR, "div.job-snippet")
                        description = description_element.text
                    except NoSuchElementException:
                        pass
                    
                    # Try to get posting date
                    date_posted = ""
                    try:
                        date_element = card.find_element(By.CSS_SELECTOR, "span.date")
                        date_text = date_element.text
                        
                        # Convert relative date to timestamp
                        today = datetime.now().date()
                        if "Just posted" in date_text or "Today" in date_text:
                            date_posted = today.isoformat()
                        elif "day ago" in date_text or "days ago" in date_text:
                            days = int(re.search(r'(\d+)', date_text).group(1))
                            date_posted = (today - timedelta(days=days)).isoformat()
                        
                    except (NoSuchElementException, AttributeError):
                        pass
                    
                    # Create job data dictionary
                    job_data = {
                        'id': job_id,
                        'title': job_title,
                        'company': company_name,
                        'location': location,
                        'url': job_url,
                        'salary': salary,
                        'description': description,
                        'date_posted': date_posted,
                    }
                    
                    job_results.append(self._normalize_job_data(job_data))
                    
                except Exception as e:
                    logger.debug(f"Error extracting Indeed job card data: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error extracting Indeed job listings: {str(e)}")
        
        return job_results
    
    def _apply_remote_filter(self):
        """Apply remote work filter to search results."""
        try:
            remote_checkbox = WebDriverWait(self._driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[id*='remotejob']"))
            )
            if not remote_checkbox.is_selected():
                remote_checkbox.click()
                time.sleep(2)  # Wait for results to update
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"Could not apply remote filter: {str(e)}")
    
    def _apply_job_type_filters(self, job_types):
        """Apply job type filters to search results."""
        try:
            # Map our job types to Indeed's filter values
            indeed_job_types = []
            for job_type in job_types:
                if "full" in job_type.lower():
                    indeed_job_types.append("fulltime")
                elif "part" in job_type.lower():
                    indeed_job_types.append("parttime")
                elif "contract" in job_type.lower() or "freelance" in job_type.lower():
                    indeed_job_types.append("contract")
                elif "intern" in job_type.lower():
                    indeed_job_types.append("internship")
            
            # Click the "Job type" filter dropdown
            filter_button = WebDriverWait(self._driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='jobType-filter']"))
            )
            filter_button.click()
            
            # Select job types
            for jt in indeed_job_types:
                try:
                    checkbox = self._driver.find_element(By.CSS_SELECTOR, f"input[id*='{jt}']")
                    if not checkbox.is_selected():
                        # Use JavaScript to click, as the checkboxes might be covered by other elements
                        self._driver.execute_script("arguments[0].click();", checkbox)
                except NoSuchElementException:
                    continue
            
            # Apply filters
            apply_button = self._driver.find_element(By.CSS_SELECTOR, "button[data-testid='filter-pill-apply']")
            apply_button.click()
            time.sleep(2)  # Wait for results to update
            
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"Could not apply job type filters: {str(e)}")
    
    def _apply_experience_filters(self, experience_levels):
        """Apply experience level filters to search results."""
        try:
            # Map our experience levels to Indeed's filter values
            indeed_exp_levels = []
            for level in experience_levels:
                if "entry" in level.lower():
                    indeed_exp_levels.append("entry_level")
                elif "mid" in level.lower():
                    indeed_exp_levels.append("mid_level")
                elif "senior" in level.lower():
                    indeed_exp_levels.append("senior_level")
            
            # Click the "Experience level" filter dropdown
            filter_button = WebDriverWait(self._driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='experienceLevel-filter']"))
            )
            filter_button.click()
            
            # Select experience levels
            for exp in indeed_exp_levels:
                try:
                    checkbox = self._driver.find_element(By.CSS_SELECTOR, f"input[id*='{exp}']")
                    if not checkbox.is_selected():
                        # Use JavaScript to click, as the checkboxes might be covered by other elements
                        self._driver.execute_script("arguments[0].click();", checkbox)
                except NoSuchElementException:
                    continue
            
            # Apply filters
            apply_button = self._driver.find_element(By.CSS_SELECTOR, "button[data-testid='filter-pill-apply']")
            apply_button.click()
            time.sleep(2)  # Wait for results to update
            
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"Could not apply experience level filters: {str(e)}")
    
    def _apply_date_filter(self, days):
        """Apply date posted filter to search results."""
        try:
            # Determine which date filter to use
            date_value = ""
            if days <= 1:
                date_value = "last"  # Last 24 hours
            elif days <= 3:
                date_value = "3"  # Last 3 days
            elif days <= 7:
                date_value = "7"  # Last 7 days
            elif days <= 14:
                date_value = "14"  # Last 14 days
            else:
                return  # No date filter for longer periods
                
            # Click the "Date posted" filter dropdown
            filter_button = WebDriverWait(self._driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='date-filter']"))
            )
            filter_button.click()
            
            # Select the appropriate date filter
            date_option = self._driver.find_element(By.CSS_SELECTOR, f"input[id*='{date_value}']")
            if not date_option.is_selected():
                # Use JavaScript to click, as the option might be covered by other elements
                self._driver.execute_script("arguments[0].click();", date_option)
            
            # Apply filter
            apply_button = self._driver.find_element(By.CSS_SELECTOR, "button[data-testid='filter-pill-apply']")
            apply_button.click()
            time.sleep(2)  # Wait for results to update
            
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"Could not apply date filter: {str(e)}")