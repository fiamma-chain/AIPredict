# 系统架构文档

## 概述

AI Trading Arena 是一个模块化的加密货币交易竞技场系统，允许多个 AI 策略在真实市场中竞争。

## 架构设计

### 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│                  (Web UI + REST API)                     │
├─────────────────────────────────────────────────────────┤
│                    Application Layer                     │
│           (Trading Engine + Arena System)                │
├─────────────────────────────────────────────────────────┤
│                     Business Layer                       │
│        (Strategies + Performance + Leaderboard)          │
├─────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                   │
│         (Hyperliquid Client + Risk Manager)              │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. Trading Layer（交易层）

#### Hyperliquid Client (`trading/hyperliquid/client.py`)
- **职责**: 与 Hyperliquid 交易所通信
- **功能**:
  - 获取市场数据
  - 下单/撤单
  - 查询持仓和余额
  - 获取交易历史
- **特点**:
  - 异步 API 调用
  - 自动签名验证
  - 支持测试网/主网切换

#### Order Manager (`trading/order_manager.py`)
- **职责**: 管理订单生命周期
- **功能**:
  - 订单创建和提交
  - 订单状态追踪
  - 订单取消
  - 历史记录
- **数据结构**:
  ```python
  Order {
      order_id: str
      strategy_id: str
      coin: str
      side: OrderSide
      size: float
      price: float
      status: OrderStatus
  }
  ```

#### Risk Manager (`trading/risk_manager.py`)
- **职责**: 风险控制和资金管理
- **功能**:
  - 持仓风险检查
  - 止损/止盈执行
  - 日亏损限制
  - 仓位大小控制
- **风险规则**:
  - 最大持仓数量
  - 单仓位大小限制
  - 杠杆限制
  - 最小余额要求

### 2. Strategy Layer（策略层）

#### Base Strategy (`strategies/base.py`)
- **职责**: 策略接口定义
- **核心方法**:
  ```python
  async def analyze(coin, market_data) -> Signal
  def get_position_size(coin, signal, balance) -> float
  ```
- **状态管理**:
  - 持仓追踪
  - 交易统计
  - 性能指标

#### 内置策略

**Trend Following Strategy** (`strategies/trend_following.py`)
- 算法: 双均线交叉
- 指标: SMA(10), SMA(30)
- 适用: 趋势市场

**Mean Reversion Strategy** (`strategies/mean_reversion.py`)
- 算法: 布林带均值回归
- 指标: 均值 ± 2σ
- 适用: 震荡市场

**ML Strategy** (`strategies/ml_strategy.py`)
- 算法: 特征提取 + 规则决策
- 指标: RSI, 动量, 波动率, 成交量
- 适用: 多种市场环境

### 3. Arena System（竞技场系统）

#### Trading Engine (`arena/trading_engine.py`)
- **职责**: 协调所有组件运行
- **工作流程**:
  ```
  1. 获取市场数据
  2. 调用策略分析
  3. 生成交易信号
  4. 风险检查
  5. 执行订单
  6. 更新状态
  ```
- **并发处理**: 多策略并行运行

#### Performance Tracker (`arena/performance.py`)
- **职责**: 追踪策略性能
- **指标计算**:
  - 盈亏统计
  - 胜率计算
  - 夏普比率
  - 索提诺比率
  - 最大回撤
- **数据结构**:
  ```python
  PerformanceMetrics {
      total_pnl: float
      win_rate: float
      sharpe_ratio: float
      max_drawdown: float
      roi_percentage: float
  }
  ```

#### Leaderboard (`arena/leaderboard.py`)
- **职责**: 排行榜管理
- **排序指标**:
  - 总盈亏
  - ROI%
  - 胜率
  - 夏普比率
  - 盈亏比
- **时间周期**:
  - 全时段
  - 月度
  - 周度
  - 日度

### 4. API Layer（接口层）

#### REST API (`api/routes.py`)
- **端点分类**:
  - `/strategies/*` - 策略管理
  - `/leaderboard/*` - 排行榜
  - `/market/*` - 市场数据
  - `/risk/*` - 风险指标
  - `/engine/*` - 引擎状态

#### WebSocket (`/ws`)
- **功能**: 实时数据推送
- **推送内容**:
  - 排行榜更新
  - 策略性能
  - 风险指标
- **频率**: 5秒一次

## 数据流

### 交易执行流程

```
Market Data → Strategy.analyze() → Signal
                                      ↓
                            RiskManager.check()
                                      ↓
                              OrderManager.create()
                                      ↓
                          HyperliquidClient.place_order()
                                      ↓
                        PerformanceTracker.record_trade()
```

### 性能更新流程

```
Trade Closed → PerformanceTracker.record_trade()
                            ↓
                  Calculate Metrics
                            ↓
              Leaderboard.calculate_rankings()
                            ↓
                    API.broadcast_update()
                            ↓
                  WebSocket → Web UI
```

## 设计模式

### 1. Strategy Pattern（策略模式）
- 所有策略继承 `BaseStrategy`
- 统一接口，灵活扩展
- 便于添加新策略

### 2. Observer Pattern（观察者模式）
- WebSocket 客户端订阅数据更新
- 事件驱动的性能追踪

### 3. Facade Pattern（外观模式）
- Trading Engine 作为统一入口
- 隐藏底层复杂性

### 4. Repository Pattern（仓储模式）
- Performance Tracker 管理性能数据
- 分离数据访问逻辑

## 扩展点

### 添加新策略
```python
class CustomStrategy(BaseStrategy):
    async def analyze(self, coin, market_data):
        # 实现你的分析逻辑
        pass
```

### 添加新指标
```python
# 在 PerformanceMetrics 中添加
custom_metric: float = 0.0

# 在 _calculate_metrics 中计算
def _calculate_metrics(self):
    # 你的计算逻辑
    pass
```

### 添加新 API 端点
```python
@self.app.get("/custom/endpoint")
async def custom_endpoint():
    # 你的逻辑
    pass
```

## 性能优化

### 1. 异步 I/O
- 所有网络请求使用 async/await
- 并发处理多个策略
- 非阻塞订单执行

### 2. 数据缓存
- 市场数据缓存
- 排行榜计算缓存
- 减少重复计算

### 3. 批处理
- 批量更新订单状态
- 批量计算性能指标

## 安全考虑

### 1. 私钥管理
- 环境变量存储
- 不记录到日志
- 不通过 API 暴露

### 2. 风险控制
- 多层风险检查
- 强制止损/止盈
- 日亏损限制

### 3. API 安全
- CORS 配置
- 速率限制（待实现）
- 认证机制（待实现）

## 监控和日志

### 日志级别
- INFO: 正常操作
- WARNING: 风险警告
- ERROR: 错误情况

### 关键日志点
- 订单提交/成交
- 风险触发
- 策略信号
- 系统异常

## 部署架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Web UI     │────▶│  API Server │────▶│   Trading   │
│  (Browser)  │     │  (FastAPI)  │     │   Engine    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                     │
                           │                     ▼
                           │            ┌─────────────┐
                           │            │ Hyperliquid │
                           │            │   Exchange  │
                           │            └─────────────┘
                           ▼
                    ┌─────────────┐
                    │  Database   │
                    │ (PostgreSQL)│
                    └─────────────┘
```

## 未来改进

### 短期
- [ ] 添加数据库持久化
- [ ] 实现用户认证
- [ ] 添加更多技术指标

### 中期
- [ ] 回测框架
- [ ] 策略参数优化
- [ ] 移动端界面

### 长期
- [ ] 深度学习策略
- [ ] 多交易所支持
- [ ] 分布式部署

