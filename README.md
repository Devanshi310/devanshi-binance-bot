## Binance Futures Order Bot

This project places and manages Binance USD‑M Futures orders via CLI. It supports:

- Market orders
- Limit orders
- (Bonus) Stop‑Limit, OCO‑like TP/SL management, TWAP, and Grid placement

Always use Binance Futures Testnet for development.

### 1. Project Structure

Clone/extract with this layout:

```
rahul_binance_bot/
├── src/
│   ├── __init__.py
│   ├── market_orders.py
│   ├── limit_orders.py
│   ├── config.py
│   ├── utils.py
│   └── advanced/
│       ├── __init__.py
│       ├── oco.py
│       ├── twap.py
│       ├── stop_limit.py
│       └── grid.py
├── bot.log
├── report.pdf
├── requirements.txt
└── .env (create from .env.example)
```

### 2. Prerequisites (Windows)

- Python 3.10+ installed (`py --version`)
- Binance Futures Testnet API key/secret from `https://testnet.binancefuture.com`

### 3. Setup

1) In PowerShell:

```powershell
cd "C:\Users\rahul\Downloads\PrimeTradeAi\rahul_binance_bot"
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

2) Configure environment variables:

- Copy `.env.example` to `.env` and fill in your Testnet keys:

```
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
USE_TESTNET=True
```

3) Connectivity check:

```powershell
python -c "from src.config import get_client; print(get_client().futures_ping())"
```

### 4. Usage

All commands run from repo root.

- Market order:

```powershell
python src\market_orders.py BTCUSDT BUY 0.01
```

- Limit order:

```powershell
python src\limit_orders.py BTCUSDT BUY 0.01 45000
```

- Stop‑Limit:

```powershell
python src\advanced\stop_limit.py BTCUSDT BUY 0.01 44000 45000
```

- OCO‑like TP/SL (places TP limit and SL market with monitoring):

```powershell
python src\advanced\oco.py BTCUSDT SELL 0.01 46000 44000
```

- TWAP (split total quantity into slices over time):

```powershell
python src\advanced\twap.py BTCUSDT BUY 1.0 60 5
```

- Grid (static placement of buy/sell limits across range):

```powershell
python src\advanced\grid.py BTCUSDT 44000 46000 10 0.01
```

### 5. Logs

- Logs are written to `bot.log` with format `[TIMESTAMP] [LEVEL] [ACTION] - message`.

### 6. Troubleshooting

- Activation blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
- Invalid symbol/qty/price: ensure USDT symbol and tick/step compliance; try `0.01` or `0.001` quantities.
- Insufficient balance: fund Testnet USD‑M Futures wallet and transfer to Futures.
- Network errors: retry later; rate limits may apply.

### 7. Notes

- OCO in USD‑M Futures is emulated by placing TP limit and SL market orders with `reduceOnly=True` and canceling the other when one fills.
- Always test on Testnet first.



### 8. Parameter and Validation Notes

- Use USDT‑margined symbols (e.g., `BTCUSDT`).
- Quantity and price must satisfy exchange filters:
  - Tick size compliance for price
  - Step size and minQty compliance for quantity
  - Min notional: price × quantity ≥ 100 (approx., varies by symbol)
- If you get “Order would immediately trigger,” move TP higher or SL lower relative to the current price.

### 9. Checking Account State

```powershell
\.venv\Scripts\python.exe -c "from src.config import get_client; c=get_client(); print('balance=', c.futures_account_balance()); print('position=', c.futures_position_information(symbol='BTCUSDT')); print('open=', c.futures_get_open_orders(symbol='BTCUSDT'))"
```

Cancel all open orders (per symbol):

```powershell
\.venv\Scripts\python.exe -c "from src.config import get_client; print(get_client().futures_cancel_all_open_orders(symbol='BTCUSDT'))"
```

### 10. Test Checklist (before submission)

```powershell
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
```

### 11. Logs

- Actions are logged to `bot.log` in the project root.

```powershell
Get-Content -Tail 100 .\bot.log
```

### 12. Submission Checklist

- Private GitHub repo with project contents; grant instructor access.
- ZIP archive of the project folder (exclude `.venv/` if requested).
- `report.pdf` with required screenshots/analysis.

### 13. Security Notes

- Never commit real API keys. Keep them in `.env` and do not push `.env` to Git.
- Revoke any keys that were shared publicly and generate new Testnet keys.
