# src/advanced/twap.py
"""
Binance Futures TWAP (Time-Weighted Average Price) Strategy
Usage: python src/advanced/twap.py BTCUSDT BUY 1.0 60 5
"""

import argparse
import sys
import os
import time
import threading
from datetime import datetime, timedelta

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from utils import (
    validate_symbol, validate_quantity, validate_side,
    log_order, handle_api_error, logger, format_number
)

def get_current_price(client, symbol):
    """Get current market price for a symbol"""
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except Exception as e:
        raise Exception(f"Could not get price for {symbol}: {e}")

def calculate_twap_schedule(total_quantity, duration_minutes, num_orders):
    """
    Calculate TWAP execution schedule
    Args:
        total_quantity (float): Total quantity to execute
        duration_minutes (int): Duration in minutes
        num_orders (int): Number of orders to split into
    Returns:
        list: List of (quantity, delay_seconds) tuples
    """
    quantity_per_order = total_quantity / num_orders
    interval_seconds = (duration_minutes * 60) / num_orders
    
    schedule = []
    for i in range(num_orders):
        delay = i * interval_seconds
        schedule.append((quantity_per_order, delay))
    
    return schedule

def execute_twap_order(symbol, side, quantity, delay, client, order_number, total_orders):
    """
    Execute a single TWAP order after delay
    Args:
        symbol (str): Trading symbol
        side (str): Order side
        quantity (float): Order quantity
        delay (float): Delay in seconds before execution
        client: Binance client
        order_number (int): Current order number
        total_orders (int): Total number of orders
    Returns:
        dict: Order result or None
    """
    try:
        if delay > 0:
            logger.info(f"TWAP Order {order_number}/{total_orders}: Waiting {delay:.1f} seconds")
            time.sleep(delay)
        
        # Get current price
        current_price = get_current_price(client, symbol)
        
        # Log order attempt
        log_order(f"TWAP_ORDER_{order_number}_ATTEMPT", symbol, side, quantity, current_price)
        
        # Place market order
        order_params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': quantity,
        }
        
        order = client.futures_create_order(**order_params)
        
        # Log successful order
        log_order(
            f"TWAP_ORDER_{order_number}_SUCCESS", 
            symbol, 
            side, 
            quantity, 
            current_price,
            order_id=order['orderId'], 
            status=order['status']
        )
        
        print(f"✓ TWAP Order {order_number}/{total_orders} executed: {format_number(quantity)} @ {format_number(current_price)}")
        
        return {
            'order': order,
            'price': current_price,
            'timestamp': datetime.now(),
            'order_number': order_number
        }
        
    except Exception as e:
        error_msg = handle_api_error(e, f"TWAP_ORDER_{order_number}")
        log_order(f"TWAP_ORDER_{order_number}_FAILED", symbol, side, quantity, 
                 error=error_msg, status="FAILED")
        print(f"✗ TWAP Order {order_number}/{total_orders} failed: {error_msg}")
        return None

def execute_twap_strategy(symbol, side, total_quantity, duration_minutes, num_orders, dry_run=False):
    """
    Execute TWAP strategy by splitting large order into smaller chunks over time
    Args:
        symbol (str): Trading symbol
        side (str): Order side (BUY/SELL)
        total_quantity (float): Total quantity to execute
        duration_minutes (int): Duration in minutes
        num_orders (int): Number of orders to split into
        dry_run (bool): If True, don't actually place orders
    Returns:
        dict: Strategy results
    """
    try:
        # Validate inputs
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        total_quantity = validate_quantity(total_quantity)
        
        if duration_minutes <= 0:
            raise ValueError("Duration must be positive")
        if num_orders <= 0:
            raise ValueError("Number of orders must be positive")
        if num_orders > total_quantity * 1000:  # Prevent too many tiny orders
            raise ValueError("Too many orders for the given quantity")
        
        # Get Binance client
        client = Config.get_client()
        
        # Calculate execution schedule
        schedule = calculate_twap_schedule(total_quantity, duration_minutes, num_orders)
        
        # Get initial price for reference
        initial_price = get_current_price(client, symbol)
        
        # Log strategy start
        log_order("TWAP_STRATEGY_START", symbol, side, total_quantity, 
                 f"Duration:{duration_minutes}min,Orders:{num_orders}")
        
        print(f"\n📊 TWAP Strategy Configuration:")
        print(f"Total Quantity: {format_number(total_quantity)}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Number of Orders: {num_orders}")
        print(f"Quantity per Order: {format_number(total_quantity / num_orders)}")
        print(f"Interval: {duration_minutes * 60 / num_orders:.1f} seconds")
        print(f"Initial Price: {format_number(initial_price)}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Estimated End Time: {(datetime.now() + timedelta(minutes=duration_minutes)).strftime('%Y-%m-%d %H:%M:%S')}")
        
        if dry_run:
            print(f"\n🧪 DRY RUN MODE - No real orders will be placed")
            for i, (qty, delay) in enumerate(schedule, 1):
                print(f"Order {i}: {format_number(qty)} after {delay:.1f}s")
            return {
                'status': 'DRY_RUN',
                'total_orders': num_orders,
                'total_quantity': total_quantity,
                'schedule': schedule
            }
        
        # Execute orders
        results = []
        successful_orders = 0
        total_executed_quantity = 0.0
        total_cost = 0.0
        
        start_time = datetime.now()
        
        for i, (quantity, delay) in enumerate(schedule, 1):
            result = execute_twap_order(symbol, side, quantity, delay, client, i, num_orders)
            
            if result:
                results.append(result)
                successful_orders += 1
                total_executed_quantity += quantity
                
                # Calculate cost/proceeds
                if side == 'BUY':
                    total_cost += quantity * result['price']
                else:
                    total_cost += quantity * result['price']  # For sells, this is proceeds
            else:
                print(f"⚠️  Order {i} failed - continuing with remaining orders...")
        
        end_time = datetime.now()
        duration_actual = (end_time - start_time).total_seconds() / 60
        
        # Calculate average execution price
        if total_executed_quantity > 0:
            avg_price = total_cost / total_executed_quantity
        else:
            avg_price = 0
        
        # Get final price for comparison
        final_price = get_current_price(client, symbol)
        
        # Log strategy completion
        log_order("TWAP_STRATEGY_COMPLETE", symbol, side, total_executed_quantity,
                 f"AvgPrice:{avg_price},Orders:{successful_orders}/{num_orders}")
        
        # Display final results
        print(f"\n📈 TWAP Strategy Results:")
        print(f"{'='*50}")
        print(f"Successful Orders: {successful_orders}/{num_orders}")
        print(f"Total Executed Quantity: {format_number(total_executed_quantity)}")
        print(f"Average Execution Price: {format_number(avg_price)}")
        print(f"Initial Price: {format_number(initial_price)}")
        print(f"Final Price: {format_number(final_price)}")
        print(f"Price Impact: {((final_price - initial_price) / initial_price * 100):+.3f}%")
        print(f"Execution vs Initial: {((avg_price - initial_price) / initial_price * 100):+.3f}%")
        print(f"Actual Duration: {duration_actual:.1f} minutes")
        print(f"Total Cost/Proceeds: {format_number(total_cost)} USDT")
        print(f"Completion Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            'status': 'COMPLETED',
            'successful_orders': successful_orders,
            'total_orders': num_orders,
            'total_executed_quantity': total_executed_quantity,
            'average_price': avg_price,
            'initial_price': initial_price,
            'final_price': final_price,
            'total_cost': total_cost,
            'duration_minutes': duration_actual,
            'results': results
        }
        
    except Exception as e:
        error_msg = handle_api_error(e, "TWAP_STRATEGY")
        log_order("TWAP_STRATEGY_FAILED", symbol, side, total_quantity,
                 error=error_msg, status="FAILED")
        print(f"\n✗ TWAP Strategy Error: {error_msg}")
        return None

def main():
    """Main function for CLI interface"""
    parser = argparse.ArgumentParser(
        description='Binance Futures TWAP (Time-Weighted Average Price) Strategy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute 1 BTC buy over 60 minutes with 5 orders
  python src/advanced/twap.py BTCUSDT BUY 1.0 60 5
  
  # Execute 10 ETH sell over 30 minutes with 10 orders
  python src/advanced/twap.py ETHUSDT SELL 10.0 30 10
  
  # Test strategy without placing real orders
  python src/advanced/twap.py BTCUSDT BUY 0.5 120 8 --dry-run

Strategy Benefits:
- Reduces market impact for large orders
- Averages out price volatility over time
- Minimizes slippage compared to single large order
        """
    )
    
    parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    parser.add_argument('side', choices=['BUY', 'SELL'], help='Order side')
    parser.add_argument('quantity', type=float, help='Total quantity to execute')
    parser.add_argument('duration', type=int, help='Duration in minutes')
    parser.add_argument('orders', type=int, help='Number of orders to split into')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Test strategy without placing real orders')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.duration <= 0:
        print("Error: Duration must be positive")
        sys.exit(1)
    if args.orders <= 0:
        print("Error: Number of orders must be positive")
        sys.exit(1)
    if args.orders > 100:
        print("Error: Maximum 100 orders allowed")
        sys.exit(1)
    if args.quantity / args.orders < 0.001:
        print("Error: Quantity per order would be too small (< 0.001)")
        sys.exit(1)
    
    print(f"\n=== Binance Futures TWAP Strategy ===")
    print(f"Symbol: {args.symbol}")
    print(f"Side: {args.side}")
    print(f"Total Quantity: {args.quantity}")
    print(f"Duration: {args.duration} minutes")
    print(f"Number of Orders: {args.orders}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"====================================\n")
    
    # Ask for confirmation unless dry run
    if not args.dry_run:
        estimated_end = datetime.now() + timedelta(minutes=args.duration)
        print(f"⚠️  This will execute {args.orders} orders over {args.duration} minutes")
        print(f"   Estimated completion: {estimated_end.strftime('%H:%M:%S')}")
        response = input("   Continue? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Strategy cancelled by user")
            sys.exit(0)
    
    # Execute TWAP strategy
    result = execute_twap_strategy(
        args.symbol,
        args.side,
        args.quantity,
        args.duration,
        args.orders,
        args.dry_run
    )
    
    if result is None:
        print("\nTWAP strategy failed. Check the logs for details.")
        sys.exit(1)
    
    print(f"\nTWAP strategy completed!")
    if result['status'] == 'COMPLETED':
        success_rate = (result['successful_orders'] / result['total_orders']) * 100
        print(f"Success Rate: {success_rate:.1f}%")
    
    sys.exit(0)

if __name__ == "__main__":
    main()