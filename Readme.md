Binance Futures Order Bot
A comprehensive CLI-based trading bot for Binance USDT-M Futures supporting multiple order types with robust logging, validation, and advanced trading strategies. It supports:

Market orders
Limit orders
Stop‑Limit, OCO‑like TP/SL management, TWAP, and Grid placement
Always use Binance Futures Testnet for development.

1. Project Structure
Clone/extract with this layout:

Devanshi_binance_bot/
├── src/
│   ├── _init_.py
│   ├── market_orders.py
│   ├── limit_orders.py
│   ├── config.py
│   ├── utils.py
│   └── advanced/
│       ├── _init_.py
│       ├── oco.py
│       ├── twap.py
│       ├── stop_limit.py
│       └── grid.py
├── bot.log
├── report.pdf
├── requirements.txt
└── .env (create from .env.example)

2. Prerequisites (Windows)
Python 3.10+ installed (py --version)
Binance Futures Testnet API key/secret from https://testnet.binancefuture.com
1. Go to the link provided
2. Login
3. Scroll down the page you will find the required API and the SECRET key
3. Setup
Clone Repository:
git clone https://github.com/Devanshi310/devanshi-binance-bot
cd Devanshi-finance-bot
Install Dependencies:

pip install -r requirements.txt
Configure environment variable:

Copy .env.example to .env and fill in your Testnet keys:
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
USE_TESTNET=True
Connectivity check:
python -c "from src.config import get_client; print(get_client().futures_ping())"
4. Usage
All commands run from repo root.

Market order:
python src/market_orders.py BTCUSDT BUY 0.01
Limit order:
python src\limit_orders.py BTCUSDT BUY 0.01 45000
Stop‑Limit:
python src\advanced\stop_limit.py BTCUSDT BUY 0.01 44000 45000
OCO‑like TP/SL (places TP limit and SL market with monitoring):
python src\advanced\oco.py BTCUSDT SELL 0.01 46000 44000
TWAP (split total quantity into slices over time):
.\.venv\Scripts\python.exe src\advanced\twap.py BTCUSDT BUY 0.05 60 10
Grid (static placement of buy/sell limits across range):
python src\advanced\grid.py BTCUSDT 44000 46000 10 0.01
5. Logs
Logs are written to bot.log with format [TIMESTAMP] [LEVEL] [ACTION] - message.
6. Troubleshooting
Activation blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Invalid symbol/qty/price: ensure USDT symbol and tick/step compliance; try 0.01 or 0.001 quantities.
Insufficient balance: fund Testnet USD‑M Futures wallet and transfer to Futures.
Network errors: retry later; rate limits may apply.
7. Parameter and Validation Notes
Use USDT‑margined symbols (e.g., BTCUSDT).
Quantity and price must satisfy exchange filters:
Tick size compliance for price
Step size and minQty compliance for quantity
Min notional: price × quantity ≥ 100 (approx., varies by symbol)
If you get “Order would immediately trigger,” move TP higher or SL lower relative to the current price.
8. Checking Account State
\.venv\Scripts\python.exe -c "from src.config import get_client; c=get_client(); print('balance=', c.futures_account_balance()); print('position=', c.futures_position_information(symbol='BTCUSDT')); print('open=', c.futures_get_open_orders(symbol='BTCUSDT'))"
Cancel all open orders (per symbol):

\.venv\Scripts\python.exe -c "from src.config import get_client; print(get_client().futures_cancel_all_open_orders(symbol='BTCUSDT'))"
9. Test Checklist (before submission)
# Connectivity
\.venv\Scripts\python.exe -c "from src.config import get_client; print(get_client().futures_ping())"
\.venv\Scripts\python.exe -c "from src.config import get_client; c=get_client(); print(c.futures_symbol_ticker(symbol='BTCUSDT'))"

# Market order buy and close
\.venv\Scripts\python.exe src\market_orders.py BTCUSDT BUY 0.001
\.venv\Scripts\python.exe -c "from src.config import get_client; c=get_client(); print(c.futures_position_information(symbol='BTCUSDT'))"
\.venv\Scripts\python.exe src\market_orders.py BTCUSDT SELL 0.001

# Limit order (ensure price*qty >= 100)
\.venv\Scripts\python.exe src\limit_orders.py BTCUSDT BUY 0.001 117500
\.venv\Scripts\python.exe -c "from src.config import get_client; c=get_client(); print(c.futures_get_open_orders(symbol='BTCUSDT'))"

# Advanced strategies
\.venv\Scripts\python.exe src\advanced\stop_limit.py BTCUSDT BUY 0.001 119500 119600
\.venv\Scripts\python.exe src\advanced\twap.py BTCUSDT BUY 0.005 30 5
\.venv\Scripts\python.exe src\advanced\grid.py BTCUSDT 117000 119000 5 0.001
\.venv\Scripts\python.exe src\advanced\oco.py BTCUSDT SELL 0.001 120000 117000

# Cleanup
\.venv\Scripts\python.exe -c "from src.config import get_client; print(get_client().futures_cancel_all_open_orders(symbol='BTCUSDT'))"
10. Logs
Actions are logged to bot.log in the project root.
Get-Content -Tail 100 .\bot.log
11. Security Notes
Never commit real API keys. Keep them in .env and do not push .env to Git.
Revoke any keys that were shared publicly and generate new Testnet keys.
