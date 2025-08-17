# src/advanced/grid.py
"""
Binance Futures Grid Trading Strategy
Usage: python src/advanced/grid.py BTCUSDT 44000 46000 10 0.01
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
    validate_symbol, validate_quantity, validate_price,
    log_order, handle_api_error, logger, format_number
)

class GridTradingBot:
    def __init__(self, symbol, lower_price, upper_price, grid_levels, quantity_per_grid, dry_run=False):
        self.symbol = validate_symbol(symbol)
        self.lower_price = validate_price(lower_price)
        self.upper_price = validate_price(upper_price)
        self.grid_levels = int(grid_levels)
        self.quantity_per_grid = validate_quantity(quantity_per_grid)
        self.dry_run = dry_run
        
        # Validate grid parameters
        if self.lower_price >= self.upper_price:
            raise ValueError("Lower price must be less than upper price")
        if self.grid_levels < 2:
            raise ValueError("Minimum 2 grid levels required")
        if self.grid_levels > 50:
            raise ValueError("Maximum 50 grid levels allowed")
        
        # Initialize client and state
        self.client = Config.get_client()
        self.grid_orders = {}  # Track placed orders
        self.running = False
        
        # Calculate grid prices
        self.calculate_grid_levels()
        
    def calculate_grid_levels(self):
        """Calculate buy and sell price levels for the grid"""
        price_range = self.upper_price - self.lower_price
        price_step = price_range / (self.grid_levels - 1)
        
        self.buy_levels = []
        self.sell_levels = []
        
        for i in range(self.grid_levels):
            level_price = self.lower_price + (i * price_step)
            
            # Buy orders at lower levels, sell orders at higher levels
            if i < self.grid_levels // 2:
                self.buy_levels.append(level_price)
            else:
                self.sell_levels.append(level_price)
        
        logger.info(f"Grid calculated: {len(self.buy_levels)} buy levels, {len(self.sell_levels)} sell levels")
        
    def get_current_price(self):
        """Get current market price"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
            return float(ticker['price'])
        except Exception as e:
            raise Exception(f"Could not get price for {self.symbol}: {e}")
    
    def place_grid_order(self, side, price, order_id=None):
        """Place a single grid order"""
        try:
            if self.dry_run:
                fake_order_id = f"DRY_RUN_GRID_{side}_{len(self.grid_orders)}"
                logger.info(f"DRY RUN: Would place {side} order at {price}")
                return {
                    'orderId': fake_order_id,
                    'symbol': self.symbol,
                    'side': side,
                    'type': 'LIMIT',
                    'price': str(price),
                    'origQty': str(self.quantity_per_grid),
                    'status': 'DRY_RUN'
                }
            
            order_params = {
                'symbol': self.symbol,
                'side': side,
                'type': 'LIMIT',
                'quantity': self.quantity_per_grid,
                'price': price,
                'timeInForce': 'GTC'
            }
            
            order = self.client.futures_create_order(**order_params)
            
            log_order(f"GRID_{side}_ORDER_PLACED", self.symbol, side, 
                     self.quantity_per_grid, price, order_id=order['orderId'])
            
            return order
            
        except Exception as e:
            error_msg = handle_api_error(e, f"GRID_{side}_ORDER")
            logger.error(f"Failed to place grid order: {error_msg}")
            return None
    
    def cancel_order(self, order_id):
        """Cancel a specific order"""
        try:
            if self.dry_run:
                logger.info(f"DRY RUN: Would cancel order {order_id}")
                return True
            
            self.client.futures_cancel_order(symbol=self.symbol, orderId=order_id)
            logger.info(f"Cancelled order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def check_and_replace_orders(self):
        """Check filled orders and replace them with opposite side orders"""
        try:
            current_price = self.get_current_price()
            orders_to_replace = []
            
            for level_price, order_info in list(self.grid_orders.items()):
                if self.dry_run:
                    continue  # Skip order checking in dry run
                
                order_id = order_info['order_id']
                side = order_info['side']
                
                try:
                    # Check order status
                    order_status = self.client.futures_get_order(
                        symbol=self.symbol, 
                        orderId=order_id
                    )
                    
                    # If order is filled, mark for replacement
                    if order_status['status'] == 'FILLED':
                        logger.info(f"Grid order filled: {side} at {level_price}")
                        orders_to_replace.append((level_price, order_info))
                        
                        # Log the fill
                        log_order(f"GRID_{side}_ORDER_FILLED", self.symbol, side,
                                 self.quantity_per_grid, level_price, order_id=order_id)
                        
                except Exception as e:
                    logger.error(f"Error checking order {order_id}: {e}")
            
            # Replace filled orders with opposite side
            for level_price, old_order_info in orders_to_replace:
                del self.grid_orders[level_price]
                
                # Place opposite order
                old_side = old_order_info['side']
                new_side = 'SELL' if old_side == 'BUY' else 'BUY'
                
                # Calculate new price level
                if new_side == 'BUY':
                    # Place buy order slightly below current level
                    new_price = level_price * 0.995
                    if new_price < self.lower_price:
                        new_price = self.lower_price
                else:
                    # Place sell order slightly above current level
                    new_price = level_price * 1.005
                    if new_price > self.upper_price:
                        new_price = self.upper_price
                
                # Place the replacement order
                new_order = self.place_grid_order(new_side, new_price)
                if new_order:
                    self.grid_orders[new_price] = {
                        'order_id': new_order['orderId'],
                        'side': new_side,
                        'price': new_price,
                        'placed_at': datetime.now()
                    }
                    
                    print(f"🔄 Replaced {old_side} order at {format_number(level_price)} "
                          f"with {new_side} order at {format_number(new_price)}")
                          
        except Exception as e:
            logger.error(f"Error in check_and_replace_orders: {e}")
    
    def initialize_grid(self):
        """Place initial grid orders"""
        try:
            current_price = self.get_current_price()
            
            print(f"\n📊 Initializing Grid Trading Bot")
            print(f"Symbol: {self.symbol}")
            print(f"Current Price: {format_number(current_price)}")
            print(f"Grid Range: {format_number(self.lower_price)} - {format_number(self.upper_price)}")
            print(f"Grid Levels: {self.grid_levels}")
            print(f"Quantity per Level: {format_number(self.quantity_per_grid)}")
            print(f"Dry Run: {self.dry_run}")
            
            # Place buy orders at levels below current price
            for price in self.buy_levels:
                if price < current_price:
                    order = self.place_grid_order('BUY', price)
                    if order:
                        self.grid_orders[price] = {
                            'order_id': order['orderId'],
                            'side': 'BUY',
                            'price': price,
                            'placed_at': datetime.now()
                        }
                        print(f"📈 Placed BUY order at {format_number(price)}")
            
            # Place sell orders at levels above current price
            for price in self.sell_levels:
                if price > current_price:
                    order = self.place_grid_order('SELL', price)
                    if order:
                        self.grid_orders[price] = {
                            'order_id': order['orderId'],
                            'side': 'SELL',
                            'price': price,
                            'placed_at': datetime.now()
                        }
                        print(f"📉 Placed SELL order at {format_number(price)}")
            
            print(f"\n✅ Grid initialized with {len(self.grid_orders)} orders")
            
            # Log grid initialization
            log_order("GRID_INITIALIZED", self.symbol, "BOTH", 
                     len(self.grid_orders) * self.quantity_per_grid,
                     f"Range:{self.lower_price}-{self.upper_price}")
            
            return True
            
        except Exception as e:
            error_msg = handle_api_error(e, "GRID_INITIALIZATION")
            print(f"Failed to initialize grid: {error_msg}")
            return False
    
    def run_grid(self, duration_minutes=60):
        """Run the grid trading bot"""
        try:
            if not self.initialize_grid():
                return False
            
            self.running = True
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            print(f"\n🚀 Grid trading started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Will run until {end_time.strftime('%Y-%m-%d %H:%M:%S')} (Ctrl+C to stop early)")
            
            cycle_count = 0
            
            while self.running and datetime.now() < end_time:
                cycle_count += 1
                current_price = self.get_current_price()
                
                print(f"\n🔍 Cycle {cycle_count} - Price: {format_number(current_price)} "
                      f"- Active Orders: {len(self.grid_orders)}")
                
                # Check and replace filled orders
                if not self.dry_run:
                    self.check_and_replace_orders()
                
                # Display grid status
                if cycle_count % 10 == 0:  # Every 10 cycles
                    self.display_grid_status()
                
                # Wait before next cycle
                time.sleep(30)  # Check every 30 seconds
            
            print(f"\n🏁 Grid trading completed after {cycle_count} cycles")
            self.stop_grid()
            
            return True
            
        except KeyboardInterrupt:
            print(f"\n⏹️  Grid trading stopped by user")
            self.stop_grid()
            return False
        except Exception as e:
            error_msg = handle_api_error(e, "GRID_EXECUTION")
            print(f"Grid trading error: {error_msg}")
            self.stop_grid()
            return False
    
    def display_grid_status(self):
        """Display current grid status"""
        try:
            current_price = self.get_current_price()
            buy_orders = sum(1 for info in self.grid_orders.values() if info['side'] == 'BUY')
            sell_orders = sum(1 for info in self.grid_orders.values() if info['side'] == 'SELL')
            
            print(f"\n📋 Grid Status:")
            print(f"Current Price: {format_number(current_price)}")
            print(f"Active Orders: {len(self.grid_orders)} (BUY: {buy_orders}, SELL: {sell_orders})")
            print(f"Price Range: {format_number(self.lower_price)} - {format_number(self.upper_price)}")
            
            if current_price < self.lower_price:
                print(f"⚠️  Price below grid range!")
            elif current_price > self.upper_price:
                print(f"⚠️  Price above grid range!")
                
        except Exception as e:
            logger.error(f"Error displaying grid status: {e}")
    
    def stop_grid(self):
        """Stop grid trading and cancel all orders"""
        self.running = False
        
        print(f"\n🛑 Stopping grid trading...")
        cancelled_count = 0
        
        for level_price, order_info in list(self.grid_orders.items()):
            if self.cancel_order(order_info['order_id']):
                cancelled_count += 1
        
        print(f"✅ Cancelled {cancelled_count} orders")
        
        # Log grid stop
        log_order("GRID_STOPPED", self.symbol, "BOTH", 0, 
                 f"Cancelled:{cancelled_count}")

def main():
    """Main function for CLI interface"""
    parser = argparse.ArgumentParser(
        description='Binance Futures Grid Trading Strategy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # BTC grid between 44000-46000 with 10 levels, 0.01 BTC per level
  python src/advanced/grid.py BTCUSDT 44000 46000 10 0.01
  
  # ETH grid with 20 levels over 2 hours
  python src/advanced/grid.py ETHUSDT 3000 3200 20 0.1 --duration 120
  
  # Test grid without real orders
  python src/advanced/grid.py BTCUSDT 44000 46000 10 0.01 --dry-run

Strategy Notes:
- Places buy orders below current price, sell orders above
- When an order fills, replaces it with opposite side order
- Profits from price oscillations within the range
- Works best in sideways/ranging markets
        """
    )
    
    parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    parser.add_argument('lower_price', type=float, help='Lower bound of grid range')
    parser.add_argument('upper_price', type=float, help='Upper bound of grid range')
    parser.add_argument('grid_levels', type=int, help='Number of grid levels (2-50)')
    parser.add_argument('quantity', type=float, help='Quantity per grid level')
    parser.add_argument('--duration', type=int, default=60,
                       help='Duration to run in minutes (default: 60)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Test strategy without placing real orders')
    
    args = parser.parse_args()
    
    print(f"\n=== Binance Futures Grid Trading Bot ===")
    print(f"Symbol: {args.symbol}")
    print(f"Price Range: {args.lower_price} - {args.upper_price}")
    print(f"Grid Levels: {args.grid_levels}")
    print(f"Quantity per Level: {args.quantity}")
    print(f"Duration: {args.duration} minutes")
    print(f"Dry Run: {args.dry_run}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"======================================\n")
    
    try:
        # Create and run grid bot
        grid_bot = GridTradingBot(
            args.symbol,
            args.lower_price,
            args.upper_price,
            args.grid_levels,
            args.quantity,
            args.dry_run
        )
        
        # Ask for confirmation unless dry run
        if not args.dry_run:
            total_quantity = args.grid_levels * args.quantity
            print(f"⚠️  This will use approximately {format_number(total_quantity)} {args.symbol[:-4]} in total")
            response = input("   Continue? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Grid strategy cancelled by user")
                sys.exit(0)
        
        success = grid_bot.run_grid(args.duration)
        
        if success:
            print("\n✅ Grid strategy completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Grid strategy failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    from datetime import timedelta
    main()