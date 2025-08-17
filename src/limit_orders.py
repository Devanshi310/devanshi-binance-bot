# src/limit_orders.py
"""
Binance Futures Limit Order Bot
Usage: python src/limit_orders.py BTCUSDT BUY 0.01 45000
"""

import argparse
import sys
import time
from datetime import datetime

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

def validate_limit_price(current_price, limit_price, side):
    """
    Validate limit price makes sense compared to current market price
    Args:
        current_price (float): Current market price
        limit_price (float): Proposed limit price
        side (str): Order side (BUY/SELL)
    Returns:
        bool: True if price is reasonable
    """
    price_diff_percent = abs((limit_price - current_price) / current_price) * 100
    
    # Warn if price is too far from market
    if price_diff_percent > 50:
        logger.warning(f"Limit price {limit_price} is {price_diff_percent:.1f}% away from market price {current_price}")
        return False
    
    # Check if limit price makes sense for the side
    if side == 'BUY' and limit_price > current_price * 1.1:
        logger.warning(f"BUY limit price {limit_price} is significantly above market price {current_price}")
    elif side == 'SELL' and limit_price < current_price * 0.9:
        logger.warning(f"SELL limit price {limit_price} is significantly below market price {current_price}")
    
    return True

def place_limit_order(symbol, side, quantity, price, dry_run=False):
    """
    Place a limit order on Binance Futures
    Args:
        symbol (str): Trading symbol (e.g., BTCUSDT)
        side (str): Order side (BUY/SELL)
        quantity (float): Order quantity
        price (float): Limit price
        dry_run (bool): If True, don't actually place order
    Returns:
        dict: Order response or None if failed
    """
    try:
        # Validate inputs
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        quantity = validate_quantity(quantity)
        price = validate_price(price)
        
        # Get Binance client
        client = Config.get_client()
        
        # Get current market price for validation
        current_price = get_current_price(client, symbol)
        logger.info(f"Current price for {symbol}: {current_price}")
        
        # Validate limit price makes sense
        if not validate_limit_price(current_price, price, side):
            print(f"Warning: Limit price {price} may not be optimal compared to market price {current_price}")
            response = input("Continue anyway? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Order cancelled by user")
                return None
        
        # Log order attempt
        log_order("LIMIT_ORDER_ATTEMPT", symbol, side, quantity, price)
        
        if dry_run:
            logger.info("DRY RUN: Order would be placed but dry_run=True")
            return {
                'symbol': symbol,
                'orderId': 'DRY_RUN_LIMIT_123456',
                'status': 'DRY_RUN',
                'origQty': str(quantity),
                'price': str(price),
                'side': side,
                'type': 'LIMIT'
            }
        
        # Place the actual limit order
        order_params = {
            'symbol': symbol,
            'side': side,
            'type': 'LIMIT',
            'quantity': quantity,
            'price': price,
            'timeInForce': 'GTC'  # Good Till Cancel
        }
        
        logger.info(f"Placing limit order with params: {order_params}")
        order = client.futures_create_order(**order_params)
        
        # Log successful order
        log_order(
            "LIMIT_ORDER_SUCCESS", 
            symbol, 
            side, 
            quantity, 
            price,
            order_id=order['orderId'], 
            status=order['status']
        )
        
        # Display results
        print(f"\n✓ Limit order placed successfully!")
        print(f"Order ID: {order['orderId']}")
        print(f"Symbol: {order['symbol']}")
        print(f"Side: {order['side']}")
        print(f"Type: {order['type']}")
        print(f"Quantity: {format_number(order['origQty'])}")
        print(f"Limit Price: {format_number(order['price'])}")
        print(f"Status: {order['status']}")
        print(f"Time in Force: {order.get('timeInForce', 'GTC')}")
        print(f"Current Market Price: {format_number(current_price)}")
        print(f"Price Difference: {((float(order['price']) - current_price) / current_price * 100):+.2f}%")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return order
        
    except Exception as e:
        error_msg = handle_api_error(e, "LIMIT_ORDER")
        log_order("LIMIT_ORDER_FAILED", symbol, side, quantity, price,
                 error=error_msg, status="FAILED")
        print(f"\n✗ Error: {error_msg}")
        return None

def check_order_status(order_id, symbol, max_checks=5):
    """
    Check the status of a placed order
    Args:
        order_id (str): Order ID to check
        symbol (str): Trading symbol
        max_checks (int): Maximum number of status checks
    """
    try:
        client = Config.get_client()
        
        for i in range(max_checks):
            order_status = client.futures_get_order(symbol=symbol, orderId=order_id)
            
            print(f"\nOrder Status Check #{i+1}:")
            print(f"Status: {order_status['status']}")
            print(f"Executed Quantity: {format_number(order_status['executedQty'])}")
            print(f"Remaining Quantity: {format_number(float(order_status['origQty']) - float(order_status['executedQty']))}")
            
            if order_status['status'] in ['FILLED', 'CANCELED', 'EXPIRED']:
                break
            
            if i < max_checks - 1:
                print("Order still open, checking again in 10 seconds...")
                time.sleep(10)
        
        return order_status
        
    except Exception as e:
        error_msg = handle_api_error(e, "ORDER_STATUS_CHECK")
        print(f"Could not check order status: {error_msg}")
        return None

def main():
    """Main function for CLI interface"""
    parser = argparse.ArgumentParser(
        description='Binance Futures Limit Order Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/limit_orders.py BTCUSDT BUY 0.01 45000
  python src/limit_orders.py ETHUSDT SELL 0.1 3200
  python src/limit_orders.py ADAUSDT BUY 100 0.45 --dry-run
  python src/limit_orders.py BTCUSDT BUY 0.01 45000 --check-status
        """
    )
    
    parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    parser.add_argument('side', choices=['BUY', 'SELL'], help='Order side')
    parser.add_argument('quantity', type=float, help='Order quantity')
    parser.add_argument('price', type=float, help='Limit price')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Test order without actually placing it')
    parser.add_argument('--check-status', action='store_true',
                       help='Monitor order status after placement')
    
    args = parser.parse_args()
    
    print(f"\n=== Binance Futures Limit Order Bot ===")
    print(f"Symbol: {args.symbol}")
    print(f"Side: {args.side}")
    print(f"Quantity: {args.quantity}")
    print(f"Limit Price: {args.price}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Check Status: {args.check_status}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=========================================\n")
    
    # Place the order
    result = place_limit_order(args.symbol, args.side, args.quantity, args.price, args.dry_run)
    
    if result is None:
        print("\nOrder failed. Check the logs for details.")
        sys.exit(1)
    
    # Check order status if requested and not dry run
    if args.check_status and not args.dry_run and result.get('orderId'):
        print(f"\nMonitoring order status...")
        final_status = check_order_status(result['orderId'], args.symbol)
        
        if final_status:
            print(f"\nFinal Order Status: {final_status['status']}")
    
    print(f"\nOrder completed successfully!")
    sys.exit(0)

if __name__ == "__main__":
    main()