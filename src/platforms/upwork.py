"""
Upwork connector for finding freelance opportunities.
This module provides functionality to search for jobs on Upwork.
"""
import time
import logging
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.platforms.base import BaseConnector

logger = logging.getLogger(__name__)

class UpworkConnector(BaseConnector):
    """Connector for searching freelance jobs on Upwork."""
    
    def __init__(self, settings):
        """Initialize the Upwork connector."""
        super().__init__(settings)
        self.base_url = "https://www.upwork.com"
        self.login_url = f"{self.base_url}/ab/account-security/login"
        self.search_url = f"{self.base_url}/nx/jobs/search"
        self._driver = None
    
    def authenticate(self):
        """
        Authenticate with Upwork.
        
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
            
            # Navigate to Upwork login page
            self._driver.get(self.login_url)
            
            # Wait for the page to load
            WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.ID, "login_username"))
            )
            
            # Enter username and click continue
            username_field = self._driver.find_element(By.ID, "login_username")
            username_field.clear()
            username_field.send_keys(self.credentials.get('username', ''))
            continue_button = self._driver.find_element(By.ID, "login_password_continue")
            continue_button.click()
            
            # Wait for password field to appear
            WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.ID, "login_password"))
            )
            
            # Enter password and login
            password_field = self._driver.find_element(By.ID, "login_password")
            password_field.clear()
            password_field.send_keys(self.credentials.get('password', ''))
            login_button = self._driver.find_element(By.ID, "login_control_continue")
            login_button.click()
            
            # Wait for login to complete
            WebDriverWait(self._driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-qa='mainContent']"))
            )
            
            logger.info("Successfully logged in to Upwork")
            return True
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Upwork: {str(e)}")
            if self._driver:
                self._driver.quit()
                self._driver = None
            return False
    
    def search_jobs(self, keywords, locations=None, job_types=None, remote=None, experience_levels=None):
        """
        Search for freelance opportunities on Upwork.
        
        Args:
            keywords (list): List of skills or job titles to search for.
            locations (list, optional): Not used for Upwork (all jobs are remote).
            job_types (list, optional): List of job types (hourly, fixed-price).
            remote (bool, optional): Not used for Upwork (all jobs are remote).
            experience_levels (list, optional): List of experience levels.
            
        Returns:
            list: List of freelance opportunities found on Upwork.
        """
        results = []
        
        try:
            if not self._driver:
                if not self.authenticate():
                    return results
            
            # Process each keyword
            for keyword in keywords:
                logger.info(f"Searching Upwork for '{keyword}'")
                
                # Build search URL with keyword
                search_query = f"{keyword}"
                encoded_query = search_query.replace(' ', '%20')
                current_search_url = f"{self.search_url}/?q={encoded_query}"
                
                # Navigate to search page
                self._driver.get(current_search_url)
                
                # Wait for search results to load
                WebDriverWait(self._driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test='job-tile-list']"))
                )
                
                # Apply filters
                self._apply_filters(job_types, experience_levels)
                
                # Extract job listings
                time.sleep(3)  # Allow dynamic content to load
                page_results = self._extract_job_listings()
                results.extend(page_results)
                
                # Check for pagination, up to a reasonable limit
                max_pages = 3
                current_page = 1
                
                try:
                    while current_page < max_pages:
                        # Check if there's a next page button and it's clickable
                        next_button = None
                        try:
                            next_buttons = self._driver.find_elements(By.CSS_SELECTOR, "button[data-qa='pagination-next']")
                            if next_buttons and next_buttons[0].is_enabled():
                                next_button = next_buttons[0]
                        except (NoSuchElementException, IndexError):
                            break
                            
                        if next_button:
                            # Use JavaScript to scroll to the button to make it visible
                            self._driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                            time.sleep(1)
                            
                            # Click the next page button
                            next_button.click()
                            time.sleep(3)  # Allow page to load
                            
                            # Wait for job listings to load
                            WebDriverWait(self._driver, 15).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test='job-tile-list']"))
                            )
                            
                            page_results = self._extract_job_listings()
                            results.extend(page_results)
                            current_page += 1
                        else:
                            break
                except Exception as e:
                    logger.warning(f"Pagination error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error searching Upwork jobs: {str(e)}")
        
        finally:
            if self._driver:
                self._driver.quit()
                self._driver = None
        
        return results
    
    def get_job_details(self, job_id):
        """
        Get detailed information about a specific Upwork job.
        
        Args:
            job_id (str): Upwork job ID.
            
        Returns:
            dict: Detailed information about the job.
        """
        job_url = f"{self.base_url}/jobs/{job_id}"
        
        try:
            if not self._driver:
                if not self.authenticate():
                    return {}
            
            self._driver.get(job_url)
            
            # Wait for job details to load
            WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test='job-details']"))
            )
            
            # Extract job details
            job_details = {'id': job_id, 'url': job_url}
            
            try:
                # Get job title
                title_element = self._driver.find_element(By.CSS_SELECTOR, "h1[data-qa='job-title']")
                job_details['title'] = title_element.text
                
                # Get job description
                description_element = self._driver.find_element(By.CSS_SELECTOR, "div[data-qa='job-description']")
                job_details['description'] = description_element.text
                
                # Get client info
                try:
                    company_element = self._driver.find_element(By.CSS_SELECTOR, "div[data-qa='client-info'] h2")
                    job_details['company'] = company_element.text
                except NoSuchElementException:
                    job_details['company'] = "Upwork Client"
                
                # Get job type and payment info
                payment_info = {}
                try:
                    payment_elements = self._driver.find_elements(By.CSS_SELECTOR, "div[data-qa='job-insights'] strong")
                    for elem in payment_elements:
                        if '$' in elem.text:  # This is likely the budget/rate
                            payment_info['amount'] = elem.text
                        elif 'hour' in elem.text.lower():  # Hourly rate
                            job_details['job_type'] = 'Hourly'
                        elif 'fixed' in elem.text.lower():  # Fixed price
                            job_details['job_type'] = 'Fixed-Price'
                    
                    if payment_info.get('amount'):
                        job_details['salary'] = payment_info['amount']
                except NoSuchElementException:
                    pass
                
                # Get other job details
                try:
                    detail_elements = self._driver.find_elements(By.CSS_SELECTOR, "li[data-test='attribute-item']")
                    for elem in detail_elements:
                        detail_text = elem.text
                        if "Experience Level:" in detail_text:
                            job_details['experience_level'] = detail_text.replace("Experience Level:", "").strip()
                        elif "Duration:" in detail_text:
                            job_details['duration'] = detail_text.replace("Duration:", "").strip()
                except NoSuchElementException:
                    pass
                
                # Get skills
                try:
                    skill_elements = self._driver.find_elements(By.CSS_SELECTOR, "span[data-qa='skill-tag']")
                    job_details['skills'] = [skill.text for skill in skill_elements]
                except NoSuchElementException:
                    job_details['skills'] = []
                
            except Exception as e:
                logger.debug(f"Could not extract some job details: {str(e)}")
            
            return self._normalize_job_data(job_details)
            
        except Exception as e:
            logger.error(f"Error getting Upwork job details: {str(e)}")
            return {}
        
        finally:
            if self._driver:
                self._driver.quit()
                self._driver = None
    
    def apply_to_job(self, job_id, application_data):
        """
        Apply to a specific job on Upwork.
        
        Args:
            job_id (str): Upwork job ID.
            application_data (dict): Application data including cover letter, proposed rate, etc.
            
        Returns:
            bool: True if application was submitted successfully, False otherwise.
        """
        # NOTE: Implementing a full automated application process for Upwork requires careful handling
        # This is a placeholder implementation for demonstration purposes
        logger.warning("Automated Upwork applications are not implemented")
        return False
    
    def _extract_job_listings(self):
        """
        Extract job listings from the current search results page.
        
        Returns:
            list: List of job data dictionaries.
        """
        job_results = []
        
        try:
            # Wait for job cards to load
            WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "section[data-test='job-tile']"))
            )
            
            # Get all job cards on the page
            job_cards = self._driver.find_elements(By.CSS_SELECTOR, "section[data-test='job-tile']")
            
            for card in job_cards:
                try:
                    # Extract job data from card
                    
                    # Get job title and URL
                    title_element = card.find_element(By.CSS_SELECTOR, "h2[data-test='job-title'] a")
                    job_title = title_element.text.strip()
                    job_url = title_element.get_attribute('href')
                    
                    # Extract job ID from URL
                    job_id = ""
                    try:
                        job_id = re.search(r'~([a-f0-9]+)$', job_url).group(1)
                    except (AttributeError, IndexError):
                        # Try alternate format
                        try:
                            job_id = job_url.split('/')[-1]
                        except:
                            job_id = f"upwork_{time.time()}"
                    
                    # Get job description snippet
                    description = ""
                    try:
                        description_element = card.find_element(By.CSS_SELECTOR, "span[data-test='job-description-text']")
                        description = description_element.text.strip()
                    except NoSuchElementException:
                        pass
                    
                    # Get payment/budget info
                    salary = ""
                    job_type = ""
                    try:
                        payment_element = card.find_element(By.CSS_SELECTOR, "div[data-test='job-type']")
                        payment_text = payment_element.text
                        
                        if "Fixed Price" in payment_text:
                            job_type = "Fixed-Price"
                            budget_match = re.search(r'\$[\d,]+', payment_text)
                            if budget_match:
                                salary = budget_match.group(0)
                        elif "Hourly" in payment_text:
                            job_type = "Hourly"
                            rate_match = re.search(r'\$[\d.]+-\$[\d.]+', payment_text)
                            if rate_match:
                                salary = rate_match.group(0)
                    except NoSuchElementException:
                        pass
                    
                    # Get client info
                    company = "Upwork Client"
                    try:
                        company_elements = card.find_elements(By.CSS_SELECTOR, 
                            "div[data-test='client-info'] small")
                        if company_elements:
                            company_info = []
                            for elem in company_elements:
                                company_info.append(elem.text.strip())
                            company = " - ".join(company_info)
                    except NoSuchElementException:
                        pass
                    
                    # Get skills
                    skills = []
                    try:
                        skill_elements = card.find_elements(By.CSS_SELECTOR, "span[data-test='skill-tag']")
                        skills = [skill.text for skill in skill_elements]
                    except NoSuchElementException:
                        pass
                    
                    # Get posting time
                    date_posted = ""
                    try:
                        date_element = card.find_element(By.CSS_SELECTOR, 
                            "div[data-test='client-info'] span:last-child")
                        date_text = date_element.text
                        
                        # Convert relative date to timestamp
                        today = datetime.now().date()
                        if "Posted" in date_text:
                            date_text = date_text.replace("Posted", "").strip()
                            
                            if "min" in date_text or "hour" in date_text:
                                date_posted = today.isoformat()
                            elif "day" in date_text:
                                days = int(re.search(r'(\d+)', date_text).group(1))
                                date_posted = (today - timedelta(days=days)).isoformat()
                    except (NoSuchElementException, AttributeError):
                        pass
                    
                    # Create job data dictionary
                    job_data = {
                        'id': job_id,
                        'title': job_title,
                        'company': company,
                        'url': job_url,
                        'description': description,
                        'salary': salary,
                        'job_type': job_type,
                        'date_posted': date_posted,
                        'skills': skills,
                        'is_remote': True,  # All Upwork jobs are remote
                    }
                    
                    job_results.append(self._normalize_job_data(job_data))
                    
                except Exception as e:
                    logger.debug(f"Error extracting Upwork job card data: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error extracting Upwork job listings: {str(e)}")
        
        return job_results
    
    def _apply_filters(self, job_types, experience_levels):
        """Apply filters to job search results."""
        try:
            # First, click to open filters section if needed
            try:
                filter_button = WebDriverWait(self._driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-qa='filter-button']"))
                )
                filter_button.click()
                time.sleep(1)
            except (TimeoutException, NoSuchElementException):
                # Filters might already be visible
                pass
            
            # Apply job type filters
            if job_types:
                hourly = any("hour" in jt.lower() for jt in job_types)
                fixed = any("fix" in jt.lower() or "contract" in jt.lower() for jt in job_types)
                
                try:
                    if hourly or fixed:
                        # Open job type dropdown
                        job_type_button = WebDriverWait(self._driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test='dropdown-toggle-payment-type']"))
                        )
                        job_type_button.click()
                        time.sleep(1)
                        
                        # Select appropriate checkboxes
                        if hourly:
                            hourly_checkbox = self._driver.find_element(By.CSS_SELECTOR, 
                                "input[id*='hourly']")
                            if not hourly_checkbox.is_selected():
                                self._driver.execute_script("arguments[0].click();", hourly_checkbox)
                        
                        if fixed:
                            fixed_checkbox = self._driver.find_element(By.CSS_SELECTOR, 
                                "input[id*='fixed']")
                            if not fixed_checkbox.is_selected():
                                self._driver.execute_script("arguments[0].click();", fixed_checkbox)
                        
                        # Apply button
                        apply_button = self._driver.find_element(By.CSS_SELECTOR, 
                            "button[data-test='dropdown-apply']")
                        apply_button.click()
                        time.sleep(2)
                except (TimeoutException, NoSuchElementException) as e:
                    logger.warning(f"Could not apply job type filters: {str(e)}")
            
            # Apply experience level filters
            if experience_levels:
                try:
                    # Map our experience levels to Upwork's values
                    upwork_exp_levels = []
                    for level in experience_levels:
                        level_lower = level.lower()
                        if "entry" in level_lower or "junior" in level_lower:
                            upwork_exp_levels.append("ENTRY")
                        elif "mid" in level_lower or "intermediate" in level_lower:
                            upwork_exp_levels.append("INTERMEDIATE")
                        elif "senior" in level_lower or "expert" in level_lower:
                            upwork_exp_levels.append("EXPERT")
                    
                    if upwork_exp_levels:
                        # Open experience level dropdown
                        exp_button = WebDriverWait(self._driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test='dropdown-toggle-experience']"))
                        )
                        exp_button.click()
                        time.sleep(1)
                        
                        # Select appropriate checkboxes
                        for exp_level in upwork_exp_levels:
                            exp_checkbox = self._driver.find_element(By.CSS_SELECTOR, 
                                f"input[id*='{exp_level.lower()}']")
                            if not exp_checkbox.is_selected():
                                self._driver.execute_script("arguments[0].click();", exp_checkbox)
                        
                        # Apply button
                        apply_button = self._driver.find_element(By.CSS_SELECTOR, 
                            "button[data-test='dropdown-apply']")
                        apply_button.click()
                        time.sleep(2)
                except (TimeoutException, NoSuchElementException) as e:
                    logger.warning(f"Could not apply experience level filters: {str(e)}")
            
            # Apply hourly rate filter if specified in settings
            hourly_rate = self.search_criteria.get('hourly_rate', {})
            min_rate = hourly_rate.get('min')
            max_rate = hourly_rate.get('max')
            
            if min_rate or max_rate:
                try:
                    # Open hourly rate dropdown
                    rate_button = WebDriverWait(self._driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test='dropdown-toggle-hourly-rate']"))
                    )
                    rate_button.click()
                    time.sleep(1)
                    
                    # Set min rate if provided
                    if min_rate:
                        min_input = self._driver.find_element(By.CSS_SELECTOR, 
                            "input[data-test='min-rate']")
                        min_input.clear()
                        min_input.send_keys(str(min_rate))
                    
                    # Set max rate if provided
                    if max_rate:
                        max_input = self._driver.find_element(By.CSS_SELECTOR, 
                            "input[data-test='max-rate']")
                        max_input.clear()
                        max_input.send_keys(str(max_rate))
                    
                    # Apply button
                    apply_button = self._driver.find_element(By.CSS_SELECTOR, 
                        "button[data-test='dropdown-apply']")
                    apply_button.click()
                    time.sleep(2)
                except (TimeoutException, NoSuchElementException) as e:
                    logger.warning(f"Could not apply hourly rate filter: {str(e)}")
            
            # Allow time for filters to apply and results to load
            time.sleep(3)
            
        except Exception as e:
            logger.warning(f"Error applying filters: {str(e)}")