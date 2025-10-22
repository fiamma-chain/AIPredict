# 🚀 快速开始指南

## ✅ 已完成的工作

恭喜！系统已经完全配置好，可以开始使用了：

1. ✅ Aster 客户端实现完成（基于官方 API 文档）
2. ✅ 多平台交易架构实现完成
3. ✅ 依赖安装完成
4. ✅ 连接测试通过（已验证可以正常连接 AsterDex）

## 📋 下一步操作

### 方案 A：快速测试（推荐新手）

**1. 创建 API Wallet**

访问 https://www.asterdex.com/en/api-wallet
- 点击右上角切换到 `Pro API`
- 创建新的 API Wallet (AGENT)
- **保存以下信息**：
  - User Address（主钱包地址）
  - Signer Address（API Wallet 地址）
  - Private Key（API Wallet 私钥）⚠️ **不是主钱包私钥！**

**2. 测试私有 API**

编辑 `test_aster_connection.py`，将私钥填入：
```python
TEST_PRIVATE_KEY = "0x你的API_Wallet私钥"
```

运行测试：
```bash
python3 test_aster_connection.py
```

如果看到账户余额和历史成交，说明配置成功！

### 方案 B：运行完整交易系统

**1. 复制配置文件**

```bash
cp env.example.txt .env
```

**2. 编辑 .env 文件**

```bash
# 选择启用的平台
ENABLED_PLATFORMS=aster
# 或同时启用两个平台对比: ENABLED_PLATFORMS=hyperliquid,aster

# Aster 配置
ASTER_TESTNET=False
ASTER_API_URL=https://fapi.asterdex.com

# Alpha 组配置（使用你的 API Wallet 私钥）
GROUP_1_NAME=Alpha组
GROUP_1_PRIVATE_KEY=0x你的API_Wallet私钥
GROUP_1_TESTNET=False

# Beta 组配置（如果有第二个 API Wallet）
GROUP_2_NAME=Beta组
GROUP_2_PRIVATE_KEY=0x另一个API_Wallet私钥
GROUP_2_TESTNET=False

# AI API Keys（至少需要 3 个）
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
QWEN_API_KEY=...
GROK_API_KEY=...
DEEPSEEK_API_KEY=...

# 交易配置
ALLOWED_TRADING_SYMBOLS=BTC
AI_INITIAL_BALANCE=1000.0
CONSENSUS_MIN_VOTES=2
CONSENSUS_INTERVAL=300
MIN_CONFIDENCE=60.0
```

**3. 运行系统**

```bash
# 运行多平台版本
python3 consensus_arena_multiplatform.py

# 或者只运行 Hyperliquid（如果你还没准备好 Aster）
ENABLED_PLATFORMS=hyperliquid python3 consensus_arena.py
```

## 📊 测试结果

已验证以下功能正常工作：
- ✅ 获取市场数据
- ✅ 获取订单簿
- ✅ 获取最近成交
- ✅ 获取 K 线数据

待测试（需要 API Wallet）：
- ⏳ 账户信息查询
- ⏳ 下单功能
- ⏳ 撤单功能
- ⏳ 持仓管理

## 🎯 预期效果

### 单平台模式

```
🤖 AI共识交易系统 - 多平台对比版
============================================================
启用的交易平台: aster
交易币种: BTC
⏱️  决策周期: 5分钟
🎯 共识规则: 每组至少2个AI同意才执行
============================================================

[Alpha组] 📊 平台收益对比:
  Alpha组-Aster: 余额=$1050.00, 盈亏=$+50.00, ROI=+5.00%, 胜率=60.0%
```

### 多平台对比模式

```
启用的交易平台: hyperliquid, aster

[Alpha组] 📊 平台收益对比:
  Alpha组-Hyperliquid: 余额=$1050.00, 盈亏=$+50.00, ROI=+5.00%, 胜率=60.0%
  Alpha组-Aster: 余额=$1080.00, 盈亏=$+80.00, ROI=+8.00%, 胜率=65.0%
```

## 📚 相关文档

- **`ASTER_SETUP_GUIDE.md`** - Aster 详细配置指南
- **`MULTI_PLATFORM_GUIDE.md`** - 多平台功能说明
- **`UPDATE_SUMMARY.md`** - 技术实现细节
- **`test_aster_connection.py`** - 连接测试脚本

## ⚠️ 重要提示

### 关于 API Wallet

1. **API Wallet ≠ 主钱包**
   - API Wallet 是专门用于 API 访问的子账户
   - 使用 API Wallet 的私钥，不是主钱包私钥
   - API Wallet 有交易权限但无提现权限（更安全）

2. **创建 API Wallet**
   - 必须在 https://www.asterdex.com/en/api-wallet 创建
   - 切换到顶部的 `Pro API` 标签
   - 保存好 Private Key（无法再次查看）

### 安全建议

1. **小额测试**
   - AsterDex 没有测试网
   - 建议先用小额资金测试
   - 确认系统稳定后再加大资金

2. **私钥安全**
   - 不要将私钥提交到 Git
   - 使用 `.env` 文件（已在 .gitignore 中）
   - 定期更换 API Wallet

3. **风险控制**
   - 设置合理的每日亏损限制
   - 使用止损止盈
   - 监控交易日志

### 费率说明

- **Maker 费率**: 约 0.02%
- **Taker 费率**: 约 0.05%
- 具体费率以实际交易为准

## 🔧 故障排除

### 问题 1: 签名验证失败

**解决方案**：
1. 确认使用的是 API Wallet 的私钥
2. 检查 API Wallet 是否正确创建
3. 确认系统时间准确（`sudo sntp -sS time.apple.com`）

### 问题 2: 余额不足

**解决方案**：
1. 确认资金在合约账户（不是现货账户）
2. 检查是否有足够的 USDT
3. 考虑保证金和手续费

### 问题 3: 无法获取账户信息

**解决方案**：
1. 运行 `python3 test_aster_connection.py` 验证连接
2. 检查网络连接
3. 确认 API Wallet 有账户访问权限

### 问题 4: 依赖安装失败

**解决方案**：
```bash
# 升级 pip
python3 -m pip install --upgrade pip

# 重新安装依赖
python3 -m pip install -r requirements.txt
```

## 📞 获取帮助

1. **查看日志**：所有操作都有详细日志
2. **查看文档**：`ASTER_SETUP_GUIDE.md` 有详细说明
3. **运行测试**：`python3 test_aster_connection.py`
4. **AsterDex 社区**：访问官方 Discord

## ✨ 功能特性

- ✅ 统一接口设计
- ✅ 多平台同时交易
- ✅ 实时收益对比
- ✅ AI 共识决策
- ✅ 风险管理
- ✅ 完整的交易日志
- ✅ Web 界面监控

## 🎊 开始交易

一切就绪！根据你的需求选择：

**选项 1**：只在 Aster 上交易
```bash
ENABLED_PLATFORMS=aster python3 consensus_arena_multiplatform.py
```

**选项 2**：在 Hyperliquid 和 Aster 上对比交易
```bash
ENABLED_PLATFORMS=hyperliquid,aster python3 consensus_arena_multiplatform.py
```

**选项 3**：先测试连接
```bash
python3 test_aster_connection.py
```

祝交易顺利！📈

