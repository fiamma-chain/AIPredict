# 快速开始指南

欢迎使用 AI Trading Arena！这个指南将帮助你快速启动系统。

## 📋 前置要求

- Python 3.11+
- Hyperliquid 账户和私钥
- 足够的测试资金（建议从测试网开始）

## 🚀 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件（参考 `.env.example`）：

```bash
# Hyperliquid 配置
HYPERLIQUID_PRIVATE_KEY=你的私钥
HYPERLIQUID_TESTNET=true

# 交易配置
MAX_POSITION_SIZE=1000
MAX_LEVERAGE=5
STOP_LOSS_PERCENTAGE=5.0
TAKE_PROFIT_PERCENTAGE=10.0

# 风险管理
DAILY_LOSS_LIMIT=500
MAX_OPEN_POSITIONS=5
MIN_ACCOUNT_BALANCE=100
```

### 3. 启动系统

```bash
python main.py
```

系统将启动：
- ✅ Hyperliquid 交易客户端
- ✅ 交易执行引擎
- ✅ 3 个示例 AI 策略
- ✅ REST API 服务器（端口 8000）
- ✅ WebSocket 实时数据推送

### 4. 访问 Web 界面

在浏览器中打开 `web/index.html` 或访问：

```bash
cd web
python -m http.server 8080
```

然后打开：http://localhost:8080

### 5. 查看 API 文档

访问：http://localhost:8000/docs

## 📊 系统架构

```
AI Trading Arena
│
├── Trading Layer（交易层）
│   ├── Hyperliquid Client - 交易所接口
│   ├── Order Manager - 订单管理
│   └── Risk Manager - 风险管理
│
├── Strategy Layer（策略层）
│   ├── Base Strategy - 策略基类
│   ├── Trend Following - 趋势跟踪
│   ├── Mean Reversion - 均值回归
│   └── ML Strategy - 机器学习策略
│
├── Arena System（竞技场系统）
│   ├── Trading Engine - 交易引擎
│   ├── Performance Tracker - 性能追踪
│   └── Leaderboard - 排行榜
│
└── API Layer（接口层）
    ├── REST API - HTTP 接口
    ├── WebSocket - 实时推送
    └── Web UI - Web 界面
```

## 🎯 内置策略

### 1. 趋势跟踪策略（Trend Following）
- 使用快慢均线交叉判断趋势
- 适合趋势明显的市场
- 参数：fast_period=10, slow_period=30

### 2. 均值回归策略（Mean Reversion）
- 基于价格偏离均值进行反向操作
- 适合震荡市场
- 参数：period=20, std_multiplier=2.0

### 3. 机器学习策略（ML Strategy）
- 提取多维特征进行决策
- 动态止损止盈
- 参数：lookback_period=50, feature_window=10

## 🔧 自定义策略

创建你自己的策略：

```python
from strategies.base import BaseStrategy, StrategyConfig, Signal

class MyStrategy(BaseStrategy):
    async def analyze(self, coin: str, market_data: dict) -> Signal:
        # 你的分析逻辑
        if buy_condition:
            return Signal.BUY
        elif sell_condition:
            return Signal.CLOSE
        return Signal.HOLD
    
    def get_position_size(self, coin: str, signal: Signal, balance: float) -> float:
        # 计算仓位大小
        return balance * 0.1

# 在 main.py 中注册
config = StrategyConfig(
    name="My Strategy",
    coins=["BTC", "ETH"],
    max_positions=2,
    position_size=200.0
)
strategy = MyStrategy(config)
trading_engine.register_strategy(strategy)
```

## 🛡️ 安全建议

1. **从测试网开始**
   ```bash
   HYPERLIQUID_TESTNET=true
   ```

2. **设置合理的风险限制**
   - 每日亏损限制
   - 最大持仓数量
   - 单仓位大小限制

3. **小资金测试**
   - 先用小额资金验证策略
   - 确认系统稳定后再增加资金

4. **监控系统**
   - 定期检查日志
   - 关注风险指标
   - 及时调整参数

## 📈 监控指标

### 策略性能
- **总盈亏（Total PnL）** - 累计盈亏金额
- **ROI%** - 投资回报率百分比
- **胜率（Win Rate）** - 盈利交易占比
- **夏普比率（Sharpe Ratio）** - 风险调整后收益
- **盈亏比（Profit Factor）** - 总盈利/总亏损
- **最大回撤（Max Drawdown）** - 最大资金回撤

### 风险指标
- **当前持仓数** - 实时持仓数量
- **总敞口** - 总持仓价值
- **未实现盈亏** - 当前持仓盈亏
- **日亏损使用率** - 已达日亏损限制的百分比

## 🔌 API 使用示例

### 获取排行榜
```bash
curl http://localhost:8000/leaderboard?metric=total_pnl&limit=10
```

### 获取策略详情
```bash
curl http://localhost:8000/strategies/{strategy_id}
```

### WebSocket 连接
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('实时数据:', data);
};
```

## 🐛 故障排除

### 问题：无法连接到 Hyperliquid
- 检查私钥是否正确
- 确认网络连接
- 验证 API URL 设置

### 问题：策略不执行交易
- 检查账户余额是否充足
- 确认风险限制设置
- 查看日志了解详细错误

### 问题：API 无法访问
- 确认端口未被占用
- 检查防火墙设置
- 验证 API_HOST 和 API_PORT 配置

## 📚 进一步学习

- 查看 `README.md` 了解完整功能
- 阅读代码注释了解实现细节
- 访问 Hyperliquid 文档学习 API

## 💡 最佳实践

1. **回测优先** - 在实盘前充分回测策略
2. **渐进式部署** - 逐步增加资金和策略
3. **分散风险** - 不要把所有资金放在一个策略
4. **持续监控** - 定期检查系统状态
5. **记录日志** - 保留交易记录便于分析

## 🤝 获取帮助

如果遇到问题：
1. 检查日志文件
2. 查看 API 文档：http://localhost:8000/docs
3. 阅读源代码注释

---

**重要提示**：加密货币交易存在风险，请谨慎操作。建议从测试网和小额资金开始。

