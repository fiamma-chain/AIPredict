# AI Trading Arena

An AI trading arena platform similar to nof1.ai, where multiple AI models compete in real markets.

## System Architecture

### Core Modules

1. **Trading Execution Layer** (`trading/`)
   - Hyperliquid contract trading interface
   - Order management and risk control
   - Real-time market data

2. **AI Strategy Layer** (`strategies/`)
   - Strategy base classes and interfaces
   - Multiple AI trading strategy implementations
   - Strategy backtesting framework

3. **Arena System** (`arena/`)
   - Model registration and management
   - Performance tracking and scoring
   - Leaderboard system

4. **Data Layer** (`data/`)
   - Trading history records
   - Performance metrics calculation
   - Data persistence

5. **Web Interface** (`web/`)
   - Real-time trading display
   - Leaderboard visualization
   - Model detail pages

## Tech Stack

- **Backend**: Python 3.11+
- **Trading Platform**: Hyperliquid & Aster
- **Web Framework**: FastAPI
- **Frontend**: HTML + JavaScript
- **Database**: Redis
- **Real-time Communication**: WebSocket
- **Monitoring**: Custom logging

## Features

- ✅ Multiple AI models trading in parallel
- ✅ Real-time performance tracking
- ✅ Transparent trading history
- ✅ Risk management system
- ✅ Leaderboard and competition mechanism
- ✅ RESTful API
- ✅ Multi-platform support (Hyperliquid & Aster)
- ✅ Consensus voting mechanism
- ✅ Individual AI traders

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Start backend service
python consensus_arena_multiplatform.py

# Access web interface
# Open http://localhost:8000 in your browser
```

## Project Structure

```
AIPredict/
├── trading/              # Trading execution layer
│   ├── hyperliquid/     # Hyperliquid interface
│   ├── aster/           # Aster interface
│   ├── auto_trader.py   # Auto trading logic
│   ├── multi_platform_trader.py  # Multi-platform management
│   └── kline_manager.py # K-line data manager
├── ai_models/           # AI models
│   ├── base_ai.py      # Base AI class
│   ├── deepseek_trader.py
│   ├── claude_trader.py
│   ├── grok_trader.py
│   ├── gpt_trader.py
│   ├── gemini_trader.py
│   └── qwen_trader.py
├── config/              # Configuration
│   └── settings.py
├── utils/               # Utilities
│   ├── redis_manager.py
│   └── symbol_filter.py
├── web/                 # Web interface
│   └── consensus_arena.html
├── logs/                # Log files
└── consensus_arena_multiplatform.py  # Main entry point
```

## Key Improvements

### AI Decision Optimization

The system now implements an optimized decision flow:

1. **Step 1: Individual AI Decision** - All 6 independent AI models make their decisions first
2. **Step 2: Group Consensus** - Alpha and Beta groups reuse the individual AI decisions for consensus voting (no redundant API calls)
3. **Step 3: Trade Execution** - Individual AI traders execute their pre-made decisions

**Benefits:**
- ✅ Reduced API calls by 66% (from 18 to 6 calls per cycle)
- ✅ Lower costs and faster execution
- ✅ Consistent decisions across individual and group trading

## Security Notice

⚠️ This system involves real money trading. Before using:
1. Thoroughly test all strategies
2. Set reasonable risk limits
3. Start with small amounts
4. Monitor all trading activities

## License

MIT


