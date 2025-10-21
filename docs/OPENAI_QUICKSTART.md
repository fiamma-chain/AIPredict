# 🚀 OpenAI API Key 快速获取指南

## 📍 官方文档地址
```
https://platform.openai.com/docs/quickstart
https://platform.openai.com/api-keys
```

---

## ⚡ 5分钟快速获取

### 步骤 1：访问 OpenAI Platform
```
https://platform.openai.com/
```

### 步骤 2：注册/登录

**选项 A - 新用户注册**
1. 点击 "Sign up"
2. 选择注册方式：
   - Email
   - Google 账号
   - Microsoft 账号
   - Apple ID

**选项 B - 已有账号**
1. 点击 "Log in"
2. 使用你的 OpenAI 账号登录

### 步骤 3：完成账号设置

**重要：** 新账号需要完成以下步骤：

1. **验证邮箱**
   - 检查邮箱中的验证邮件
   - 点击链接完成验证

2. **验证手机号**（可能需要）
   - 输入手机号码
   - 接收并输入验证码
   - ⚠️ 需要海外手机号

### 步骤 4：设置付费（必需）

**2024 年政策：必须先充值才能使用**

1. 点击左侧菜单 **"Settings"** 或右上角设置图标

2. 选择 **"Billing"**

3. 点击 **"Add payment method"**

4. 填写信用卡信息：
   - 卡号
   - 到期日期
   - CVV
   - 账单地址

5. 设置充值：
   
   **方式 A：自动充值（推荐）**
   ```
   Automatic recharge:
   - Threshold: $5 (余额低于 $5 时充值)
   - Recharge amount: $20 (每次充值金额)
   ```
   
   **方式 B：手动充值**
   ```
   - 点击 "Add to credit balance"
   - 选择金额：$10 / $20 / $50 / 自定义
   - 建议首次充值：$20-30
   ```

### 步骤 5：创建 API Key

1. 点击左侧菜单 **"API keys"**
   
   或直接访问：
   ```
   https://platform.openai.com/api-keys
   ```

2. 点击右上角 **"+ Create new secret key"** 按钮

3. 配置 API Key：
   
   ```
   Name: AI Trading Arena (给密钥起个名字)
   
   Project: Default project (选择项目)
   
   Permissions: (选择权限)
   ┌─────────────────────────────────┐
   │ ○ All                           │  ← 全部权限（推荐）
   │ ● Restricted                    │  ← 限制权限
   │   ✓ Model capabilities          │
   │   ✓ Read                        │
   │   ✓ Write                       │
   └─────────────────────────────────┘
   ```
   
   **推荐选择：All** (除非你需要细粒度控制)

4. 点击 **"Create secret key"**

5. **⚠️ 重要：立即复制密钥！**
   
   ```
   sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   
   - 密钥只显示一次
   - 立即复制到安全的地方
   - 建议保存到密码管理器

6. 点击 **"Done"**

### 步骤 6：设置使用限制（强烈推荐）

1. 在 **"Settings"** → **"Limits"**

2. 设置月度预算：
   ```
   Monthly budget limit: $50
   
   Email threshold: $40 (80%)
   (当使用达到 $40 时发邮件提醒)
   ```

3. 保存设置

---

## ✅ 验证 API Key

### 使用 curl 测试

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Say hello in Chinese"}
    ],
    "max_tokens": 20
  }'
```

**预期响应：**
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "你好！"
      }
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 3,
    "total_tokens": 15
  }
}
```

### 使用 Python 测试

```python
import openai

# 设置 API Key
openai.api_key = "YOUR_API_KEY_HERE"

# 测试调用
response = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Say hello"}
    ],
    max_tokens=20
)

print(response.choices[0].message.content)
```

---

## 🎯 选择合适的模型

OpenAI 现在提供多个 GPT-4 系列模型：

| 模型 ID | 速度 | 成本 | Input价格 | Output价格 | 推荐用途 |
|---------|------|------|-----------|------------|----------|
| `gpt-4o-mini` | ⚡⚡⚡ | 💰 | $0.15/1M | $0.60/1M | **新手推荐** - 便宜快速 |
| `gpt-4o` | ⚡⚡ | 💰💰 | $5/1M | $15/1M | **推荐** - 平衡型 |
| `gpt-4-turbo` | ⚡ | 💰💰💰 | $10/1M | $30/1M | 高质量分析 |
| `gpt-4` | 🐌 | 💰💰💰💰 | $30/1M | $60/1M | 最高质量 |

### 我们系统推荐配置

**方案 1：省钱方案**
```bash
GPT_MODEL=gpt-4o-mini
```
每天成本：~$0.08

**方案 2：平衡方案（推荐）**
```bash
GPT_MODEL=gpt-4o
```
每天成本：~$2.38

**方案 3：高质量方案**
```bash
GPT_MODEL=gpt-4-turbo
```
每天成本：~$4.75

---

## 🔧 配置到我们的系统

### 1. 编辑配置文件
```bash
cd /Users/cyimon/Work/Dev/AITrading
nano .env
```

### 2. 添加配置
```bash
# OpenAI GPT-4 配置
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GPT_MODEL=gpt-4o

# 或使用更便宜的
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

### 4. 测试 API
```bash
python3 << 'EOF'
import asyncio
import httpx
from config.settings import settings

async def test():
    if not settings.openai_api_key:
        print("❌ 未配置 OpenAI API Key")
        return
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Say hello"}],
                    "max_tokens": 10
                }
            )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ OpenAI API 测试成功！")
            print(f"响应: {result['choices'][0]['message']['content']}")
            print(f"使用 tokens: {result['usage']['total_tokens']}")
        else:
            print(f"❌ API 调用失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 测试失败: {e}")

asyncio.run(test())
EOF
```

---

## ❌ 常见问题

### 问题 1：手机验证失败
**原因：** OpenAI 不支持某些地区的手机号

**解决方案：**
- 使用海外手机号（美国、欧洲、日本等）
- 或考虑使用 Claude/Gemini API（更容易获取）

### 问题 2：信用卡被拒绝
**可能原因：**
- 不支持国际支付
- 银行风控拦截
- 卡信息填写错误

**解决方案：**
1. 确认卡支持国际支付
2. 联系银行开通国际支付
3. 尝试其他信用卡
4. 使用虚拟信用卡（如 Visa/Mastercard 预付卡）

### 问题 3：充值后仍无法使用
**解决方案：**
1. 刷新页面
2. 等待 5-10 分钟（系统处理时间）
3. 检查 Billing 页面确认余额
4. 联系 OpenAI 支持

### 问题 4：API Key 无效
**检查清单：**
- [ ] 是否完整复制（包括 sk-proj- 前缀）
- [ ] 是否包含多余空格
- [ ] 账户是否已充值
- [ ] API Key 是否被删除或过期

### 问题 5：429 错误（速率限制）
**原因：** 新账户有较低的速率限制

**解决方案：**
```bash
# 增加我们系统的更新间隔
ARENA_UPDATE_INTERVAL=900  # 从10分钟改为15分钟
```

或充值更多金额以提高限制

### 问题 6：成本太高
**降低成本方案：**

```bash
# 1. 使用最便宜的模型
GPT_MODEL=gpt-4o-mini  # 便宜 97%

# 2. 增加更新间隔
ARENA_UPDATE_INTERVAL=1200  # 20分钟

# 3. 只交易一个币种
# 修改 arena/ai_arena.py:
self.trading_pairs = ["BTC"]

# 综合效果：$0.08/天 → $0.01/天
```

---

## 🌍 地区限制

### 支持的地区
✅ 美国、加拿大
✅ 欧洲大部分国家
✅ 日本、韩国、新加坡
✅ 澳大利亚、新西兰

### 不支持的地区
❌ 中国大陆
❌ 俄罗斯
❌ 部分中东国家

### 如果在不支持地区
**替代方案：**

1. **使用 Claude API**
   - 地区限制较少
   - 质量也很好
   - https://console.anthropic.com/

2. **使用 Gemini API**
   - 更容易获取
   - 有免费额度
   - https://aistudio.google.com/

3. **使用 API 代理服务**（谨慎）
   - API2D
   - OpenAI-SB
   - 需要评估可信度

---

## 💰 费用管理

### 查看使用情况
```
https://platform.openai.com/usage
```

可以看到：
- 每日使用量
- 成本统计
- 按模型分类
- 按 API Key 分类

### 设置预算提醒
在 Billing → Limits 设置：
- 软限制（发邮件）
- 硬限制（停止使用）

### 控制成本技巧
1. 使用 `max_tokens` 限制输出长度
2. 选择合适的模型（不一定用最贵的）
3. 缓存重复请求（我们的系统已实现）
4. 设置合理的更新间隔

---

## 📚 官方资源

- **文档**: https://platform.openai.com/docs
- **API 参考**: https://platform.openai.com/docs/api-reference
- **定价**: https://openai.com/api/pricing/
- **状态页**: https://status.openai.com/
- **社区论坛**: https://community.openai.com/

---

## ✅ 配置完成检查清单

- [ ] 已注册 OpenAI Platform 账号
- [ ] 已验证邮箱
- [ ] 已验证手机号（如需要）
- [ ] 已添加信用卡
- [ ] 已充值（至少 $5）
- [ ] 已创建 API Key
- [ ] 已保存 API Key
- [ ] 已设置使用限制
- [ ] 已测试 API Key
- [ ] 已配置到 .env 文件
- [ ] 已运行 verify_setup.py

全部完成？🎉 恭喜！可以开始使用了！

---

**需要帮助？**
- 查看官方文档: https://platform.openai.com/docs
- 运行验证脚本: `python3 verify_setup.py`
- 或考虑使用替代 AI: Claude / Gemini

