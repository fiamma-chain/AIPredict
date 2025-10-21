# 🚨 主网部署指南

## ⚠️ 重要警告

**主网使用真实资金！请务必：**
1. ✅ 充分测试所有功能
2. ✅ 从小额资金开始（建议 $100-500）
3. ✅ 设置严格的风险限制
4. ✅ 密切监控系统运行
5. ✅ 准备好随时停止系统

## 📋 前置要求

### 1. Hyperliquid 主网账户
- 充值足够的 USDC（建议起始 $500-1000）
- 导出私钥（MetaMask → 账户详情 → 导出私钥）

### 2. AI API 密钥

#### Claude API (推荐)
- 访问: https://console.anthropic.com/
- 价格: ~$3/1M input tokens, ~$15/1M output tokens
- 申请 API 密钥并充值（建议 $20-50）

#### OpenAI GPT-4 API
- 访问: https://platform.openai.com/api-keys
- 价格: ~$10/1M input tokens, ~$30/1M output tokens
- 创建 API 密钥并充值

#### Google Gemini API
- 访问: https://ai.google.dev/
- 价格: 前 1M tokens 免费，之后 ~$0.5-7/1M tokens
- 获取 API 密钥

## 🔧 配置步骤

### 1. 更新 .env 文件

```bash
cd /Users/cyimon/Work/Dev/AITrading
nano .env
```

配置内容：

```bash
# ==========================================
# 主网配置
# ==========================================

# Hyperliquid 主网配置
HYPERLIQUID_PRIVATE_KEY=你的主网私钥
HYPERLIQUID_TESTNET=false  # ⚠️ 改为 false 启用主网
HYPERLIQUID_API_URL=https://api.hyperliquid.xyz

# ==========================================
# AI API 密钥（至少配置一个）
# ==========================================

# Claude API (推荐 - 最稳定)
CLAUDE_API_KEY=sk-ant-api03-xxx...
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# OpenAI GPT-4 API
OPENAI_API_KEY=sk-xxx...
GPT_MODEL=gpt-4-turbo-preview

# Google Gemini API
GEMINI_API_KEY=xxx...
GEMINI_MODEL=gemini-pro

# ==========================================
# AI 交易配置（保守设置）
# ==========================================

# 每个 AI 的起始资金（虚拟分配）
AI_INITIAL_BALANCE=300
# 每个 AI 的最大单笔仓位
AI_MAX_POSITION_SIZE=100

# 竞技场更新间隔（秒）
# 主网建议 300-600 秒（5-10分钟）避免频繁调用 API
ARENA_UPDATE_INTERVAL=600

# ==========================================
# 风险管理（严格限制）
# ==========================================

# 最大单仓位大小（USD）
MAX_POSITION_SIZE=300
# 最大杠杆倍数（建议 1-3）
MAX_LEVERAGE=2
# 止损百分比
STOP_LOSS_PERCENTAGE=3.0
# 止盈百分比
TAKE_PROFIT_PERCENTAGE=5.0

# 每日最大亏损限制（USD）
DAILY_LOSS_LIMIT=150
# 最大同时持仓数量
MAX_OPEN_POSITIONS=3
# 最小账户余额要求（USD）
MIN_ACCOUNT_BALANCE=200

# API 服务配置
API_HOST=0.0.0.0
API_PORT=8000
```

### 2. 验证配置

```bash
# 检查私钥是否正确
python3 << 'EOF'
from eth_account import Account
from config.settings import settings

if settings.hyperliquid_private_key:
    account = Account.from_key(settings.hyperliquid_private_key)
    print(f"✅ 钱包地址: {account.address}")
    print(f"⚠️  主网模式: {not settings.hyperliquid_testnet}")
else:
    print("❌ 未配置私钥")
EOF
```

### 3. 测试 AI API 连接

```bash
python3 << 'EOF'
import asyncio
from config.settings import settings

async def test_apis():
    print("测试 AI API 连接...\n")
    
    # 测试 Claude
    if settings.claude_api_key:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.claude_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-3-5-sonnet-20241022",
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Hi"}]
                    }
                )
            print(f"✅ Claude API: {response.status_code}")
        except Exception as e:
            print(f"❌ Claude API: {e}")
    
    # 测试 OpenAI
    if settings.openai_api_key:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-turbo-preview",
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 10
                    }
                )
            print(f"✅ OpenAI API: {response.status_code}")
        except Exception as e:
            print(f"❌ OpenAI API: {e}")

asyncio.run(test_apis())
EOF
```

## 🚀 启动主网 AI 竞技场

### 1. 停止演示服务器

```bash
pkill -f demo_ai_arena
lsof -ti:8000 | xargs kill -9 2>/dev/null
```

### 2. 启动主网竞技场

```bash
# 直接运行（前台，可看到实时日志）
python3 ai_arena_main.py

# 或后台运行
nohup python3 ai_arena_main.py > mainnet_arena.log 2>&1 &

# 查看日志
tail -f mainnet_arena.log
```

### 3. 监控系统

访问 Web 界面：
```bash
open web/ai_arena.html
```

或访问 API：
```bash
# 查看状态
curl http://localhost:8000/arena/status | python3 -m json.tool

# 查看排行榜
curl http://localhost:8000/leaderboard | python3 -m json.tool

# 查看 AI 模型
curl http://localhost:8000/ai-models | python3 -m json.tool
```

## 📊 预期成本

### AI API 调用成本（每天）

假设配置：
- 3 个 AI 模型
- 3 个交易对（BTC, ETH, SOL）
- 10 分钟更新一次

每天调用次数：
```
(60分钟 / 10分钟) × 24小时 × 3个AI × 3个币种 = 1,296 次/天
```

成本估算：
- **Claude**: ~$0.003/次 = ~$3.89/天
- **GPT-4**: ~$0.01/次 = ~$12.96/天
- **Gemini**: ~$0.001/次 = ~$1.30/天

**总计**: ~$18/天（3个AI都开启）

💡 **节省成本建议**：
1. 增加更新间隔（10-15分钟）
2. 减少交易对数量
3. 只运行 1-2 个 AI 模型
4. 优先使用 Gemini（最便宜）

## 🛡️ 风险控制建议

### 保守型配置（推荐新手）
```bash
AI_INITIAL_BALANCE=200
AI_MAX_POSITION_SIZE=80
MAX_POSITION_SIZE=200
MAX_LEVERAGE=1
DAILY_LOSS_LIMIT=100
ARENA_UPDATE_INTERVAL=900  # 15分钟
```

### 平衡型配置
```bash
AI_INITIAL_BALANCE=300
AI_MAX_POSITION_SIZE=150
MAX_POSITION_SIZE=300
MAX_LEVERAGE=2
DAILY_LOSS_LIMIT=150
ARENA_UPDATE_INTERVAL=600  # 10分钟
```

### 激进型配置（谨慎！）
```bash
AI_INITIAL_BALANCE=500
AI_MAX_POSITION_SIZE=250
MAX_POSITION_SIZE=500
MAX_LEVERAGE=3
DAILY_LOSS_LIMIT=250
ARENA_UPDATE_INTERVAL=300  # 5分钟
```

## 🔔 监控和告警

### 1. 实时监控脚本

创建 `monitor.sh`:
```bash
#!/bin/bash
while true; do
    clear
    echo "=== AI Trading Arena 监控 ==="
    echo ""
    curl -s http://localhost:8000/leaderboard/summary | python3 -m json.tool
    echo ""
    echo "按 Ctrl+C 退出"
    sleep 30
done
```

```bash
chmod +x monitor.sh
./monitor.sh
```

### 2. 重要日志关键词

监控这些关键词：
```bash
# 错误和警告
tail -f mainnet_arena.log | grep -E "ERROR|WARNING|风险"

# 交易执行
tail -f mainnet_arena.log | grep -E "开仓|平仓|订单"

# AI 决策
tail -f mainnet_arena.log | grep "🤖"
```

## 🚨 紧急停止

### 快速停止系统

```bash
# 方法1：找到进程并停止
pkill -f ai_arena_main

# 方法2：如果知道进程ID
kill -SIGINT <PID>

# 方法3：强制停止
pkill -9 -f ai_arena_main
```

### 平仓所有持仓

```bash
python3 << 'EOF'
import asyncio
from config.settings import settings
from trading.hyperliquid.client import HyperliquidClient

async def close_all():
    client = HyperliquidClient(
        private_key=settings.hyperliquid_private_key,
        testnet=settings.hyperliquid_testnet
    )
    
    async with client:
        positions = await client.get_positions()
        for pos in positions:
            coin = pos['position']['coin']
            print(f"平仓: {coin}")
            await client.close_position(coin)
        print("所有仓位已平仓")

asyncio.run(close_all())
EOF
```

## 📈 最佳实践

1. **分阶段部署**
   - 第1周：小额测试（$100-200）
   - 第2周：评估表现，调整参数
   - 第3周+：根据结果决定是否增加资金

2. **定期检查**
   - 每天查看排行榜和盈亏
   - 每周分析 AI 决策质量
   - 每月评估整体 ROI

3. **参数调优**
   - 记录不同配置的表现
   - 逐步优化风险参数
   - 测试不同的更新间隔

4. **止损纪律**
   - 设定总资金止损线（如 -20%）
   - 单个 AI 表现差就暂停
   - 市场异常时及时停止

## 📞 获取帮助

如果遇到问题：
1. 查看日志: `tail -f mainnet_arena.log`
2. 检查 API: `curl http://localhost:8000/health`
3. 验证余额: 访问 Hyperliquid 网页端

---

**祝交易顺利！记住：谨慎为上，风险自负！** 🚀💰

