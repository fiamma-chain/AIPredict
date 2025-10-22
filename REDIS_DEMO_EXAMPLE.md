# Redis 持久化使用演示

## 🎬 完整使用流程演示

### 步骤 1: 安装 Redis

```bash
# 方式 1: 使用自动化脚本（推荐）
./setup_redis.sh

# 方式 2: 手动安装（macOS）
brew install redis
brew services start redis

# 验证安装
redis-cli ping
# 输出: PONG ✅
```

### 步骤 2: 配置环境变量

创建 `.env` 文件（如果没有，复制 `env.example.txt`）:

```bash
cp env.example.txt .env
```

编辑 `.env` 文件，确保 Redis 配置正确：

```env
# Redis 配置
REDIS_ENABLED=True
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### 步骤 3: 启动系统

```bash
python consensus_arena_multiplatform.py
```

**预期输出：**

```
================================
🤖 AI共识交易系统 - 多平台对比版
================================
🔄 正在初始化 Redis 持久化...
✅ Redis 连接成功: localhost:6379/0
🔥 Redis 管理器初始化成功
✅ Redis 持久化已启用
启用的交易平台: hyperliquid, aster
交易币种: BTC
⏱️  决策周期: 5分钟
🎯 共识规则: 每组至少2个AI同意才执行
每组初始资金: $1000.0
================================

📊 初始化 Alpha 组 (DeepSeek + Claude + Grok)...
[Alpha组] 启用的交易平台: ['hyperliquid', 'aster']
[DeepSeek] ✅ Redis 持久化已启用
[Claude] ✅ Redis 持久化已启用
[Grok] ✅ Redis 持久化已启用
✅ 添加交易平台: Alpha组-Hyperliquid
✅ 添加交易平台: Alpha组-Aster
[Alpha组-Hyperliquid] 初始余额: $1,000.00
[Alpha组-Aster] 初始余额: $1,000.00
✅ Alpha组初始化完成

📊 初始化 Beta 组 (GPT-4 + Gemini + Qwen)...
[Beta组] 启用的交易平台: ['hyperliquid', 'aster']
[GPT] ✅ Redis 持久化已启用
[Gemini] ✅ Redis 持久化已启用
[Qwen] ✅ Redis 持久化已启用
✅ 添加交易平台: Beta组-Hyperliquid
✅ 添加交易平台: Beta组-Aster
[Beta组-Hyperliquid] 初始余额: $1,000.00
[Beta组-Aster] 初始余额: $1,000.00
✅ Beta组初始化完成

🚀 系统初始化完成！
🚀 共识交易系统已启动
```

### 步骤 4: 观察 AI 决策和持久化

系统运行时，每次 AI 做出决策，都会：
1. 在控制台显示决策
2. 保存到内存（最近 100 条）
3. **自动保存到 Redis**（永久保存）

**控制台输出示例：**

```
================================================================================
🤖 共识决策循环 #1 - 2025-10-22 10:30:45
================================================================================
💰 BTC 价格: $67,234.50
📈 24h涨跌: +2.34%

────────────────────────────────────────────────────────────────────────────────
📊 Alpha组 开始共识决策
────────────────────────────────────────────────────────────────────────────────
[Alpha组] 🚀 开始并行调用 3 个AI模型...
[Alpha组] 🤖 正在获取 DeepSeek (hyperliquid) 的决策...
[Alpha组] 🤖 正在获取 Claude (hyperliquid) 的决策...
[Alpha组] 🤖 正在获取 Grok (hyperliquid) 的决策...
[Alpha组]    DeepSeek (hyperliquid): BUY (信心: 72.0%)
[DeepSeek] 已保存响应到 Redis: BTC buy ✅
[Alpha组]    Claude (hyperliquid): BUY (信心: 68.5%)
[Claude] 已保存响应到 Redis: BTC buy ✅
[Alpha组]    Grok (hyperliquid): HOLD (信心: 45.0%)
[Grok] 已保存响应到 Redis: BTC hold ✅
[Alpha组] 📊 共识结果: 看涨 (2/3票, 平均信心70.3%)
投票详情: 看涨2票, 看跌0票, 观望1票
[Alpha组] ✅ 达成共识！将执行: 看涨 (BUY)
```

### 步骤 5: 实时查询数据

在系统运行的同时，打开新终端查询数据：

```bash
# 查看整体统计
./redis_query_tool.py stats
```

**输出：**

```
📊 Redis 数据统计
============================================================

总键数: 12
总响应数: 36

平台分布:
  • hyperliquid: 18 条
  • aster: 18 条

AI 模型分布:
  • DeepSeek: 6 条
  • Claude: 6 条
  • Grok: 6 条
  • GPT: 6 条
  • Gemini: 6 条
  • Qwen: 6 条

币种分布:
  • BTC: 36 条
============================================================
```

### 步骤 6: 查询特定 AI 的决策历史

```bash
# 查询 DeepSeek 在 Hyperliquid 上的决策
./redis_query_tool.py query hyperliquid DeepSeek BTC --limit 5
```

**输出：**

```
🔍 查询: hyperliquid - DeepSeek - BTC
============================================================
总记录数: 6

显示最近 5 条记录:

[1] ============================================================
时间: 2025-10-22T10:30:45.123456
平台: hyperliquid
模型: DeepSeek
币种: BTC
决策: buy
信心: 72.0%
理由: 价格突破关键阻力位，买盘强劲，建议做多
============================================================

[2] ============================================================
时间: 2025-10-22T10:25:30.654321
平台: hyperliquid
模型: DeepSeek
币种: BTC
决策: hold
信心: 55.5%
理由: 市场震荡，等待更明确信号
============================================================

...
```

### 步骤 7: 导出数据进行分析

```bash
# 导出 Claude 的所有决策到 JSON 文件
./redis_query_tool.py export hyperliquid Claude BTC --output claude_decisions.json --limit 100
```

**输出：**

```
📤 导出: hyperliquid - Claude - BTC
============================================================
✅ 已导出 6 条记录到 claude_decisions.json
============================================================
```

**查看导出的文件：**

```bash
cat claude_decisions.json
```

```json
{
  "platform": "hyperliquid",
  "ai_model": "Claude",
  "coin": "BTC",
  "export_time": "2025-10-22T10:35:00.000000",
  "total_records": 6,
  "responses": [
    {
      "timestamp": "2025-10-22T10:30:45.234567",
      "platform": "hyperliquid",
      "ai_model": "Claude",
      "coin": "BTC",
      "decision": "buy",
      "confidence": 68.5,
      "reasoning": "技术指标显示上涨趋势，RSI处于健康区间",
      "raw_response": "DECISION: BUY\nCONFIDENCE: 68.5\nREASONING: ..."
    },
    ...
  ]
}
```

### 步骤 8: 测试持久化（系统重启）

```bash
# 1. 停止系统（Ctrl+C）
^C
🛑 共识交易系统正在停止...
🔄 正在关闭 Redis 连接...
Redis 连接已关闭
✅ 共识交易系统已停止

# 2. 验证数据仍然存在
./redis_query_tool.py stats

📊 Redis 数据统计
============================================================
总键数: 12
总响应数: 36  # 数据依然存在 ✅
...

# 3. 重启系统
python consensus_arena_multiplatform.py

# 4. 查询历史数据（证明持久化成功）
./redis_query_tool.py query hyperliquid DeepSeek BTC --limit 10
# 可以看到重启前的所有历史决策 ✅
```

### 步骤 9: 进行数据分析

使用 Python 脚本分析导出的数据：

```python
import json
import pandas as pd

# 读取导出的数据
with open('claude_decisions.json', 'r') as f:
    data = json.load(f)

# 转换为 DataFrame
df = pd.DataFrame(data['responses'])

# 分析决策分布
print("决策分布:")
print(df['decision'].value_counts())

# 分析平均信心度
print(f"\n平均信心度: {df['confidence'].mean():.2f}%")

# 按时间排序
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp')

# 可视化（可选）
import matplotlib.pyplot as plt
df['confidence'].plot(title='Claude 信心度趋势')
plt.show()
```

### 步骤 10: 监控和维护

```bash
# 监控 Redis 内存使用
watch -n 5 'redis-cli INFO memory | grep used_memory_human'

# 监控数据增长
watch -n 10 './redis_query_tool.py stats'

# 定期备份（手动）
redis-cli SAVE
cp /var/lib/redis/dump.rdb /backup/redis-backup-$(date +%Y%m%d).rdb

# 清理旧数据（可选）
./redis_query_tool.py clear --platform hyperliquid --ai-model Grok
```

## 🎯 实际应用场景

### 场景 1: AI 决策质量分析

```bash
# 导出所有 AI 的决策
for ai in DeepSeek Claude Grok GPT Gemini Qwen; do
    ./redis_query_tool.py export hyperliquid $ai BTC --output "${ai}_decisions.json"
done

# 使用 Python 分析哪个 AI 的决策最准确
# 对比决策时的价格和后续价格变化
```

### 场景 2: 平台对比分析

```bash
# 导出同一个 AI 在不同平台的决策
./redis_query_tool.py export hyperliquid DeepSeek BTC --output deepseek_hyperliquid.json
./redis_query_tool.py export aster DeepSeek BTC --output deepseek_aster.json

# 对比两个平台的决策差异（理论上应该相同）
```

### 场景 3: 时间序列分析

```python
# 分析 AI 决策的时间模式
import json
import pandas as pd
from datetime import datetime

# 加载数据
with open('claude_decisions.json', 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data['responses'])
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hour'] = df['timestamp'].dt.hour

# 分析每小时的决策分布
hourly_decisions = df.groupby(['hour', 'decision']).size()
print(hourly_decisions)
```

### 场景 4: 共识分析

```bash
# 导出所有 AI 的决策
for ai in DeepSeek Claude Grok; do
    ./redis_query_tool.py export hyperliquid $ai BTC --output "alpha_${ai}.json" --limit 1000
done

# 分析哪些时间点达成了共识
# 对比共识决策和非共识决策的成功率
```

## 📊 数据统计示例

运行一周后的数据规模：

```bash
./redis_query_tool.py stats
```

```
📊 Redis 数据统计
============================================================

总键数: 12
总响应数: 8,064  # 一周约 8000 条决策

平台分布:
  • hyperliquid: 4,032 条
  • aster: 4,032 条

AI 模型分布:
  • DeepSeek: 1,344 条  # 每个 AI 每周约 1300 条
  • Claude: 1,344 条
  • Grok: 1,344 条
  • GPT: 1,344 条
  • Gemini: 1,344 条
  • Qwen: 1,344 条

币种分布:
  • BTC: 8,064 条
============================================================

内存使用: ~8-16 MB
磁盘使用: ~10-20 MB (含 AOF)
```

## 💡 最佳实践

1. **定期监控**: 每天检查一次数据统计
2. **定期备份**: 每周备份一次 Redis 数据
3. **数据分析**: 每周导出数据进行深度分析
4. **性能优化**: 根据需要调整保留的记录数量
5. **文档记录**: 记录重要的决策时刻

## 🎓 进阶使用

### 创建自定义查询脚本

```python
# custom_query.py
from utils.redis_manager import RedisManager
from config.settings import settings

# 连接 Redis
redis_mgr = RedisManager(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db
)
redis_mgr.connect()

# 查询所有 AI 的最新决策
platforms = redis_mgr.get_all_platforms()
models = redis_mgr.get_all_ai_models()
coins = redis_mgr.get_all_coins()

for platform in platforms:
    for model in models:
        for coin in coins:
            responses = redis_mgr.get_ai_responses(platform, model, coin, limit=1)
            if responses:
                latest = responses[0]
                print(f"{platform} - {model} - {coin}: {latest['decision']} ({latest['confidence']}%)")

redis_mgr.disconnect()
```

### 实时监控脚本

```bash
# monitor.sh
#!/bin/bash
while true; do
    clear
    echo "=== AI 决策实时监控 ==="
    date
    echo ""
    ./redis_query_tool.py stats
    echo ""
    echo "最新决策："
    ./redis_query_tool.py query hyperliquid DeepSeek BTC --limit 1
    sleep 10
done
```

## 🏆 成功验证清单

- [x] Redis 成功安装和启动
- [x] 系统启动时显示 "Redis 持久化已启用"
- [x] 每个 AI 模型显示 "Redis 持久化已启用"
- [x] 决策后显示 "已保存响应到 Redis"
- [x] `redis_query_tool.py stats` 显示数据统计
- [x] 能够查询历史决策
- [x] 能够导出数据到 JSON
- [x] 系统重启后数据仍然存在
- [x] 内存使用在合理范围内

## 🎉 完成！

恭喜！您已经成功配置并使用了 Redis 持久化功能。现在所有 AI 决策都会：

✅ 自动保存到 Redis  
✅ 按平台和 AI 模型分类  
✅ 系统重启后不会丢失  
✅ 可以随时查询和分析  
✅ 支持导出和备份  

---

**更多帮助**: 查看 [REDIS_PERSISTENCE_GUIDE.md](./REDIS_PERSISTENCE_GUIDE.md)

