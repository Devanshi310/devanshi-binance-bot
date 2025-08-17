# src/advanced/stop_limit.py
"""
Binance Futures Stop-Limit Order Bot
Usage: python src/advanced/stop_limit.py BTCUSDT BUY 0.01 44000 45000
"""

import argparse
import sys
import os
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from utils import (
    validate_symbol, validate_quantity, validate_side, validate_price,
    log_order, handle_api_error, logger, format_number
)

def get_current_price(client, symbol):
    """Get current market price for a symbol"""
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except Exception as e:
        raise Exception(f"Could not get price for {symbol}: {e}")

def validate_stop_limit_prices(current_price, stop_price, limit_price, side):
    """
    Validate stop-limit price relationships
    Args:
        current_price (float): Current market price
        stop_price (float): Stop trigger price
        limit_price (float): Limit execution price
        side (str): Order side (BUY/SELL)
    Returns:
        bool: True if prices are valid
    """
    if side == 'BUY':
        # For BUY stop-limit: stop_price should be above current price
        # limit_price should be >= stop_price
        if stop_price <= current_price:
            logger.error(f"BUY stop price {stop_price} should be above current price {current_price}")
            return False
        if limit_price < stop_price:
            logger.error(f"BUY limit price {limit_price} should be >= stop price {stop_price}")
            return False
    else:  # SELL
        # For SELL stop-limit: stop_price should be below current price
        # limit_price should be <= stop_price
        if stop_price >= current_price:
            logger.error(f"SELL stop price {stop_price} should be below current price {current_price}")
            return False
        if limit_price > stop_price:
            logger.error(f"SELL limit price {limit_price} should be <= stop price {stop_price}")
            return False
    
    return True

def place_stop_limit_order(symbol, side, quantity, stop_price, limit_price, dry_run=False):
    """
    Place a stop-limit order on Binance Futures
    Args:
        symbol (str): Trading symbol
        side (str): Order side (BUY/SELL)
        quantity (float): Order quantity
        stop_price (float): Price that triggers the limit order
        limit_price (float): Limit price for execution
        dry_run (bool): If True, don't actually place order
    Returns:
        dict: Order response or None if failed
    """
    try:
        # Validate inputs
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        quantity = validate_quantity(quantity)
        stop_price = validate_price(stop_price)
        limit_price = validate_price(limit_price)
        
        # Get Binance client
        client = Config.get_client()
        
        # Get current market price
        current_price = get_current_price(client, symbol)
        logger.info(f"Current price for {symbol}: {current_price}")
        
        # Validate price relationships
        if not validate_stop_limit_prices(current_price, stop_price, limit_price, side):
            raise ValueError("Invalid price relationships for stop-limit order")
        
        # Log order attempt
        log_order("STOP_LIMIT_ORDER_ATTEMPT", symbol, side, quantity, 
                 f"Stop:{stop_price},Limit:{limit_price}")
        
        if dry_run:
            logger.info("DRY RUN: Order would be placed but dry_run=True")
            return {
                'symbol': symbol,
                'orderId': 'DRY_RUN_STOP_LIMIT_123456',
                'status': 'DRY_RUN',
                'origQty': str(quantity),
                'price': str(limit_price),
                'stopPrice': str(stop_price),
                'side': side,
                'type': 'STOP'
            }
        
        # Place the stop-limit order
        order_params = {
            'symbol': symbol,
            'side': side,
            'type': 'STOP',
            'quantity': quantity,
            'price': limit_price,
            'stopPrice': stop_price,
            'timeInForce': 'GTC'
        }
        
        logger.info(f"Placing stop-limit order with params: {order_params}")
        order = client.futures_create_order(**order_params)
        
        # Log successful order
        log_order(
            "STOP_LIMIT_ORDER_SUCCESS", 
            symbol, 
            side, 
            quantity, 
            f"Stop:{stop_price},Limit:{limit_price}",
            order_id=order['orderId'], 
            status=order['status']
        )
        
        # Display results
        print(f"\n✓ Stop-limit order placed successfully!")
        print(f"Order ID: {order['orderId']}")
        print(f"Symbol: {order['symbol']}")
        print(f"Side: {order['side']}")
        print(f"Type: {order['type']}")
        print(f"Quantity: {format_number(order['origQty'])}")
        print(f"Stop Price: {format_number(order['stopPrice'])}")
        print(f"Limit Price: {format_number(order['price'])}")
        print(f"Status: {order['status']}")
        print(f"Current Market Price: {format_number(current_price)}")
        print(f"Time in Force: {order.get('timeInForce', 'GTC')}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Explain the order logic
        if side == 'BUY':
            print(f"\nOrder Logic:")
            print(f"- When price rises to {stop_price}, a limit BUY order will be placed at {limit_price}")
            print(f"- This is typically used to enter a position on an upward breakout")
        else:
            print(f"\nOrder Logic:")
            print(f"- When price falls to {stop_price}, a limit SELL order will be placed at {limit_price}")
            print(f"- This is typically used as a stop-loss to limit losses")
        
        return order
        
    except Exception as e:
        error_msg = handle_api_error(e, "STOP_LIMIT_ORDER")
        log_order("STOP_LIMIT_ORDER_FAILED", symbol, side, quantity, 
                 f"Stop:{stop_price},Limit:{limit_price}", error=error_msg, status="FAILED")
        print(f"\n✗ Error: {error_msg}")
        return None

def main():
    """Main function for CLI interface"""
    parser = argparse.ArgumentParser(
        description='Binance Futures Stop-Limit Order Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # BUY stop-limit (breakout entry)
  python src/advanced/stop_limit.py BTCUSDT BUY 0.01 47000 47500
  
  # SELL stop-limit (stop-loss)
  python src/advanced/stop_limit.py BTCUSDT SELL 0.01 43000 42500
  
  # Dry run test
  python src/advanced/stop_limit.py ETHUSDT BUY 0.1 3300 3350 --dry-run

Note: 
- For BUY: stop_price > current_price, limit_price >= stop_price
- For SELL: stop_price < current_price, limit_price <= stop_price
        """
    )
    
    parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    parser.add_argument('side', choices=['BUY', 'SELL'], help='Order side')
    parser.add_argument('quantity', type=float, help='Order quantity')
    parser.add_argument('stop_price', type=float, help='Stop trigger price')
    parser.add_argument('limit_price', type=float, help='Limit execution price')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Test order without actually placing it')
    
    args = parser.parse_args()
    
    print(f"\n=== Binance Futures Stop-Limit Order Bot ===")
    print(f"Symbol: {args.symbol}")
    print(f"Side: {args.side}")
    print(f"Quantity: {args.quantity}")
    print(f"Stop Price: {args.stop_price}")
    print(f"Limit Price: {args.limit_price}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"===========================================\n")
    
    # Place the order
    result = place_stop_limit_order(
        args.symbol, 
        args.side, 
        args.quantity, 
        args.stop_price, 
        args.limit_price,
        args.dry_run
    )
    
    if result is None:
        print("\nOrder failed. Check the logs for details.")
        sys.exit(1)
    else:
        print(f"\nStop-limit order completed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()