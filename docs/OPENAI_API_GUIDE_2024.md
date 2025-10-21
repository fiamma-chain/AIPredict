# 🟢 OpenAI GPT-4 API 获取指南（2024年最新版）

## 📋 2024年最新流程

### 方式一：通过 OpenAI Platform（推荐）

#### 1. 访问 OpenAI Platform
```
https://platform.openai.com/
```

#### 2. 注册/登录
**重要更新**：
- ⚠️ OpenAI Platform 账号和 ChatGPT 账号现在是**分开**的
- 需要单独注册 OpenAI Platform 账号
- 或使用已有的 OpenAI 账号登录

注册选项：
- Email 注册
- Google 账号
- Microsoft 账号
- Apple 账号

#### 3. 验证手机号
OpenAI 现在要求验证手机号：
- 输入你的手机号码
- 接收验证码
- 输入验证码完成验证

**支持的地区**：
- ✅ 美国、英国、欧洲大部分国家
- ✅ 日本、韩国、新加坡
- ⚠️ 中国大陆手机号可能不支持（需要使用海外手机号）

#### 4. 设置计费（必需）

**2024年新政策**：
- 新用户需要**先充值才能使用** GPT-4
- 最低充值：**$5**
- 不再有免费试用额度

步骤：
1. 登录后点击左侧 **"Settings"**
2. 点击 **"Billing"**
3. 点击 **"Add payment method"**
4. 添加信用卡信息
5. 选择充值金额（建议 $20-50）

支持的支付方式：
- ✅ Visa/Mastercard/American Express
- ✅ 借记卡
- ❌ PayPal（大部分地区不支持）

#### 5. 创建 API Key

**2024年新界面**：

1. 点击左侧菜单 **"API keys"**（或 "Dashboard" → "API keys"）

2. 点击右上角 **"+ Create new secret key"**

3. 填写信息：
   ```
   Name: AI Trading Arena
   Project: Default project (或创建新项目)
   Permissions: All (或只选 Model capabilities)
   ```

4. 点击 **"Create secret key"**

5. **⚠️ 立即复制密钥！只显示一次！**
   ```
   sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   
   注意：新格式以 `sk-proj-` 开头

6. 保存到安全的地方（如密码管理器）

#### 6. 设置使用限制（强烈推荐）

**2024年新功能 - 更细致的控制**：

1. 在 **"Settings"** → **"Limits"**

2. 设置月度支出限额：
   ```
   Monthly budget: $50
   Email notification at: $40
   ```

3. 设置速率限制（可选）：
   ```
   Rate limits: Custom
   TPM (Tokens per minute): 90000
   RPM (Requests per minute): 3500
   ```

#### 7. 选择合适的模型

**2024年可用的 GPT-4 模型**：

| 模型 | 速度 | 成本 | 推荐用途 |
|------|------|------|----------|
| `gpt-4-turbo` | 快 | 中 | **推荐** - 平衡型 |
| `gpt-4-turbo-preview` | 快 | 中 | 最新功能预览 |
| `gpt-4` | 慢 | 高 | 最高质量 |
| `gpt-4-32k` | 慢 | 很高 | 长文本 |
| `gpt-4o` | 很快 | 中 | **新推荐** - 多模态 |
| `gpt-4o-mini` | 最快 | 低 | 便宜快速 |

**我们系统推荐使用**：
```python
# 在 .env 文件中
GPT_MODEL=gpt-4-turbo
# 或
GPT_MODEL=gpt-4o  # 如果想要更快速度
```

---

## 💰 2024年最新定价

### GPT-4 Turbo
```
Input:  $10 / 1M tokens
Output: $30 / 1M tokens
```

### GPT-4o (推荐)
```
Input:  $5 / 1M tokens
Output: $15 / 1M tokens
```

### GPT-4o Mini (最便宜)
```
Input:  $0.15 / 1M tokens
Output: $0.60 / 1M tokens
```

### 预估成本（我们的系统）

使用 `gpt-4-turbo`：
```
每次分析: ~500 tokens input + 200 tokens output
成本: $0.005 + $0.006 = $0.011/次

每天调用（10分钟间隔）:
144 次/天 × 3个币种 = 432 次
总成本: ~$4.75/天
```

使用 `gpt-4o`（更便宜）：
```
成本: $0.0025 + $0.003 = $0.0055/次
每天: ~$2.38/天
```

使用 `gpt-4o-mini`（最便宜）：
```
成本: $0.000075 + $0.00012 = $0.000195/次
每天: ~$0.08/天
```

---

## 🌍 地区限制和解决方案

### 不支持的地区

如果你在中国大陆或其他受限地区：

#### 方案 1：使用海外手机号
- 可以购买海外虚拟号码服务
- 或请海外朋友帮忙验证

#### 方案 2：使用 API 代理服务
一些第三方服务提供 OpenAI API 代理：
- API2D (https://api2d.com/)
- OpenAI-SB (https://openai-sb.com/)
- **注意**：需要评估可信度和成本

#### 方案 3：使用替代模型
如果无法获取 OpenAI API，可以：
- ✅ 使用 Claude API（Anthropic）
- ✅ 使用 Gemini API（Google）
- 这两个模型质量也很好，且可能更容易获取

---

## ✅ 验证 API Key

### 方法 1：使用 curl
```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4-turbo",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 10
  }'
```

成功响应：
```json
{
  "choices": [
    {
      "message": {
        "content": "Hello! How can I assist you today?"
      }
    }
  ]
}
```

### 方法 2：使用我们的验证脚本
```bash
cd /Users/cyimon/Work/Dev/AITrading

python3 << 'EOF'
import asyncio
import httpx

async def test_openai():
    api_key = input("输入你的 OpenAI API Key: ")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4-turbo",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 10
                }
            )
        
        if response.status_code == 200:
            print("✅ API Key 有效！")
            print(f"响应: {response.json()['choices'][0]['message']['content']}")
        else:
            print(f"❌ 错误: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 测试失败: {e}")

asyncio.run(test_openai())
EOF
```

---

## 🛠️ 配置到我们的系统

### 1. 编辑配置文件
```bash
nano .env
```

### 2. 添加 API Key
```bash
# OpenAI 配置
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GPT_MODEL=gpt-4-turbo

# 或使用更便宜的模型
# GPT_MODEL=gpt-4o
# GPT_MODEL=gpt-4o-mini
```

### 3. 验证配置
```bash
python3 verify_setup.py
```

应该看到：
```
3️⃣  检查 AI API 配置...
   ✅ OpenAI API 已配置
```

---

## ❌ 常见问题

### 问题 1：手机号验证失败
**解决方案**：
- 尝试使用海外手机号
- 或使用替代 AI 模型（Claude/Gemini）

### 问题 2：信用卡被拒绝
**解决方案**：
- 确认卡支持国际支付
- 尝试其他信用卡
- 联系银行确认是否被拦截

### 问题 3：API Key 无效
**解决方案**：
- 检查是否完整复制（包括 `sk-proj-` 前缀）
- 确认账户已充值
- 检查 API Key 权限设置

### 问题 4：429 错误（速率限制）
**解决方案**：
- 新账户有较低的速率限制
- 充值更多金额可提高限制
- 或增加我们系统的更新间隔

### 问题 5：成本太高
**解决方案**：
```bash
# 方案 1: 使用更便宜的模型
GPT_MODEL=gpt-4o-mini

# 方案 2: 增加更新间隔
ARENA_UPDATE_INTERVAL=900  # 15分钟

# 方案 3: 减少交易对
# 修改 arena/ai_arena.py
self.trading_pairs = ["BTC"]  # 只交易一个
```

---

## 🔄 2024年的主要变化

### 相比 2023年的变化：
1. ❌ **取消免费额度** - 必须先充值
2. ✅ **新增 GPT-4o** - 更快更便宜
3. ✅ **新增 GPT-4o-mini** - 超便宜选项
4. 🔄 **API Key 格式变化** - 现在以 `sk-proj-` 开头
5. 🔄 **更严格的地区限制** - 需要手机验证
6. ✅ **更好的用量控制** - 可设置详细限制

---

## 💡 推荐配置

### 如果你是新用户
```bash
# 使用 GPT-4o-mini（最便宜）
OPENAI_API_KEY=sk-proj-xxx
GPT_MODEL=gpt-4o-mini
ARENA_UPDATE_INTERVAL=600
```
**成本**: ~$0.08/天

### 如果你想要平衡
```bash
# 使用 GPT-4o（平衡）
OPENAI_API_KEY=sk-proj-xxx
GPT_MODEL=gpt-4o
ARENA_UPDATE_INTERVAL=600
```
**成本**: ~$2.38/天

### 如果你想要最佳质量
```bash
# 使用 GPT-4-turbo（高质量）
OPENAI_API_KEY=sk-proj-xxx
GPT_MODEL=gpt-4-turbo
ARENA_UPDATE_INTERVAL=600
```
**成本**: ~$4.75/天

---

## 🎯 总结

**2024年获取 OpenAI API 的关键步骤**：
1. ✅ 注册 OpenAI Platform 账号
2. ✅ 验证手机号（海外号码）
3. ✅ 添加信用卡并充值（最低$5）
4. ✅ 创建 API Key（格式：sk-proj-xxx）
5. ✅ 设置使用限制（避免超支）
6. ✅ 选择合适的模型（推荐 gpt-4o）

**如果遇到困难**：
- 考虑使用 Claude API（可能更容易获取）
- 或使用 Gemini API（有免费额度）

需要更多帮助？运行：
```bash
python3 verify_setup.py
```

祝配置顺利！🚀

