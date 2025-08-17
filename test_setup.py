# test_setup.py
from src.config import Config
from src.utils import validate_symbol, validate_quantity, logger

def test_setup():
    print("Testing project setup...")
    
    # Test configuration
    try:
        Config.validate_config()
        print("✓ Configuration loaded successfully")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False
    
    # Test Binance client
    try:
        client = Config.get_client()
        account_info = client.futures_account()
        print("✓ Binance connection successful")
        print(f"✓ Account balance: {account_info['totalWalletBalance']} USDT")
    except Exception as e:
        print(f"✗ Binance connection failed: {e}")
        return False
    
    # Test validation functions
    try:
        validate_symbol("BTCUSDT")
        validate_quantity(0.01)
        print("✓ Validation functions working")
    except Exception as e:
        print(f"✗ Validation error: {e}")
        return False
    
    print("✓ All tests passed! Setup is complete.")
    return True

if __name__ == "__main__":
    test_setup()