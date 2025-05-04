"""
Fiverr connector for finding freelance opportunities.
This module provides functionality to search for jobs on Fiverr.
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

class FiverrConnector(BaseConnector):
    """Connector for searching freelance opportunities on Fiverr."""
    
    def __init__(self, settings):
        """Initialize the Fiverr connector."""
        super().__init__(settings)
        self.base_url = "https://www.fiverr.com"
        self.login_url = f"{self.base_url}/login"
        self.search_url = f"{self.base_url}/search/gigs"
        self._driver = None
    
    def authenticate(self):
        """
        Authenticate with Fiverr.
        
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
            
            # Navigate to Fiverr login page
            self._driver.get(self.login_url)
            
            # Wait for the page to load
            WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.ID, "login"))
            )
            
            # Enter username/email
            username_field = self._driver.find_element(By.ID, "login")
            username_field.clear()
            username_field.send_keys(self.credentials.get('username', ''))
            
            # Enter password
            password_field = self._driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(self.credentials.get('password', ''))
            
            # Submit login form
            submit_button = self._driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            # Wait for login to complete
            WebDriverWait(self._driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "header.header"))
            )
            
            logger.info("Successfully logged in to Fiverr")
            return True
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Fiverr: {str(e)}")
            if self._driver:
                self._driver.quit()
                self._driver = None
            return False
    
    def search_jobs(self, keywords, locations=None, job_types=None, remote=None, experience_levels=None):
        """
        Search for freelance opportunities on Fiverr.
        Note: Since Fiverr is primarily for offering services rather than finding jobs,
        this method searches for relevant buyer requests that match the user's skills.
        
        Args:
            keywords (list): List of skills or job titles to search for.
            locations (list, optional): Not used for Fiverr.
            job_types (list, optional): Not used for Fiverr.
            remote (bool, optional): Not used for Fiverr.
            experience_levels (list, optional): Not used for Fiverr.
            
        Returns:
            list: List of freelance opportunities found on Fiverr.
        """
        results = []
        
        try:
            if not self._driver:
                if not self.authenticate():
                    return results
            
            # Navigate to buyer requests page (requires login)
            buyer_requests_url = f"{self.base_url}/sellers/buyer-requests"
            self._driver.get(buyer_requests_url)
            
            # Wait for page to load
            try:
                WebDriverWait(self._driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.js-buyer-requests-table"))
                )
            except TimeoutException:
                logger.warning("Could not access buyer requests. Make sure the account has seller status on Fiverr.")
                
                # As fallback, search public gigs for competitors analysis
                for keyword in keywords:
                    search_url = f"{self.search_url}?query={keyword}"
                    logger.info(f"Searching Fiverr public gigs for '{keyword}'")
                    self._driver.get(search_url)
                    
                    # Wait for search results
                    try:
                        WebDriverWait(self._driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.gig-card"))
                        )
                        
                        # Extract market insights from gigs
                        time.sleep(2)
                        market_insights = self._extract_market_insights()
                        if market_insights:
                            results.extend(market_insights)
                    except TimeoutException:
                        logger.warning(f"No public gigs found for '{keyword}'")
                        
                return results
            
            # Extract buyer requests that match keywords
            time.sleep(2)  # Allow table to load completely
            
            for keyword in keywords:
                logger.info(f"Searching Fiverr buyer requests for '{keyword}'")
                requests = self._extract_buyer_requests(keyword)
                if requests:
                    results.extend(requests)
                    
            logger.info(f"Found {len(results)} buyer requests matching your skills")
                
        except Exception as e:
            logger.error(f"Error searching Fiverr opportunities: {str(e)}")
        
        finally:
            if self._driver:
                self._driver.quit()
                self._driver = None
        
        return results
    
    def get_job_details(self, job_id):
        """
        Get detailed information about a specific buyer request.
        
        Args:
            job_id (str): Fiverr buyer request ID.
            
        Returns:
            dict: Detailed information about the request.
        """
        # Note: This is a stub implementation since Fiverr doesn't have a direct URL
        # to access individual buyer requests without context
        logger.warning("Detailed buyer request view not implemented for Fiverr")
        return {}
    
    def apply_to_job(self, job_id, application_data):
        """
        Apply to a specific buyer request on Fiverr.
        
        Args:
            job_id (str): Fiverr buyer request ID.
            application_data (dict): Application data including offer details.
            
        Returns:
            bool: True if application was submitted successfully, False otherwise.
        """
        # NOTE: Implementing automated applications on Fiverr requires careful handling
        logger.warning("Automated Fiverr applications are not implemented")
        return False
    
    def _extract_buyer_requests(self, keyword):
        """
        Extract buyer requests that match the given keyword.
        
        Args:
            keyword (str): Keyword to match against requests.
            
        Returns:
            list: List of matching buyer requests.
        """
        requests = []
        keyword_lower = keyword.lower()
        
        try:
            # Find all request rows in the table
            request_rows = self._driver.find_elements(By.CSS_SELECTOR, "div.buyer-request-row")
            
            for row in request_rows:
                try:
                    # Get request description
                    description_elem = row.find_element(By.CSS_SELECTOR, "div.description")
                    description = description_elem.text
                    
                    # Check if keyword is in description
                    if keyword_lower not in description.lower():
                        continue
                    
                    # Get buyer name
                    buyer_elem = row.find_element(By.CSS_SELECTOR, "div.request-from a")
                    buyer = buyer_elem.text
                    
                    # Get delivery time and budget if available
                    delivery_time = ""
                    budget = ""
                    try:
                        delivery_elem = row.find_element(By.CSS_SELECTOR, "div.delivery-time")
                        delivery_time = delivery_elem.text
                        
                        budget_elem = row.find_element(By.CSS_SELECTOR, "div.price")
                        budget = budget_elem.text
                    except NoSuchElementException:
                        pass
                    
                    # Create a unique ID for the request
                    request_id = f"fiverr_request_{int(time.time())}_{len(requests)}"
                    
                    # Create normalized job data
                    job_data = {
                        'id': request_id,
                        'title': f"Buyer Request: {description[:50]}...",
                        'company': f"Fiverr Buyer: {buyer}",
                        'description': description,
                        'salary': budget,
                        'date_posted': datetime.now().strftime("%Y-%m-%d"),
                        'job_type': 'Freelance',
                        'platform': 'Fiverr',
                        'url': f"{self.base_url}/sellers/buyer-requests",
                        'is_remote': True
                    }
                    
                    # Add delivery time as additional field
                    if delivery_time:
                        job_data['duration'] = delivery_time
                    
                    requests.append(self._normalize_job_data(job_data))
                    
                except Exception as e:
                    logger.debug(f"Error extracting buyer request: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error extracting buyer requests: {str(e)}")
        
        return requests
    
    def _extract_market_insights(self):
        """
        Extract market insights from public gigs as a fallback.
        This is useful for understanding market demand and competitor offerings.
        
        Returns:
            list: List of market insights presented as job opportunities.
        """
        insights = []
        
        try:
            # Find all gig cards
            gig_cards = self._driver.find_elements(By.CSS_SELECTOR, "div.gig-card")
            
            for idx, card in enumerate(gig_cards[:10]):  # Limit to first 10 for analysis
                try:
                    # Get gig title
                    title_elem = card.find_element(By.CSS_SELECTOR, "h3")
                    title = title_elem.text
                    
                    # Get seller name
                    seller_elem = card.find_element(By.CSS_SELECTOR, "div.seller-name")
                    seller = seller_elem.text
                    
                    # Get price
                    price = ""
                    try:
                        price_elem = card.find_element(By.CSS_SELECTOR, "span.price")
                        price = price_elem.text
                    except NoSuchElementException:
                        pass
                    
                    # Get rating if available
                    rating = ""
                    try:
                        rating_elem = card.find_element(By.CSS_SELECTOR, "span.gig-rating")
                        rating = rating_elem.text
                    except NoSuchElementException:
                        pass
                    
                    # Create a unique ID for the insight
                    insight_id = f"fiverr_insight_{int(time.time())}_{idx}"
                    
                    # Create insight data formatted like a job opportunity
                    insight_data = {
                        'id': insight_id,
                        'title': f"Market Opportunity: {title}",
                        'company': "Fiverr Market Analysis",
                        'description': f"Market insight based on competitor offering: '{title}' by {seller}. " +
                                       f"This service is priced at {price} with a rating of {rating}. " +
                                       f"Consider offering similar services to tap into this market demand.",
                        'salary': f"Competitor price: {price}",
                        'date_posted': datetime.now().strftime("%Y-%m-%d"),
                        'job_type': 'Market Insight',
                        'platform': 'Fiverr',
                        'url': self._driver.current_url,
                        'is_remote': True
                    }
                    
                    insights.append(self._normalize_job_data(insight_data))
                    
                except Exception as e:
                    logger.debug(f"Error extracting market insight: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error extracting market insights: {str(e)}")
        
        return insights