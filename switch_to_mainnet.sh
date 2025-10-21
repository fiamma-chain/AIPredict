#!/bin/bash

echo "=================================="
echo "🚨 切换到 Hyperliquid 主网"
echo "=================================="
echo ""
echo "⚠️  警告：主网使用真实资金！"
echo ""
read -p "你确定要继续吗？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "已取消"
    exit 1
fi

echo ""
echo "请输入你的配置..."
echo ""

# 获取 Hyperliquid 私钥
read -p "Hyperliquid 主网私钥: " PRIVATE_KEY
echo ""

# 获取 AI API 密钥
read -p "Claude API Key (可选，直接回车跳过): " CLAUDE_KEY
read -p "OpenAI API Key (可选，直接回车跳过): " OPENAI_KEY
read -p "Gemini API Key (可选，直接回车跳过): " GEMINI_KEY

echo ""
echo "生成 .env 文件..."

cat > .env << EOF
# Hyperliquid 主网配置
HYPERLIQUID_PRIVATE_KEY=$PRIVATE_KEY
HYPERLIQUID_TESTNET=false
HYPERLIQUID_API_URL=https://api.hyperliquid.xyz

# AI API 密钥
CLAUDE_API_KEY=$CLAUDE_KEY
CLAUDE_MODEL=claude-3-5-sonnet-20241022
OPENAI_API_KEY=$OPENAI_KEY
GPT_MODEL=gpt-4-turbo-preview
GEMINI_API_KEY=$GEMINI_KEY
GEMINI_MODEL=gemini-pro

# AI 交易配置（保守设置）
AI_INITIAL_BALANCE=300
AI_MAX_POSITION_SIZE=100
ARENA_UPDATE_INTERVAL=600

# 风险管理
MAX_POSITION_SIZE=300
MAX_LEVERAGE=2
STOP_LOSS_PERCENTAGE=3.0
TAKE_PROFIT_PERCENTAGE=5.0
DAILY_LOSS_LIMIT=150
MAX_OPEN_POSITIONS=3
MIN_ACCOUNT_BALANCE=200

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
EOF

echo "✅ 配置文件已更新"
echo ""
echo "请阅读 MAINNET_SETUP.md 了解详细说明"
echo ""
echo "启动命令: python3 ai_arena_main.py"
