# 🔑 AI API Key 申请完整指南

## 目录
- [Claude API (Anthropic)](#claude-api-anthropic) - 推荐，最稳定
- [OpenAI GPT-4 API](#openai-gpt-4-api) - 最知名
- [Google Gemini API](#google-gemini-api) - 最便宜，有免费额度

---

## 📘 Claude API (Anthropic)

### ⭐ 推荐理由
- ✅ 响应稳定可靠
- ✅ 分析质量高
- ✅ API 调用速度快
- ✅ 成本适中（~$3-5/天）

### 📋 申请步骤

#### 1. 访问 Anthropic 官网
```
https://console.anthropic.com/
```

#### 2. 注册账号
- 点击右上角 **"Sign Up"**
- 可以使用 Google 账号快速注册
- 或使用邮箱注册

#### 3. 验证邮箱
- 检查邮箱收到的验证邮件
- 点击链接完成验证

#### 4. 进入控制台
登录后你会看到：
```
Console Dashboard
├── API Keys          ← 这里创建密钥
├── Usage
├── Settings
└── Billing
```

#### 5. 创建 API Key
1. 点击左侧菜单 **"API Keys"**
2. 点击 **"Create Key"** 按钮
3. 给密钥起个名字（如：AITrading）
4. 点击 **"Create Key"**
5. **⚠️ 立即复制密钥！只会显示一次！**

示例密钥格式：
```
sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 6. 充值账户
1. 点击左侧 **"Billing"**
2. 点击 **"Add Credits"**
3. 建议充值：**$20-50**
4. 支持信用卡支付

#### 7. 设置用量限制（可选但推荐）
1. 在 Billing 页面
2. 设置 **Monthly Budget Limit**
3. 建议设置：$50/月
4. 避免意外超支

### 💰 价格（2024年）
```
Claude 3.5 Sonnet:
- Input:  $3 / 1M tokens
- Output: $15 / 1M tokens

预估成本：
- 每次 AI 分析: ~$0.003
- 每天 (10分钟间隔): ~$4.32
```

### ✅ 测试 API Key
```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: YOUR_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 10,
    "messages": [{"role": "user", "content": "Hi"}]
  }'
```

---

## 🟢 OpenAI GPT-4 API

### ⭐ 特点
- ✅ 最知名的 AI 模型
- ✅ 强大的分析能力
- ⚠️ 成本较高（~$10-15/天）
- ⚠️ 有时响应较慢

### 📋 申请步骤

#### 1. 访问 OpenAI 平台
```
https://platform.openai.com/
```

#### 2. 注册/登录
- 如果有 ChatGPT 账号，可以直接登录
- 没有的话点击 **"Sign up"** 注册
- 支持 Google/Microsoft 账号登录

#### 3. 进入 API 页面
登录后会看到：
```
Platform Dashboard
├── API keys          ← 创建密钥
├── Usage
├── Billing
└── Settings
```

#### 4. 创建 API Key
1. 点击左侧 **"API keys"**
2. 点击 **"Create new secret key"**
3. 输入名称（如：AI Trading Arena）
4. 选择权限：**All** (或只选择 Models)
5. 点击 **"Create secret key"**
6. **⚠️ 立即复制并保存！只显示一次！**

示例密钥格式：
```
sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 5. 充值账户
1. 点击 **"Billing"** → **"Add payment method"**
2. 添加信用卡
3. 设置自动充值（建议）：
   - Threshold: $5（余额低于$5时充值）
   - Amount: $20（每次充值金额）

或一次性充值：
1. 点击 **"Add to credit balance"**
2. 建议充值：**$30-50**

#### 6. 启用 GPT-4 访问
- 新账号可能需要充值 $5 后才能访问 GPT-4
- 充值后立即可用

#### 7. 设置用量限制
1. 点击 **"Billing"** → **"Usage limits"**
2. 设置 **Hard limit**: $50/月
3. 设置 **Soft limit**: $40/月（会发邮件提醒）

### 💰 价格（2024年）
```
GPT-4 Turbo:
- Input:  $10 / 1M tokens
- Output: $30 / 1M tokens

预估成本：
- 每次 AI 分析: ~$0.01
- 每天 (10分钟间隔): ~$14.40
```

### ✅ 测试 API Key
```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-turbo-preview",
    "messages": [{"role": "user", "content": "Hi"}],
    "max_tokens": 10
  }'
```

---

## 🔵 Google Gemini API

### ⭐ 特点
- ✅ **最便宜**（有免费额度）
- ✅ 响应速度快
- ✅ 适合高频调用
- ⚠️ 分析质量略低于 Claude/GPT-4

### 📋 申请步骤

#### 1. 访问 Google AI Studio
```
https://aistudio.google.com/
```

或 Google Cloud Console:
```
https://console.cloud.google.com/
```

#### 2. 登录 Google 账号
- 使用你的 Gmail 账号登录
- 首次使用需要同意服务条款

#### 3. 创建 API Key (AI Studio 方式 - 最简单)

**方法 A：通过 AI Studio（推荐新手）**

1. 访问 https://aistudio.google.com/app/apikey
2. 点击 **"Create API Key"**
3. 选择或创建一个 Google Cloud 项目
4. 点击 **"Create API Key in new project"**
5. **立即复制密钥！**

示例密钥格式：
```
AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**方法 B：通过 Google Cloud Console（完整设置）**

1. 创建新项目
   - 点击顶部项目下拉菜单
   - 点击 **"New Project"**
   - 输入项目名称（如：AI Trading）
   - 点击 **"Create"**

2. 启用 Gemini API
   - 在搜索栏搜索 **"Generative Language API"**
   - 点击 **"Enable"**

3. 创建凭据
   - 左侧菜单点击 **"Credentials"**
   - 点击 **"Create Credentials"**
   - 选择 **"API Key"**
   - 复制生成的密钥

4. 限制 API Key（推荐）
   - 点击刚创建的密钥
   - **Application restrictions**: None 或设置 IP
   - **API restrictions**: 限制到 Generative Language API
   - 保存

#### 4. 设置配额和计费

**免费额度（2024年）：**
```
Gemini 1.0 Pro:
- 免费: 60 requests/分钟
- 免费: 1,500 requests/天
```

如果需要更多：
1. 在 Google Cloud Console 启用计费
2. 添加信用卡
3. 升级到付费计划

#### 5. 设置预算提醒
1. 在 Cloud Console 点击 **"Billing"**
2. 点击 **"Budgets & alerts"**
3. 创建新预算
4. 设置：$50/月
5. 设置提醒阈值：50%, 90%, 100%

### 💰 价格（2024年）
```
Gemini Pro:
- 免费额度: 前 60 requests/分钟
- 付费后:
  - Input:  $0.50 / 1M characters
  - Output: $1.50 / 1M characters

预估成本：
- 每次 AI 分析: ~$0.001
- 每天 (10分钟间隔): ~$1.44
- **或完全免费（如果在免费额度内）**
```

### ✅ 测试 API Key
```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [{"text": "Hi"}]
    }]
  }'
```

---

## 🎯 推荐配置方案

### 方案 A：预算有限（推荐新手）
```
✅ Gemini API（免费额度）
💰 成本: $0-2/天
```

### 方案 B：平衡型
```
✅ Claude API
💰 成本: ~$4/天
```

### 方案 C：多 AI 竞技（推荐）
```
✅ Claude API +
✅ Gemini API
💰 成本: ~$5-6/天
```

### 方案 D：完整对比
```
✅ Claude API +
✅ OpenAI GPT-4 API +
✅ Gemini API
💰 成本: ~$16-20/天
```

---

## 📝 申请后的配置步骤

### 1. 保存 API Key
创建一个安全的地方保存你的密钥：
```bash
# 不要提交到 git！
# 只保存在本地 .env 文件中
```

### 2. 更新 .env 文件
```bash
cd /Users/cyimon/Work/Dev/AITrading
nano .env
```

添加你的密钥：
```bash
# 如果申请了 Claude
CLAUDE_API_KEY=sk-ant-api03-xxxxx

# 如果申请了 OpenAI
OPENAI_API_KEY=sk-xxxxx

# 如果申请了 Gemini
GEMINI_API_KEY=AIzaSyxxxxx
```

### 3. 验证配置
```bash
python3 verify_setup.py
```

应该看到：
```
3️⃣  检查 AI API 配置...
   ✅ Claude API 已配置
   ✅ OpenAI API 已配置
   ✅ Gemini API 已配置
```

---

## ⚠️ 安全提示

### ❌ 不要做的事
- ❌ 不要分享你的 API Key
- ❌ 不要提交到 GitHub
- ❌ 不要在公共场所展示
- ❌ 不要用于未授权用途

### ✅ 应该做的事
- ✅ 保存在本地 .env 文件
- ✅ 设置用量限制
- ✅ 定期检查使用情况
- ✅ 不用时可以删除密钥

### 🔒 如果密钥泄露
1. 立即在控制台删除该密钥
2. 创建新密钥
3. 检查账单是否有异常

---

## 💡 省钱技巧

### 1. 增加更新间隔
```bash
# 从 5 分钟改为 15 分钟
ARENA_UPDATE_INTERVAL=900
```
**节省**: ~66% 成本

### 2. 减少交易对
```bash
# 只交易 BTC
# 在 arena/ai_arena.py 修改
self.trading_pairs = ["BTC"]
```
**节省**: ~66% 成本（如果原来是3个）

### 3. 只运行一个 AI
```bash
# 只配置一个 API Key
CLAUDE_API_KEY=xxxxx
OPENAI_API_KEY=
GEMINI_API_KEY=
```
**节省**: ~66% 成本（如果原来是3个）

### 4. 优先使用 Gemini
```bash
# Gemini 最便宜且有免费额度
GEMINI_API_KEY=xxxxx
```
**节省**: ~75-90% 成本

---

## 📞 遇到问题？

### Claude 相关
- 官方文档: https://docs.anthropic.com/
- 状态页面: https://status.anthropic.com/

### OpenAI 相关
- 官方文档: https://platform.openai.com/docs
- 状态页面: https://status.openai.com/

### Gemini 相关
- 官方文档: https://ai.google.dev/docs
- 状态页面: https://status.cloud.google.com/

---

**祝申请顺利！🚀**

申请完成后，运行 `python3 verify_setup.py` 验证配置即可开始使用！

