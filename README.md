## Binance Futures Order Bot

A comprehensive CLI-based trading bot for Binance USDT-M Futures supporting multiple order types with robust logging, validation, and advanced trading strategie. It supports:

- Market orders
- Limit orders
- Stop‑Limit, OCO‑like TP/SL management, TWAP, and Grid placement

Always use Binance Futures Testnet for development.

### 1. Project Structure

Clone/extract with this layout:

```
devanshi_binance_bot/
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
  ```
  1. Go to the link provided
  2. Login
  3. Scroll down the page, click on the API key and get the required API key and Secret Key

### 3. Setup

1) Clone Repository:

```powershell
git clone https://github.com/Devanshi310/devanshi-binance-bot
cd devanshi-binance-bot
```

2) Install Dependencies
   ```powershell
    pip install -r requirements.txt
   ```

2) Configure environment variables:

- Copy `.env.example` to `.env` and fill in your Testnet keys:

```
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
USE_TESTNET=True
```


### 4. Usage

All commands run from repo root.

- Market order:

```powershell
python src/market_orders.py BTCUSDT BUY 0.01
```

- Limit order:

```powershell
python src/limit_orders.py BTCUSDT BUY 0.01 40000 --check-status
```

- Stop‑Limit:

```powershell
python src/advanced/stop_limit.py BTCUSDT BUY 0.01 47000 47500 --dry-run
```

- OCO:

```powershell
python src/advanced/oco.py BTCUSDT SELL 0.01 46000 44000 --dry-run
```

- TWAP (split total quantity into slices over time):

```powershell
python src/advanced/twap.py BTCUSDT BUY 0.1 10 3 --dry-run
```

- Grid (static placement of buy/sell limits across range):

```powershell
python src/advanced/grid.py BTCUSDT 110000 125000 10 0.01 --dry-run
```

### 5. Logs

- Logs are written to `bot.log` with format `[TIMESTAMP] [LEVEL] [ACTION] - message`.


### 6. Security Notes

- Never commit real API keys. Keep them in `.env` and do not push `.env` to Git.
- Revoke any keys that were shared publicly and generate new Testnet keys.


