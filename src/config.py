"""
Configuration loader for the job search agent.
Handles loading and validating user preferences.
"""
import os
import yaml
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")

def load_config(config_path=None):
    """
    Load configuration from YAML file.
    
    Args:
        config_path (str, optional): Path to the configuration file.
        
    Returns:
        dict: Configuration dictionary or None if loading fails.
    """
    if not config_path:
        config_path = DEFAULT_CONFIG_PATH
    
    try:
        if not os.path.exists(config_path):
            create_default_config(config_path)
            logger.info(f"Created default configuration file at {config_path}")
            
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            
        validate_config(config)
        return config
    
    except Exception as e:
        logger.error(f"Failed to load configuration from {config_path}: {str(e)}")
        return None

def validate_config(config):
    """
    Validate the configuration to ensure all required fields are present.
    
    Args:
        config (dict): Configuration dictionary to validate.
        
    Raises:
        ValueError: If configuration is invalid.
    """
    required_fields = [
        'user_profile', 
        'job_search',
        'platforms'
    ]
    
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required configuration field: {field}")
    
    # Validate user profile
    user_profile = config['user_profile']
    if not all(key in user_profile for key in ['name', 'skills', 'experience', 'resume_path']):
        raise ValueError("User profile is incomplete. Required: name, skills, experience, resume_path")
    
    # Validate job search parameters
    job_search = config['job_search']
    if not all(key in job_search for key in ['job_types', 'locations', 'keywords']):
        raise ValueError("Job search parameters are incomplete. Required: job_types, locations, keywords")
    
    # Validate platforms configurations
    platforms = config['platforms']
    for platform, settings in platforms.items():
        if settings.get('enabled', False) and not settings.get('credentials'):
            logger.warning(f"Platform {platform} is enabled but credentials are missing.")

def create_default_config(config_path):
    """
    Create a default configuration file if none exists.
    
    Args:
        config_path (str): Path where the config file should be created.
    """
    default_config = {
        'user_profile': {
            'name': 'Your Name',
            'title': 'Your Professional Title',
            'email': 'your.email@example.com',
            'phone': '+1234567890',
            'location': 'City, Country',
            'experience': '5 years',
            'education': [
                {
                    'degree': 'Bachelor of Science',
                    'field': 'Computer Science',
                    'institution': 'University Name',
                    'year': 2020
                }
            ],
            'skills': [
                'Python', 'Data Analysis', 'Machine Learning',
                'Web Development', 'Project Management'
            ],
            'resume_path': 'path/to/your/resume.pdf',
            'portfolio_url': 'https://yourportfolio.com',
            'github_url': 'https://github.com/yourusername',
            'linkedin_url': 'https://linkedin.com/in/yourusername'
        },
        'job_search': {
            'job_types': ['Full-time', 'Contract', 'Freelance'],
            'experience_level': ['Mid-level', 'Senior'],
            'remote': True,
            'locations': ['New York, NY', 'Remote'],
            'salary_range': {
                'min': 80000,
                'max': 150000,
                'currency': 'USD'
            },
            'keywords': [
                'Python Developer',
                'Data Scientist',
                'Full Stack Developer'
            ],
            'exclude_keywords': [
                'PHP', 'WordPress'
            ]
        },
        'platforms': {
            'linkedin': {
                'enabled': True,
                'credentials': {
                    'username': 'your_username',
                    'password': 'your_password'
                },
                'search_criteria': {
                    'post_days': 7,
                    'location_distance': 25
                }
            },
            'indeed': {
                'enabled': True,
                'credentials': {},  # No login required
                'search_criteria': {
                    'post_days': 14,
                    'location_distance': 50
                }
            },
            'upwork': {
                'enabled': True,
                'credentials': {
                    'username': 'your_username',
                    'password': 'your_password'
                },
                'search_criteria': {
                    'hourly_rate': {
                        'min': 40,
                        'max': 100
                    }
                }
            }
        },
        'application': {
            'auto_apply': False,  # Set to True for automatic applications
            'cover_letter_template': 'templates/cover_letter.jinja',
            'daily_application_limit': 10
        },
        'notifications': {
            'email': {
                'enabled': True,
                'address': 'your.email@example.com'
            },
            'desktop': {
                'enabled': True
            }
        },
        'scheduler': {
            'enabled': True,
            'frequency': 'daily',  # 'daily', 'hourly', 'weekly'
            'time': '09:00'  # When to run the job search
        }
    }
    
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as file:
        yaml.dump(default_config, file, default_flow_style=False, sort_keys=False)