# 🚀 主网快速启动指南

## 📋 准备清单

在开始前，你需要：

### ✅ 必需项
1. **Hyperliquid 主网账户** 
   - 地址有足够的 USDC（建议 $500-1000）
   - 导出的私钥

2. **至少一个 AI API 密钥**
   - Claude API（推荐）
   - 或 OpenAI GPT-4 API
   - 或 Google Gemini API

### 📝 可选项
- 多个 AI API（让不同 AI 竞争）
- 更多资金（在确认系统稳定后）

---

## 🔑 步骤 1：获取 AI API 密钥

### 选项 A：Claude API（推荐 - 最稳定）

1. 访问 https://console.anthropic.com/
2. 注册/登录账号
3. 点击 "Get API Keys"
4. 创建新的 API Key
5. 充值账户（建议 $20-50）

**成本**: ~$3-5/天（每10分钟更新）

### 选项 B：OpenAI GPT-4 API

1. 访问 https://platform.openai.com/api-keys
2. 登录 OpenAI 账号
3. 创建新的 API Key
4. 充值账户

**成本**: ~$10-15/天（每10分钟更新）

### 选项 C：Google Gemini API（最便宜）

1. 访问 https://ai.google.dev/
2. 获取 Google Cloud API 密钥
3. 启用 Gemini API

**成本**: ~$1-2/天（前期有免费额度）

---

## 🔧 步骤 2：配置系统

### 方式一：使用配置脚本（推荐）

```bash
cd /Users/cyimon/Work/Dev/AITrading
./switch_to_mainnet.sh
```

按提示输入：
- Hyperliquid 主网私钥
- AI API 密钥（至少一个）

### 方式二：手动编辑配置

```bash
nano .env
```

修改以下内容：

```bash
# 1. 切换到主网
HYPERLIQUID_TESTNET=false

# 2. 配置主网私钥
HYPERLIQUID_PRIVATE_KEY=你的主网私钥

# 3. 配置 AI API（至少一个）
CLAUDE_API_KEY=sk-ant-xxx...
# 或
OPENAI_API_KEY=sk-xxx...
# 或
GEMINI_API_KEY=xxx...
```

---

## ✅ 步骤 3：验证配置

```bash
python3 verify_setup.py
```

确保看到：
```
✅ 所有检查通过！
🚀 可以启动系统
```

---

## 🚀 步骤 4：启动主网竞技场

### 停止演示服务器

```bash
pkill -f demo_ai_arena
lsof -ti:8000 | xargs kill -9 2>/dev/null
```

### 启动真实 AI 竞技场

```bash
# 前台运行（推荐第一次，可看到实时日志）
python3 ai_arena_main.py

# 或后台运行
nohup python3 ai_arena_main.py > mainnet.log 2>&1 &

# 查看日志
tail -f mainnet.log
```

你会看到类似输出：

```
================================================================================
🤖 AI Trading Arena - AI 模型竞技场
================================================================================

✅ 已连接到 Hyperliquid (主网)
📍 钱包地址: 0x...
💰 账户余额: $1,234.56
💵 可用余额: $1,234.56

🤖 注册 AI 模型...
✅ AI 模型已注册: Claude (Sonnet)
✅ AI 模型已注册: GPT-4 (Turbo)

================================================================================
🏟️  竞技场配置
================================================================================
参赛 AI: 2 个
交易对: BTC, ETH, SOL
初始资金: $300.00 / AI
最大仓位: $100.00
更新间隔: 600 秒
================================================================================

🚀 AI 竞技场启动！共有 2 个 AI 参赛
============================================================
🏟️  开始新的竞技场周期
============================================================
```

---

## 📊 步骤 5：监控系统

### 打开 Web 界面

```bash
open web/ai_arena.html
```

### 实时监控命令

```bash
# 查看排行榜
curl -s http://localhost:8000/leaderboard | python3 -m json.tool

# 查看 AI 状态
curl -s http://localhost:8000/ai-models | python3 -m json.tool

# 监控实时日志
tail -f mainnet.log | grep -E "🤖|📈|📉|⚠️"
```

---

## 🎯 预期行为

系统启动后，每隔 10 分钟：

1. **获取市场数据**
   ```
   从 Hyperliquid 获取 BTC、ETH、SOL 的实时数据
   ```

2. **AI 分析**
   ```
   🤖 Claude (Sonnet) | BTC | 决策: buy | 置信度: 75.3% | 
   理由: 订单簿买盘深度较强，资金费率为正表明多头情绪高涨...
   ```

3. **执行交易**
   ```
   📈 开仓成功 [Claude (Sonnet)] BTC: 0.0015 @ $67,234.56
   ```

4. **更新排行榜**
   ```
   🏆 AI 模型排行榜
   #1 Claude (Sonnet)    $1,156.78    +$156.78    +15.68%    5    80.0%
   #2 GPT-4 (Turbo)      $1,089.23    +$89.23     +8.92%     8    62.5%
   ```

---

## ⚠️ 重要提醒

### 🚨 风险警告
- ✅ 这是真实资金交易！
- ✅ AI 可能做出不理智的决策
- ✅ 市场波动可能导致亏损
- ✅ 密切监控系统运行

### 💡 最佳实践

1. **第一周**
   - 小额测试（$100-300）
   - 每天检查 2-3 次
   - 记录 AI 的决策质量

2. **观察期**
   - 如果 7 天内亏损 > 20%，停止并分析
   - 如果表现稳定，可以继续
   - 调整风险参数

3. **优化阶段**
   - 根据表现调整配置
   - 可以增加资金（谨慎！）
   - 测试不同的更新间隔

---

## 🛑 如何停止

### 正常停止

```bash
# 找到进程
ps aux | grep ai_arena_main

# 停止进程（替换 <PID>）
kill -SIGINT <PID>

# 或直接
pkill -f ai_arena_main
```

### 紧急平仓

```bash
python3 << 'EOF'
import asyncio
from config.settings import settings
from trading.hyperliquid.client import HyperliquidClient

async def emergency_close():
    client = HyperliquidClient(
        private_key=settings.hyperliquid_private_key,
        testnet=False  # 主网
    )
    
    async with client:
        positions = await client.get_positions()
        for pos in positions:
            coin = pos['position']['coin']
            print(f"平仓: {coin}")
            await client.close_position(coin)
        print("✅ 所有仓位已平仓")

asyncio.run(emergency_close())
EOF
```

---

## 💰 成本控制

### 降低 API 成本

```bash
# 增加更新间隔到 15 分钟
ARENA_UPDATE_INTERVAL=900

# 只运行一个 AI
# 注释掉不需要的 API Key

# 减少交易对
# 在 arena/ai_arena.py 中修改:
self.trading_pairs = ["BTC"]  # 只交易 BTC
```

### 成本估算工具

```python
# 计算每日成本
update_interval = 600  # 秒
ai_count = 2  # AI 数量
pairs_count = 3  # 交易对数量

calls_per_day = (86400 / update_interval) * ai_count * pairs_count
cost_per_call = 0.003  # Claude 平均成本

daily_cost = calls_per_day * cost_per_call
print(f"预计每日成本: ${daily_cost:.2f}")
```

---

## 📞 故障排查

### 问题：API 调用失败
```bash
# 检查 API 密钥
python3 verify_setup.py

# 查看详细错误
tail -f mainnet.log | grep ERROR
```

### 问题：没有交易
```bash
# 检查账户余额
python3 << 'EOF'
import asyncio
from config.settings import settings
from trading.hyperliquid.client import HyperliquidClient

async def check():
    client = HyperliquidClient(
        private_key=settings.hyperliquid_private_key,
        testnet=False
    )
    async with client:
        balance = await client.get_balance()
        print(f"余额: ${balance['available_balance']}")

asyncio.run(check())
EOF
```

### 问题：持仓卡住
```bash
# 手动平仓
curl -X POST http://localhost:8000/emergency/close-all
```

---

## ✅ 完成！

现在你已经成功部署了主网 AI Trading Arena！

**记住**：
- 🔍 定期检查排行榜
- 📊 分析 AI 决策质量
- 💰 控制风险，谨慎为上
- 🚀 享受 AI 竞技的乐趣

**祝交易顺利！** 🤖💰📈

