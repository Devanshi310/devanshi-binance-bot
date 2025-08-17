# src/utils.py
import logging
import re
import sys
import traceback
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Configure logging
def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        filename='bot.log',
        format='[%(asctime)s] [%(levelname)s] [%(funcName)s] - %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Also log to console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.addHandler(console_handler)
    
    return logger

# Global logger instance
logger = setup_logging()

def validate_symbol(symbol):
    """
    Validate trading symbol format for USDT-M futures
    Args:
        symbol (str): Trading symbol like BTCUSDT
    Returns:
        str: Validated and uppercase symbol
    Raises:
        ValueError: If symbol format is invalid
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string")
    
    symbol = symbol.upper().strip()
    
    # Check if symbol ends with USDT (for USDT-M futures)
    if not symbol.endswith('USDT'):
        raise ValueError(f"Invalid symbol format: {symbol}. Must end with USDT for futures trading")
    
    # Check if symbol has valid characters
    pattern = r'^[A-Z0-9]+USDT$'
    if not re.match(pattern, symbol):
        raise ValueError(f"Invalid symbol format: {symbol}. Must contain only letters and numbers")
    
    # Check minimum length
    if len(symbol) < 6:  # At least 2 chars + USDT
        raise ValueError(f"Symbol too short: {symbol}")
    
    logger.info(f"Symbol validated: {symbol}")
    return symbol

def validate_quantity(quantity):
    """
    Validate order quantity
    Args:
        quantity: Order quantity (float, int, or string)
    Returns:
        float: Validated quantity
    Raises:
        ValueError: If quantity is invalid
    """
    try:
        qty = float(quantity)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid quantity format: {quantity}. Must be a number")
    
    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got: {qty}")
    
    # Check for reasonable limits
    if qty > 1000000:
        raise ValueError(f"Quantity too large: {qty}. Maximum allowed: 1,000,000")
    
    if qty < 0.001:
        raise ValueError(f"Quantity too small: {qty}. Minimum allowed: 0.001")
    
    logger.info(f"Quantity validated: {qty}")
    return qty

def validate_price(price):
    """
    Validate price value
    Args:
        price: Price value (float, int, or string)
    Returns:
        float: Validated price
    Raises:
        ValueError: If price is invalid
    """
    try:
        p = float(price)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid price format: {price}. Must be a number")
    
    if p <= 0:
        raise ValueError(f"Price must be positive, got: {p}")
    
    # Check for reasonable limits
    if p > 10000000:
        raise ValueError(f"Price too high: {p}. Maximum allowed: 10,000,000")
    
    logger.info(f"Price validated: {p}")
    return p

def validate_side(side):
    """
    Validate order side
    Args:
        side (str): Order side (BUY or SELL)
    Returns:
        str: Validated uppercase side
    Raises:
        ValueError: If side is invalid
    """
    if not side or not isinstance(side, str):
        raise ValueError("Side must be a non-empty string")
    
    side = side.upper().strip()
    
    if side not in ['BUY', 'SELL']:
        raise ValueError(f"Invalid side: {side}. Must be BUY or SELL")
    
    logger.info(f"Side validated: {side}")
    return side

def log_order(action, symbol, side, quantity, price=None, order_id=None, status="PENDING", error=None):
    """
    Structured logging for orders
    Args:
        action (str): Action type (e.g., MARKET_ORDER_ATTEMPT)
        symbol (str): Trading symbol
        side (str): Order side (BUY/SELL)
        quantity (float): Order quantity
        price (float, optional): Order price
        order_id (str, optional): Order ID from exchange
        status (str): Order status
        error (str, optional): Error message if any
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    message = f"Action: {action} | Symbol: {symbol} | Side: {side} | Qty: {quantity}"
    
    if price is not None:
        message += f" | Price: {price}"
    
    if order_id:
        message += f" | OrderID: {order_id}"
    
    message += f" | Status: {status}"
    
    if error:
        message += f" | Error: {error}"
        logger.error(message)
    else:
        logger.info(message)

def handle_api_error(e, action="API_CALL"):
    """
    Handle and log API errors
    Args:
        e (Exception): Exception object
        action (str): Action that caused the error
    Returns:
        str: Formatted error message
    """
    error_msg = str(e)
    
    # Extract meaningful error from Binance API error
    if hasattr(e, 'response'):
        try:
            error_details = e.response.json()
            if 'msg' in error_details:
                error_msg = error_details['msg']
        except:
            pass
    
    full_error = f"{action} failed: {error_msg}"
    
    # Log full stack trace for debugging
    logger.error(f"{full_error}")
    logger.error(f"Stack trace: {traceback.format_exc()}")
    
    return full_error

def format_number(number, decimal_places=8):
    """
    Format number for display
    Args:
        number: Number to format
        decimal_places (int): Number of decimal places
    Returns:
        str: Formatted number
    """
    try:
        return f"{float(number):.{decimal_places}f}".rstrip('0').rstrip('.')
    except:
        return str(number)

def confirm_action(message):
    """
    Ask user for confirmation
    Args:
        message (str): Confirmation message
    Returns:
        bool: True if user confirms, False otherwise
    """
    response = input(f"{message} (y/N): ").strip().lower()
    return response in ['y', 'yes']