# 交易策略定义和使用指南

## 📋 概述

本系统提供了完整的交易策略定义框架，支持：

✅ 定义自定义交易策略  
✅ 导出策略供用户使用  
✅ 导入用户策略到AI模型  
✅ 策略版本管理  
✅ 策略性能追踪  

## 🏗️ 策略结构

### 核心组件

```python
TradingStrategy
├── 基本信息 (名称、版本、描述等)
├── 策略分类 (类型、时间周期)
├── 适用市场 (币种、平台)
├── 风险管理 (止损、止盈、仓位管理)
├── 技术指标配置
├── 进场/出场条件
├── 市场条件过滤
└── AI提示词模板
```

## 🚀 快速开始

### 1. 使用预定义策略

```python
from trading.strategy import get_strategy_manager, create_aggressive_swing_strategy

# 获取策略管理器
manager = get_strategy_manager()

# 列出所有策略
strategies = manager.list_strategies()
for s in strategies:
    print(f"{s.name} - {s.description}")

# 获取特定策略
strategy = manager.get_strategy("aggressive_swing_v1")
print(strategy.to_json())
```

### 2. 创建自定义策略

```python
from trading.strategy import (
    TradingStrategy, StrategyType, TimeFrame,
    RiskManagement, PositionSizing, IndicatorConfig
)

# 创建新策略
my_strategy = TradingStrategy(
    strategy_id="my_custom_strategy_v1",
    name="我的自定义策略",
    version="1.0.0",
    description="基于RSI和MACD的趋势跟踪策略",
    author="张三",
    strategy_type=StrategyType.TREND_FOLLOWING,
    timeframe=TimeFrame.H1,
    min_confidence=60.0,
    
    # 风险管理
    risk_management=RiskManagement(
        stop_loss_pct=4.0,
        take_profit_pct=8.0,
        trailing_stop=True,
        trailing_stop_pct=2.5,
        max_position_size_pct=12.0,
        risk_reward_ratio=2.0
    ),
    
    # 仓位管理
    position_sizing=PositionSizing(
        method="fixed_percentage",
        base_size_pct=8.0,
        use_confidence=True,
        max_positions=3
    ),
    
    # 技术指标
    indicators=[
        IndicatorConfig(
            name="RSI",
            enabled=True,
            params={"period": 14, "overbought": 70, "oversold": 30},
            weight=0.8
        ),
        IndicatorConfig(
            name="MACD",
            enabled=True,
            params={"fast": 12, "slow": 26, "signal": 9},
            weight=0.7
        ),
        IndicatorConfig(
            name="MA",
            enabled=True,
            params={"period": 50, "type": "EMA"},
            weight=0.6
        )
    ],
    
    tags=["trend", "rsi", "macd"]
)

# 保存到策略管理器
manager.add_strategy(my_strategy)
```

### 3. 导出策略

```python
# 导出为JSON文件
my_strategy.save_to_file("my_strategy.json")

# 或使用策略管理器导出
manager.export_strategy("my_custom_strategy_v1", "my_strategy.json")

# 导出为JSON字符串
json_str = my_strategy.to_json()
print(json_str)
```

### 4. 导入策略

```python
# 从文件导入
imported_strategy = TradingStrategy.load_from_file("my_strategy.json")

# 或使用策略管理器导入
strategy = manager.import_strategy("my_strategy.json")

# 从JSON字符串导入
strategy = TradingStrategy.from_json(json_str)
```

## 📊 策略示例

### 示例1: 激进波段策略（默认）

```json
{
  "strategy_id": "aggressive_swing_v1",
  "name": "激进波段策略",
  "version": "1.0.0",
  "description": "追求更大收益空间的波段交易策略，止损5%/止盈10%",
  "strategy_type": "swing",
  "timeframe": "15m",
  "min_confidence": 50.0,
  "risk_management": {
    "stop_loss_pct": 5.0,
    "take_profit_pct": 10.0,
    "trailing_stop": true,
    "trailing_stop_pct": 3.0,
    "risk_reward_ratio": 2.0
  },
  "position_sizing": {
    "method": "fixed_percentage",
    "base_size_pct": 10.0,
    "use_confidence": true
  },
  "indicators": [
    {
      "name": "RSI",
      "enabled": true,
      "params": {"period": 14},
      "weight": 0.8
    },
    {
      "name": "MA",
      "enabled": true,
      "params": {"period": 20, "type": "SMA"},
      "weight": 0.6
    }
  ]
}
```

### 示例2: 保守稳健策略

```json
{
  "strategy_id": "conservative_v1",
  "name": "保守稳健策略",
  "version": "1.0.0",
  "description": "风险较低的稳健策略，止损3%/止盈6%",
  "strategy_type": "trend_following",
  "timeframe": "1h",
  "min_confidence": 70.0,
  "risk_management": {
    "stop_loss_pct": 3.0,
    "take_profit_pct": 6.0,
    "risk_reward_ratio": 2.0
  },
  "position_sizing": {
    "base_size_pct": 5.0,
    "max_positions": 2
  }
}
```

### 示例3: 高频剥头皮策略

```json
{
  "strategy_id": "scalping_v1",
  "name": "高频剥头皮策略",
  "version": "1.0.0",
  "description": "快进快出，小止损小止盈",
  "strategy_type": "scalping",
  "timeframe": "5m",
  "min_confidence": 60.0,
  "risk_management": {
    "stop_loss_pct": 1.0,
    "take_profit_pct": 2.0
  },
  "market_conditions": {
    "min_volume_24h": 1000000,
    "max_spread_pct": 0.2
  }
}
```

## 🔧 高级功能

### 1. 添加进场条件

```python
from trading.strategy import EntryCondition, ExitCondition

# 定义做多进场条件
long_entry = [
    EntryCondition(
        condition_type="indicator",
        operator="<",
        value=30,
        required=True,
        description="RSI 小于 30 (超卖)"
    ),
    EntryCondition(
        condition_type="indicator",
        operator="cross_above",
        value="signal_line",
        required=True,
        description="MACD 上穿信号线"
    ),
    EntryCondition(
        condition_type="price",
        operator=">",
        value="MA_20",
        required=False,
        description="价格在20日均线上方"
    )
]

# 添加到策略
my_strategy.entry_conditions["long"] = long_entry
```

### 2. 添加出场条件

```python
# 定义做多出场条件
long_exit = [
    ExitCondition(
        condition_type="indicator",
        operator=">",
        value=70,
        priority=1,
        description="RSI 大于 70 (超买)"
    ),
    ExitCondition(
        condition_type="price",
        operator="<",
        value="stop_loss",
        priority=10,
        description="触及止损位"
    ),
    ExitCondition(
        condition_type="price",
        operator=">",
        value="take_profit",
        priority=9,
        description="触及止盈位"
    )
]

my_strategy.exit_conditions["long"] = long_exit
```

### 3. 自定义AI提示词模板

```python
custom_prompt = """你是一个专业的加密货币交易员，使用 {strategy_name} 策略。

当前币种: {coin}
策略类型: {strategy_type}

当前市场数据:
- 价格: ${price}
- RSI: {rsi}
- MACD: {macd}

策略要求:
- 止损: {stop_loss_pct}%
- 止盈: {take_profit_pct}%
- 最小信心度: {min_confidence}%

请基于以上信息做出交易决策。
"""

my_strategy.prompt_template = custom_prompt
```

### 4. 生成AI提示词

```python
market_data = {
    "price": 67234.50,
    "rsi": 45,
    "macd": 120
}

prompt = my_strategy.get_prompt_for_ai(market_data, "BTC")
print(prompt)
```

### 5. 策略克隆和修改

```python
# 克隆现有策略
new_strategy = my_strategy.clone()
new_strategy.name = "修改版策略"
new_strategy.risk_management.stop_loss_pct = 6.0

# 保存新策略
manager.add_strategy(new_strategy)
```

## 🎯 在AI模型中使用策略

### 1. 为AI模型设置策略

```python
from ai_models.deepseek_trader import DeepSeekTrader
from trading.strategy import get_strategy_manager

# 创建AI交易员
ai_trader = DeepSeekTrader(api_key="your_api_key")

# 获取策略
manager = get_strategy_manager()
strategy = manager.get_strategy("aggressive_swing_v1")

# 为AI设置策略（扩展AI类）
ai_trader.strategy = strategy
```

### 2. 应用策略到决策过程

```python
# 在AI的analyze_market方法中应用策略
async def analyze_market_with_strategy(self, coin, market_data, ...):
    # 获取策略提示词
    if hasattr(self, 'strategy') and self.strategy:
        prompt = self.strategy.get_prompt_for_ai(market_data, coin)
    else:
        prompt = self.create_market_prompt(...)
    
    # 调用AI API获取决策
    decision, confidence, reasoning = await self.call_ai_api(prompt)
    
    # 应用策略过滤和调整
    if hasattr(self, 'strategy') and self.strategy:
        result = self.strategy.merge_with_ai_style({
            'decision': decision,
            'confidence': confidence,
            'reasoning': reasoning
        })
        return result['decision'], result['confidence'], result['reasoning']
    
    return decision, confidence, reasoning
```

## 📤 导出策略给用户

### 方式1: 导出单个策略

```python
# 导出为JSON文件
strategy = manager.get_strategy("aggressive_swing_v1")
strategy.save_to_file("strategies/aggressive_swing.json")
```

### 方式2: 导出所有策略

```python
import os

# 创建策略目录
os.makedirs("exported_strategies", exist_ok=True)

# 导出所有策略
for strategy_id, strategy in manager.strategies.items():
    filename = f"exported_strategies/{strategy_id}.json"
    strategy.save_to_file(filename)
    print(f"已导出: {strategy.name} -> {filename}")
```

### 方式3: 生成策略目录

```python
# 生成策略列表（用于用户浏览）
strategy_catalog = []
for strategy in manager.list_strategies():
    strategy_catalog.append({
        "id": strategy.strategy_id,
        "name": strategy.name,
        "type": strategy.strategy_type.value,
        "description": strategy.description,
        "risk_level": "高" if strategy.risk_management.stop_loss_pct >= 5 else "低",
        "timeframe": strategy.timeframe.value,
        "tags": strategy.tags
    })

# 保存目录
import json
with open("strategy_catalog.json", "w", encoding="utf-8") as f:
    json.dump(strategy_catalog, f, indent=2, ensure_ascii=False)
```

## 📥 导入用户策略

### 方式1: 从文件导入

```python
# 用户上传策略文件
user_strategy_file = "user_uploaded_strategy.json"

try:
    # 导入并验证策略
    user_strategy = manager.import_strategy(user_strategy_file)
    
    print(f"✅ 成功导入策略: {user_strategy.name}")
    print(f"   策略类型: {user_strategy.strategy_type.value}")
    print(f"   止损: {user_strategy.risk_management.stop_loss_pct}%")
    print(f"   止盈: {user_strategy.risk_management.take_profit_pct}%")
    
except Exception as e:
    print(f"❌ 导入失败: {e}")
```

### 方式2: 从API接收

```python
from fastapi import FastAPI, UploadFile, File

app = FastAPI()

@app.post("/api/strategy/upload")
async def upload_strategy(file: UploadFile = File(...)):
    """用户上传策略"""
    try:
        # 读取文件内容
        content = await file.read()
        json_str = content.decode('utf-8')
        
        # 解析策略
        strategy = TradingStrategy.from_json(json_str)
        
        # 验证策略
        if not strategy.validate_for_coin("BTC"):
            return {"error": "策略不适用于BTC"}
        
        # 添加到管理器
        manager = get_strategy_manager()
        manager.add_strategy(strategy)
        
        return {
            "success": True,
            "strategy_id": strategy.strategy_id,
            "name": strategy.name
        }
    
    except Exception as e:
        return {"error": str(e)}
```

## 🔍 策略查询和筛选

```python
# 查询所有波段策略
swing_strategies = manager.list_strategies(strategy_type=StrategyType.SWING)

# 查询适用于BTC的策略
btc_strategies = manager.get_strategy_for_coin_and_platform(
    coin="BTC",
    platform="hyperliquid"
)

# 按风险等级筛选
low_risk = [s for s in manager.list_strategies() 
            if s.risk_management.stop_loss_pct <= 3.0]

high_risk = [s for s in manager.list_strategies() 
             if s.risk_management.stop_loss_pct >= 5.0]
```

## 📈 策略性能追踪

```python
# 记录策略性能
strategy.performance_stats = {
    "total_trades": 100,
    "winning_trades": 65,
    "win_rate": 65.0,
    "total_pnl": 1250.50,
    "roi": 12.5,
    "max_drawdown": -3.2,
    "sharpe_ratio": 1.8,
    "last_updated": datetime.now().isoformat()
}

# 保存更新后的策略
strategy.save_to_file("strategy_with_performance.json")
```

## 🛠️ 命令行工具

创建策略管理CLI工具：

```bash
# strategy_cli.py
python strategy_cli.py list                    # 列出所有策略
python strategy_cli.py show aggressive_swing_v1  # 查看策略详情
python strategy_cli.py export aggressive_swing_v1 my_strategy.json  # 导出策略
python strategy_cli.py import user_strategy.json  # 导入策略
python strategy_cli.py validate my_strategy.json  # 验证策略
```

## 📝 最佳实践

### 1. 策略命名规范
- 使用描述性名称
- 包含版本号
- 使用小写和下划线

### 2. 风险管理建议
- 止损不超过 10%
- 风险回报比至少 1:1.5
- 最大仓位不超过总资金的 20%

### 3. 策略测试
- 先进行回测
- 小仓位实盘测试
- 记录性能数据
- 定期评估和调整

### 4. 版本管理
- 每次修改增加版本号
- 保留历史版本
- 记录修改日志

## 🔗 相关文档

- [Redis 持久化指南](./REDIS_PERSISTENCE_GUIDE.md)
- [AI 模型使用指南](./README.md)
- [多平台交易指南](./MULTI_PLATFORM_GUIDE.md)

---

**提示**: 策略是交易系统的核心，请仔细设计和测试您的策略！

