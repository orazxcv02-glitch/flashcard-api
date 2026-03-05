"""
Configuration settings for Flashcard E-Learning Platform API
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

    # PayPal Configuration
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
    PAYPAL_SECRET = os.getenv('PAYPAL_SECRET')
    PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')  # sandbox or live

    # API Settings
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

    # JWT Settings
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '604800'))  # 7 days

    # Security
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # Data URLs (GitHub CDN via jsDelivr)
    DATA_BASE_URL = os.getenv('DATA_BASE_URL', 'https://cdn.jsdelivr.net/gh/orazxcv02-glitch/flashcard-data@courses/')

    # HMAC Secret for data integrity
    DATA_SIGN_SECRET = os.getenv('DATA_SIGN_SECRET', 'flashcard-data-secret-2025')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
