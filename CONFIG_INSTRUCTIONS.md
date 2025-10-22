# 📝 配置说明 - 完整步骤

## 当前状态

根据配置检查，你需要配置：
1. ✅ 平台设置 - 已配置（hyperliquid, aster）
2. ❌ API Wallet 私钥 - **需要配置**
3. ❌ AI API Keys - **需要配置至少3个**

---

## 🔑 步骤 1: 获取 API Wallet 私钥

### 1.1 创建 AsterDex API Wallet

1. 访问 https://www.asterdex.com/en/api-wallet
2. 登录你的 AsterDex 账户
3. 点击页面**顶部**的 `Pro API` 标签（重要！）
4. 点击 "Create New API Wallet" 按钮
5. 系统会显示：
   - **User Address**: 你的主钱包地址
   - **Signer Address**: API Wallet 地址
   - **Private Key**: API Wallet 私钥 ⚠️ **只显示一次，务必保存！**

### 1.2 保存私钥

```
示例私钥格式：
0x4fd0a42218f3eae43a6ce26d22544e986139a01e5b34a62db53757ffca81bae1
```

⚠️ **重要**：这是 API Wallet 的私钥，不是你的主钱包私钥！

---

## 🤖 步骤 2: 获取 AI API Keys

你需要至少 **3 个** AI API Key。推荐配置：

### 2.1 Claude (Anthropic)

1. 访问 https://console.anthropic.com/
2. 注册/登录账户
3. 进入 API Keys 页面
4. 创建新的 API Key
5. 复制保存（格式：`sk-ant-api03-...`）

**费用**: 
- 免费额度: $5
- 按使用量计费
- Claude 3.5 Sonnet 性能最佳

### 2.2 OpenAI (ChatGPT)

1. 访问 https://platform.openai.com/api-keys
2. 注册/登录账户
3. 创建新的 API Key
4. 复制保存（格式：`sk-proj-...`）

**费用**:
- 按使用量计费
- GPT-4o 推荐
- 可设置使用限额

### 2.3 其他 AI（选择其中一个）

**选项 A: Google Gemini (免费)**
1. 访问 https://makersuite.google.com/app/apikey
2. 创建 API Key
3. 格式：`AIzaSy...`
4. 免费额度充足

**选项 B: DeepSeek (便宜)**
1. 访问 https://platform.deepseek.com/
2. 注册并创建 API Key
3. 非常便宜，性能不错

**选项 C: Qwen (阿里云)**
1. 访问阿里云百炼平台
2. 创建 API Key
3. 国内访问快

**选项 D: Grok (X.AI)**
1. 需要 X Premium 账户
2. 访问 https://x.ai/api
3. 创建 API Key

---

## ⚙️ 步骤 3: 编辑 .env 文件

### 3.1 打开文件

```bash
# macOS/Linux
nano .env

# 或使用你喜欢的编辑器
code .env  # VS Code
vim .env   # Vim
```

### 3.2 填写配置

找到以下行并填入你的信息：

```bash
# ==========================================
# 必填配置
# ==========================================

# Alpha 组 API Wallet 私钥
GROUP_1_PRIVATE_KEY=0x你的API_Wallet私钥
# 例如：GROUP_1_PRIVATE_KEY=0x4fd0a42218f3eae43a6ce26d22544e986139a01e5b34a62db53757ffca81bae1

# AI API Keys (至少填3个)
CLAUDE_API_KEY=sk-ant-api03-你的Claude_Key
OPENAI_API_KEY=sk-proj-你的OpenAI_Key
GEMINI_API_KEY=AIzaSy你的Gemini_Key

# ==========================================
# 可选配置（已有默认值，可不改）
# ==========================================

# 启用的平台（已配置）
ENABLED_PLATFORMS=hyperliquid,aster

# 交易币种（已配置）
ALLOWED_TRADING_SYMBOLS=BTC

# 共识规则（已配置）
CONSENSUS_MIN_VOTES=2
MIN_CONFIDENCE=60.0

# 初始资金（可调整）
AI_INITIAL_BALANCE=1000.0

# 决策间隔（秒）
CONSENSUS_INTERVAL=300
```

### 3.3 保存文件

- **nano**: 按 `Ctrl+X`，然后 `Y`，然后 `Enter`
- **VS Code**: `Cmd+S` (Mac) 或 `Ctrl+S` (Windows)
- **vim**: 按 `Esc`，输入 `:wq`，按 `Enter`

---

## ✅ 步骤 4: 验证配置

运行配置检查：

```bash
python3 setup_and_run.py
```

应该看到：
- ✅ API Wallet 私钥已配置
- ✅ AI API Keys 充足（至少3个）
- ✅ 系统已就绪

---

## 🚀 步骤 5: 启动系统

### 5.1 方式 A: 使用启动脚本（推荐）

```bash
python3 setup_and_run.py
```

脚本会：
1. 检查配置
2. 显示当前设置
3. 询问确认
4. 启动系统

### 5.2 方式 B: 直接启动

```bash
python3 consensus_arena_multiplatform.py
```

### 5.3 测试连接（推荐先做）

在正式运行前，建议先测试连接：

```bash
# 编辑测试脚本，填入 API Wallet 私钥
nano test_aster_connection.py

# 运行测试
python3 test_aster_connection.py
```

---

## 📊 预期输出

系统启动后会看到：

```
🤖 AI共识交易系统 - 多平台对比版
============================================================
启用的交易平台: hyperliquid, aster
交易币种: BTC
⏱️  决策周期: 5分钟
🎯 共识规则: 每组至少2个AI同意才执行
============================================================

📊 初始化 Alpha 组 (DeepSeek + Claude + Grok)...
✅ Aster 客户端初始化成功
   User地址: 0x你的地址
   Signer地址: 0x你的Signer
   
✅ Hyperliquid 客户端初始化成功
   地址: 0x你的地址
   
🚀 系统初始化完成！

💰 BTC 价格: $107,477.20
📈 24h涨跌: -0.94%

[Alpha组] 🚀 开始并行调用 3 个AI模型...
[Alpha组]    DeepSeek: BUY (信心: 85.0%)
[Alpha组]    Claude: BUY (信心: 80.0%)
[Alpha组]    Grok: HOLD (信心: 55.0%)
[Alpha组] 📊 共识结果: 看涨 (2/3票, 平均信心82.5%)
[Alpha组] ✅ 达成共识！将执行: 看涨 (BUY)
```

---

## ⚠️ 常见问题

### Q1: 如果只有 2 个 AI API Key 怎么办？

**答**: 系统需要至少 3 个 AI 进行共识投票。建议：
- 使用 Gemini（免费且稳定）
- 或降低 `CONSENSUS_MIN_VOTES` 为 1（不推荐）

### Q2: API Wallet 和主钱包有什么区别？

**答**:
- **主钱包**: 持有你的资金，有完全控制权
- **API Wallet**: 只有交易权限，无提现权限（更安全）
- **必须使用 API Wallet 的私钥**，不是主钱包私钥！

### Q3: 没有 Hyperliquid 账户怎么办？

**答**: 可以只启用 Aster：
```bash
ENABLED_PLATFORMS=aster
```

### Q4: 如何停止系统？

**答**: 按 `Ctrl+C` 即可优雅停止

### Q5: 费用大概多少？

**答**: AI API 调用费用：
- Claude: ~$0.02 每次决策
- OpenAI: ~$0.03 每次决策
- Gemini: 免费额度充足
- 每 5 分钟决策一次，每天约 $5-10

交易费用：
- AsterDex: ~0.05% Taker 费率
- Hyperliquid: ~0.025% Taker 费率

---

## 📞 获取帮助

### 遇到问题？

1. **查看日志**: 系统会输出详细日志
2. **测试连接**: `python3 test_aster_connection.py`
3. **检查配置**: `python3 setup_and_run.py`
4. **查看文档**: 
   - `QUICK_START.md`
   - `ASTER_SETUP_GUIDE.md`
   - `MULTI_PLATFORM_GUIDE.md`

### 常用命令

```bash
# 检查配置
python3 setup_and_run.py

# 测试连接
python3 test_aster_connection.py

# 启动系统
python3 consensus_arena_multiplatform.py

# 查看日志（另一个终端）
tail -f *.log
```

---

## ✨ 配置完成检查清单

在启动前，确认以下项目：

- [ ] ✅ 已创建 AsterDex API Wallet
- [ ] ✅ 已保存 API Wallet 私钥
- [ ] ✅ 已获取至少 3 个 AI API Key
- [ ] ✅ 已编辑 .env 文件填入所有配置
- [ ] ✅ 已运行 `python3 setup_and_run.py` 验证配置
- [ ] ✅ （可选）已运行 `python3 test_aster_connection.py` 测试连接
- [ ] ✅ 已充值 USDT 到 AsterDex 合约账户
- [ ] ✅ 已了解交易风险

全部完成？开始交易吧！🚀

```bash
python3 setup_and_run.py
```

祝交易顺利！📈

