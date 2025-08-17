# src/market_orders.py
"""
Binance Futures Market Order Bot
Usage: python src/market_orders.py BTCUSDT BUY 0.01
"""

import argparse
import sys
from datetime import datetime

from config import Config
from utils import (
    validate_symbol, validate_quantity, validate_side,
    log_order, handle_api_error, logger, format_number
)

def get_current_price(client, symbol):
    """
    Get current market price for a symbol
    Args:
        client: Binance client
        symbol (str): Trading symbol
    Returns:
        float: Current price
    """
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except Exception as e:
        raise Exception(f"Could not get price for {symbol}: {e}")

def check_account_balance(client, required_quantity, current_price, side):
    """
    Check if account has sufficient balance
    Args:
        client: Binance client
        required_quantity (float): Required quantity
        current_price (float): Current market price
        side (str): Order side (BUY/SELL)
    Returns:
        bool: True if sufficient balance
    """
    try:
        account = client.futures_account()
        available_balance = float(account['availableBalance'])
        
        if side == 'BUY':
            required_balance = required_quantity * current_price
            if available_balance < required_balance:
                logger.warning(f"Insufficient balance. Required: {required_balance}, Available: {available_balance}")
                return False
        
        # For SELL orders, we should check position size
        # For now, we'll assume sufficient balance
        return True
        
    except Exception as e:
        logger.error(f"Could not check account balance: {e}")
        return False

def place_market_order(symbol, side, quantity, dry_run=False):
    """
    Place a market order on Binance Futures
    Args:
        symbol (str): Trading symbol (e.g., BTCUSDT)
        side (str): Order side (BUY/SELL)
        quantity (float): Order quantity
        dry_run (bool): If True, don't actually place order
    Returns:
        dict: Order response or None if failed
    """
    try:
        # Validate inputs
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        quantity = validate_quantity(quantity)
        
        # Get Binance client
        client = Config.get_client()
        
        # Get current price for logging and balance check
        current_price = get_current_price(client, symbol)
        logger.info(f"Current price for {symbol}: {current_price}")
        
        # Check account balance
        if not check_account_balance(client, quantity, current_price, side):
            raise ValueError("Insufficient account balance")
        
        # Log order attempt
        log_order("MARKET_ORDER_ATTEMPT", symbol, side, quantity, current_price)
        
        if dry_run:
            logger.info("DRY RUN: Order would be placed but dry_run=True")
            return {
                'symbol': symbol,
                'orderId': 'DRY_RUN_123456',
                'status': 'DRY_RUN',
                'executedQty': str(quantity),
                'side': side,
                'type': 'MARKET'
            }
        
        # Place the actual market order
        order_params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': quantity,
        }
        
        logger.info(f"Placing order with params: {order_params}")
        order = client.futures_create_order(**order_params)
        
        # Log successful order
        log_order(
            "MARKET_ORDER_SUCCESS", 
            symbol, 
            side, 
            quantity, 
            current_price,
            order_id=order['orderId'], 
            status=order['status']
        )
        
        # Display results
        print(f"\n✓ Market order placed successfully!")
        print(f"Order ID: {order['orderId']}")
        print(f"Symbol: {order['symbol']}")
        print(f"Side: {order['side']}")
        print(f"Quantity: {format_number(order['origQty'])}")
        print(f"Status: {order['status']}")
        print(f"Executed Quantity: {format_number(order['executedQty'])}")
        print(f"Average Price: {format_number(order.get('avgPrice', current_price))}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return order
        
    except Exception as e:
        error_msg = handle_api_error(e, "MARKET_ORDER")
        log_order("MARKET_ORDER_FAILED", symbol, side, quantity, 
                 error=error_msg, status="FAILED")
        print(f"\n✗ Error: {error_msg}")
        return None

def main():
    """Main function for CLI interface"""
    parser = argparse.ArgumentParser(
        description='Binance Futures Market Order Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/market_orders.py BTCUSDT BUY 0.01
  python src/market_orders.py ETHUSDT SELL 0.1
  python src/market_orders.py ADAUSDT BUY 100 --dry-run
        """
    )
    
    parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    parser.add_argument('side', choices=['BUY', 'SELL'], help='Order side')
    parser.add_argument('quantity', type=float, help='Order quantity')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Test order without actually placing it')
    
    args = parser.parse_args()
    
    print(f"\n=== Binance Futures Market Order Bot ===")
    print(f"Symbol: {args.symbol}")
    print(f"Side: {args.side}")
    print(f"Quantity: {args.quantity}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"========================================\n")
    
    # Place the order
    result = place_market_order(args.symbol, args.side, args.quantity, args.dry_run)
    
    if result is None:
        print("\nOrder failed. Check the logs for details.")
        sys.exit(1)
    else:
        print(f"\nOrder completed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()