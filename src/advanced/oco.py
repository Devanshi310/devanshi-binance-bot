# src/advanced/oco.py
"""
Binance Futures OCO (One-Cancels-Other) Order Bot
Usage: python src/advanced/oco.py BTCUSDT SELL 0.01 46000 44000
"""

import argparse
import sys
import os
import time
import threading
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

def validate_oco_prices(current_price, take_profit_price, stop_loss_price, side):
    """
    Validate OCO price relationships
    Args:
        current_price (float): Current market price
        take_profit_price (float): Take profit target price
        stop_loss_price (float): Stop loss price
        side (str): Original position side (BUY/SELL)
    Returns:
        bool: True if prices are valid
    """
    if side == 'SELL':  # Closing a long position
        # Take profit should be above current price
        # Stop loss should be below current price
        if take_profit_price <= current_price:
            logger.error(f"Take profit {take_profit_price} should be above current price {current_price}")
            return False
        if stop_loss_price >= current_price:
            logger.error(f"Stop loss {stop_loss_price} should be below current price {current_price}")
            return False
    else:  # BUY - Closing a short position
        # Take profit should be below current price
        # Stop loss should be above current price
        if take_profit_price >= current_price:
            logger.error(f"Take profit {take_profit_price} should be below current price {current_price}")
            return False
        if stop_loss_price <= current_price:
            logger.error(f"Stop loss {stop_loss_price} should be above current price {current_price}")
            return False
    
    return True

def monitor_orders(client, symbol, tp_order_id, sl_order_id, monitoring_duration=3600):
    """
    Monitor OCO orders and cancel the other when one executes
    Args:
        client: Binance client
        symbol (str): Trading symbol
        tp_order_id (str): Take profit order ID
        sl_order_id (str): Stop loss order ID
        monitoring_duration (int): How long to monitor in seconds
    """
    start_time = time.time()
    logger.info(f"Starting OCO order monitoring for {monitoring_duration} seconds")
    
    try:
        while time.time() - start_time < monitoring_duration:
            # Check take profit order status
            tp_status = client.futures_get_order(symbol=symbol, orderId=tp_order_id)
            sl_status = client.futures_get_order(symbol=symbol, orderId=sl_order_id)
            
            # If take profit is filled, cancel stop loss
            if tp_status['status'] == 'FILLED':
                logger.info(f"Take profit order {tp_order_id} filled, cancelling stop loss {sl_order_id}")
                try:
                    client.futures_cancel_order(symbol=symbol, orderId=sl_order_id)
                    log_order("OCO_TAKE_PROFIT_EXECUTED", symbol, "CANCEL", 0, 
                             order_id=f"TP:{tp_order_id},SL_CANCELLED:{sl_order_id}")
                    print(f"✓ Take profit executed! Stop loss cancelled.")
                except:
                    logger.warning(f"Could not cancel stop loss order {sl_order_id} - may already be cancelled")
                break
            
            # If stop loss is filled, cancel take profit
            if sl_status['status'] == 'FILLED':
                logger.info(f"Stop loss order {sl_order_id} filled, cancelling take profit {tp_order_id}")
                try:
                    client.futures_cancel_order(symbol=symbol, orderId=tp_order_id)
                    log_order("OCO_STOP_LOSS_EXECUTED", symbol, "CANCEL", 0,
                             order_id=f"SL:{sl_order_id},TP_CANCELLED:{tp_order_id}")
                    print(f"✓ Stop loss executed! Take profit cancelled.")
                except:
                    logger.warning(f"Could not cancel take profit order {tp_order_id} - may already be cancelled")
                break
            
            # Check if either order was cancelled externally
            if tp_status['status'] in ['CANCELED', 'EXPIRED'] or sl_status['status'] in ['CANCELED', 'EXPIRED']:
                logger.info(f"One or both OCO orders were cancelled externally")
                break
            
            # Sleep before next check
            time.sleep(10)
        
        logger.info("OCO monitoring completed")
        
    except Exception as e:
        logger.error(f"Error during OCO monitoring: {e}")

def place_oco_order(symbol, side, quantity, take_profit_price, stop_loss_price, dry_run=False):
    """
    Place OCO (One-Cancels-Other) orders
    Args:
        symbol (str): Trading symbol
        side (str): Side to close position (BUY to close short, SELL to close long)
        quantity (float): Order quantity
        take_profit_price (float): Take profit target price
        stop_loss_price (float): Stop loss price
        dry_run (bool): If True, don't actually place orders
    Returns:
        dict: Order response or None if failed
    """
    try:
        # Validate inputs
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        quantity = validate_quantity(quantity)
        take_profit_price = validate_price(take_profit_price)
        stop_loss_price = validate_price(stop_loss_price)
        
        # Get Binance client
        client = Config.get_client()
        
        # Get current market price
        current_price = get_current_price(client, symbol)
        logger.info(f"Current price for {symbol}: {current_price}")
        
        # Validate price relationships
        if not validate_oco_prices(current_price, take_profit_price, stop_loss_price, side):
            raise ValueError("Invalid price relationships for OCO order")
        
        # Log order attempt
        log_order("OCO_ORDER_ATTEMPT", symbol, side, quantity, 
                 f"TP:{take_profit_price},SL:{stop_loss_price}")
        
        if dry_run:
            logger.info("DRY RUN: Orders would be placed but dry_run=True")
            return {
                'symbol': symbol,
                'take_profit': {'orderId': 'DRY_RUN_TP_123456', 'status': 'DRY_RUN'},
                'stop_loss': {'orderId': 'DRY_RUN_SL_123456', 'status': 'DRY_RUN'},
                'side': side,
                'type': 'OCO'
            }
        
        # Place take profit limit order
        tp_order_params = {
            'symbol': symbol,
            'side': side,
            'type': 'LIMIT',
            'quantity': quantity,
            'price': take_profit_price,
            'timeInForce': 'GTC'
        }
        
        logger.info(f"Placing take profit order: {tp_order_params}")
        tp_order = client.futures_create_order(**tp_order_params)
        
        # Place stop loss order
        # Determine stop loss order type based on side
        if side == 'SELL':
            # For closing long position, use STOP_MARKET
            sl_order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'STOP_MARKET',
                'quantity': quantity,
                'stopPrice': stop_loss_price
            }
        else:
            # For closing short position, use STOP_MARKET
            sl_order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'STOP_MARKET',
                'quantity': quantity,
                'stopPrice': stop_loss_price
            }
        
        logger.info(f"Placing stop loss order: {sl_order_params}")
        sl_order = client.futures_create_order(**sl_order_params)
        
        # Log successful orders
        log_order(
            "OCO_ORDER_SUCCESS", 
            symbol, 
            side, 
            quantity, 
            f"TP:{take_profit_price},SL:{stop_loss_price}",
            order_id=f"TP:{tp_order['orderId']},SL:{sl_order['orderId']}", 
            status="PLACED"
        )
        
        # Display results
        print(f"\n✓ OCO orders placed successfully!")
        print(f"Take Profit Order ID: {tp_order['orderId']}")
        print(f"Stop Loss Order ID: {sl_order['orderId']}")
        print(f"Symbol: {symbol}")
        print(f"Side: {side}")
        print(f"Quantity: {format_number(quantity)}")
        print(f"Take Profit Price: {format_number(take_profit_price)}")
        print(f"Stop Loss Price: {format_number(stop_loss_price)}")
        print(f"Current Market Price: {format_number(current_price)}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Explain the strategy
        if side == 'SELL':
            profit_pct = ((take_profit_price - current_price) / current_price) * 100
            loss_pct = ((current_price - stop_loss_price) / current_price) * 100
            print(f"\nStrategy (Closing Long Position):")
            print(f"- Profit Target: +{profit_pct:.2f}% if price reaches {take_profit_price}")
            print(f"- Risk Management: -{loss_pct:.2f}% if price falls to {stop_loss_price}")
        else:
            profit_pct = ((current_price - take_profit_price) / current_price) * 100
            loss_pct = ((stop_loss_price - current_price) / current_price) * 100
            print(f"\nStrategy (Closing Short Position):")
            print(f"- Profit Target: +{profit_pct:.2f}% if price falls to {take_profit_price}")
            print(f"- Risk Management: -{loss_pct:.2f}% if price rises to {stop_loss_price}")
        
        # Start monitoring in a separate thread
        print(f"\n🔍 Starting OCO order monitoring...")
        monitor_thread = threading.Thread(
            target=monitor_orders,
            args=(client, symbol, tp_order['orderId'], sl_order['orderId']),
            daemon=True
        )
        monitor_thread.start()
        
        return {
            'take_profit': tp_order,
            'stop_loss': sl_order,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'monitor_thread': monitor_thread
        }
        
    except Exception as e:
        error_msg = handle_api_error(e, "OCO_ORDER")
        log_order("OCO_ORDER_FAILED", symbol, side, quantity, 
                 f"TP:{take_profit_price},SL:{stop_loss_price}", error=error_msg, status="FAILED")
        print(f"\n✗ Error: {error_msg}")
        return None

def main():
    """Main function for CLI interface"""
    parser = argparse.ArgumentParser(
        description='Binance Futures OCO (One-Cancels-Other) Order Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Close long position with OCO
  python src/advanced/oco.py BTCUSDT SELL 0.01 46000 44000
  
  # Close short position with OCO
  python src/advanced/oco.py BTCUSDT BUY 0.01 44000 46000
  
  # Dry run test
  python src/advanced/oco.py ETHUSDT SELL 0.1 3200 2800 --dry-run

Note: 
- Use SELL side to close long positions (take profit above, stop loss below current price)
- Use BUY side to close short positions (take profit below, stop loss above current price)
        """
    )
    
    parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    parser.add_argument('side', choices=['BUY', 'SELL'], help='Order side to close position')
    parser.add_argument('quantity', type=float, help='Order quantity')
    parser.add_argument('take_profit', type=float, help='Take profit price')
    parser.add_argument('stop_loss', type=float, help='Stop loss price')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Test order without actually placing it')
    parser.add_argument('--monitor-time', type=int, default=3600,
                       help='How long to monitor orders in seconds (default: 3600)')
    
    args = parser.parse_args()
    
    print(f"\n=== Binance Futures OCO Order Bot ===")
    print(f"Symbol: {args.symbol}")
    print(f"Side: {args.side}")
    print(f"Quantity: {args.quantity}")
    print(f"Take Profit: {args.take_profit}")
    print(f"Stop Loss: {args.stop_loss}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Monitor Time: {args.monitor_time}s")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=====================================\n")
    
    # Place the OCO orders
    result = place_oco_order(
        args.symbol, 
        args.side, 
        args.quantity, 
        args.take_profit, 
        args.stop_loss,
        args.dry_run
    )
    
    if result is None:
        print("\nOCO orders failed. Check the logs for details.")
        sys.exit(1)
    
    if not args.dry_run and 'monitor_thread' in result:
        print(f"\nOCO orders are being monitored. Press Ctrl+C to stop monitoring.")
        try:
            # Wait for monitoring to complete or user interruption
            result['monitor_thread'].join(args.monitor_time)
        except KeyboardInterrupt:
            print(f"\n\nMonitoring stopped by user.")
    
    print(f"\nOCO order setup completed successfully!")
    sys.exit(0)

if __name__ == "__main__":
    main()