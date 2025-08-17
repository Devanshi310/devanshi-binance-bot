import os
from dotenv import load_dotenv
from binance import Client

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for Binance trading bot"""
    
    # API Credentials
    API_KEY = os.getenv('BINANCE_API_KEY')
    SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
    USE_TESTNET = os.getenv('USE_TESTNET', 'True').lower() == 'true'
    
    # Trading Configuration
    DEFAULT_QUANTITY = 0.01
    MAX_RETRY_ATTEMPTS = 3
    
    @classmethod
    def get_client(cls):
        """Get configured Binance client"""
        if not cls.API_KEY or not cls.SECRET_KEY:
            raise ValueError("API credentials not found. Please check your .env file")
        
        if cls.USE_TESTNET:
            return Client(cls.API_KEY, cls.SECRET_KEY, testnet=True)
        else:
            return Client(cls.API_KEY, cls.SECRET_KEY)
    
    @classmethod
    def validate_config(cls):
        """Validate configuration settings"""
        if not cls.API_KEY:
            raise ValueError("BINANCE_API_KEY not found in environment variables")
        if not cls.SECRET_KEY:
            raise ValueError("BINANCE_SECRET_KEY not found in environment variables")
        
        print(f"Configuration loaded successfully")
        print(f"Using testnet: {cls.USE_TESTNET}")
        return True