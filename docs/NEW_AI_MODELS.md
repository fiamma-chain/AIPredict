# 🆕 新增 AI 模型配置指南

系统现已支持 **6 个 AI 模型**同时竞争！

## 📋 支持的 AI 模型

| AI 模型 | 提供商 | 优势 | 成本估算 |
|---------|--------|------|----------|
| Claude | Anthropic | 推理能力强 | ~$4/天 |
| GPT-4 | OpenAI | 最知名 | ~$2-5/天 |
| Gemini | Google | 免费额度 | ~$0-2/天 |
| **Qwen** | 阿里云 | 中文优化 | ~$1-3/天 |
| **Grok** | xAI | 实时数据 | ~$3-5/天 |
| **DeepSeek** | DeepSeek | 性价比高 | ~$0.5-2/天 |

## 🔑 获取新 AI 模型的 API Key

### 1. Qwen (通义千问)

#### 获取步骤：
1. 访问阿里云DashScope
   ```
   https://dashscope.console.aliyun.com/
   ```

2. 登录/注册阿里云账号

3. 开通 DashScope 服务
   - 点击"开通服务"
   - 完成实名认证（中国大陆用户）

4. 创建 API Key
   - 进入"API-KEY管理"
   - 点击"创建新的API-KEY"
   - 复制密钥

5. 充值（可选）
   - 新用户有免费额度
   - 可按需充值

#### 模型选择：
- `qwen-turbo` - 快速便宜
- `qwen-plus` - 平衡
- `qwen-max` - **推荐** 最强

#### 成本：
```
输入: ¥0.004/1K tokens
输出: ¥0.012/1K tokens
每天约: ¥5-10 (~$1-2)
```

---

### 2. Grok (xAI)

#### 获取步骤：
1. 访问 xAI 控制台
   ```
   https://console.x.ai/
   ```

2. 注册/登录账号
   - 可使用 X (Twitter) 账号登录

3. 申请 API 访问
   - 填写申请表单
   - 说明使用场景
   - 等待审核（通常1-3天）

4. 创建 API Key
   - 审核通过后进入控制台
   - 创建新的 API Key
   - 复制密钥

5. 充值账户
   - 添加支付方式
   - 充值 $20-50

#### 模型选择：
- `grok-beta` - 当前可用版本
- `grok-1` - 即将推出

#### 成本：
```
输入: $5/1M tokens
输出: $15/1M tokens
每天约: $3-5
```

---

### 3. DeepSeek

#### 获取步骤：
1. 访问 DeepSeek 平台
   ```
   https://platform.deepseek.com/
   ```

2. 注册账号
   - Email 注册
   - 或使用 GitHub 登录

3. 验证手机号
   - 支持中国大陆手机号

4. 创建 API Key
   - 进入"API Keys"页面
   - 点击"Create new key"
   - 复制密钥：`sk-xxx...`

5. 充值
   - 添加支付方式
   - 最低充值 ¥10
   - 新用户通常有免费额度

#### 模型选择：
- `deepseek-chat` - **推荐** 通用对话
- `deepseek-coder` - 代码专用

#### 成本：
```
输入: ¥0.001/1K tokens
输出: ¥0.002/1K tokens
每天约: ¥1-5 (~$0.15-0.7)
```

**优势：** 国内最便宜的高质量 AI！

---

## ⚙️ 配置步骤

### 1. 编辑配置文件
```bash
cd /Users/cyimon/Work/Dev/AITrading
nano .env
```

### 2. 添加新的 API Keys
```bash
# 原有的 AI
CLAUDE_API_KEY=sk-ant-xxx...
OPENAI_API_KEY=sk-proj-xxx...
GEMINI_API_KEY=AIza...

# 新增的 AI
QWEN_API_KEY=sk-xxx...
GROK_API_KEY=xai-xxx...
DEEPSEEK_API_KEY=sk-xxx...

# AI 配置
AI_INITIAL_BALANCE=300
AI_MAX_POSITION_SIZE=100
ARENA_UPDATE_INTERVAL=600
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
   ✅ Qwen API 已配置
   ✅ Grok API 已配置
   ✅ DeepSeek API 已配置
   📊 已配置 6 个 AI 模型
```

### 4. 启动完整版竞技场
```bash
# 停止演示服务器
pkill -f demo_ai_arena

# 启动完整版（6个AI）
python3 ai_arena_full.py
```

---

## 🎯 推荐配置方案

### 方案 A：经济型（国产AI）
```bash
QWEN_API_KEY=xxx
DEEPSEEK_API_KEY=xxx
GEMINI_API_KEY=xxx
```
**成本：** ~$2-4/天
**特点：** 性价比最高，适合长期运行

### 方案 B：平衡型
```bash
CLAUDE_API_KEY=xxx
QWEN_API_KEY=xxx
DEEPSEEK_API_KEY=xxx
```
**成本：** ~$5-7/天
**特点：** 质量与成本平衡

### 方案 C：顶级型
```bash
CLAUDE_API_KEY=xxx
GPT_MODEL=gpt-4o
OPENAI_API_KEY=xxx
GROK_API_KEY=xxx
```
**成本：** ~$10-15/天
**特点：** 最高质量，适合专业使用

### 方案 D：全家桶（推荐）
```bash
# 全部6个AI
CLAUDE_API_KEY=xxx
OPENAI_API_KEY=xxx
GEMINI_API_KEY=xxx
QWEN_API_KEY=xxx
GROK_API_KEY=xxx
DEEPSEEK_API_KEY=xxx
```
**成本：** ~$15-20/天
**特点：** 最完整的对比，看哪个AI最强

---

## 💰 成本对比

| 配置 | 每天成本 | 每月成本 | 适用场景 |
|------|----------|----------|----------|
| 仅 DeepSeek | ~$0.7 | ~$21 | 预算紧张 |
| DeepSeek + Qwen | ~$2 | ~$60 | 国产组合 |
| Gemini + DeepSeek + Qwen | ~$3 | ~$90 | 经济型 |
| Claude + GPT-4 + Gemini | ~$8 | ~$240 | 高质量 |
| 全部6个AI | ~$18 | ~$540 | 完整对比 |

---

## 🚀 启动命令

### 启动完整版（6个AI）
```bash
python3 ai_arena_full.py
```

### 或保持原有版本（3个AI）
```bash
python3 ai_arena_main.py
```

### 演示模式（不需要API Key）
```bash
python3 demo_ai_arena.py
```

---

## 📊 预期效果

启动后你会看到：

```
================================================================================
🤖 AI Trading Arena - 完整版（6个AI模型）
================================================================================

✅ 已连接到 Hyperliquid (测试网)
📍 钱包地址: 0x...

🤖 注册 AI 模型...
✅ AI 模型已注册: Claude (Sonnet)
✅ AI 模型已注册: GPT-4 (Turbo)
✅ AI 模型已注册: Gemini (Pro)
✅ AI 模型已注册: Qwen (Max)
✅ AI 模型已注册: Grok (Beta)
✅ AI 模型已注册: DeepSeek (Chat)

================================================================================
🏟️  竞技场配置
================================================================================
参赛 AI: 6 个
交易对: BTC, ETH, SOL
初始资金: $300.00 / AI
最大仓位: $100.00
更新间隔: 600 秒
================================================================================

🚀 AI 竞技场启动！共有 6 个 AI 参赛
============================================================
🏟️  开始新的竞技场周期
============================================================
```

然后每10分钟会看到：
```
🤖 Claude (Sonnet) | BTC | 决策: buy | 置信度: 75.3% | 理由: ...
🤖 GPT-4 (Turbo) | BTC | 决策: hold | 置信度: 60.2% | 理由: ...
🤖 Gemini (Pro) | BTC | 决策: sell | 置信度: 68.5% | 理由: ...
🤖 Qwen (Max) | BTC | 决策: buy | 置信度: 82.1% | 理由: ...
🤖 Grok (Beta) | BTC | 决策: strong_buy | 置信度: 88.7% | 理由: ...
🤖 DeepSeek (Chat) | BTC | 决策: hold | 置信度: 55.0% | 理由: ...

================================================================================
🏆 AI 模型排行榜
================================================================================
排名     模型                   余额              盈亏              ROI        交易数      胜率      
--------------------------------------------------------------------------------
1      Grok (Beta)          $1,423.56       $423.56         141.19%    12       83.3%   
2      Qwen (Max)           $1,356.78       $356.78         118.93%    15       73.3%   
3      Claude (Sonnet)      $1,234.56       $234.56         78.19%     18       66.7%   
4      DeepSeek (Chat)      $1,156.23       $156.23         52.08%     14       64.3%   
5      GPT-4 (Turbo)        $1,089.45       $89.45          29.82%     16       56.3%   
6      Gemini (Pro)         $987.65         $-12.35         -4.12%     11       45.5%   
================================================================================
```

---

## 🎨 Web 界面

前端会自动显示所有6个AI的数据：
- 实时排行榜
- 权益曲线对比
- 每个AI的决策理由
- 实时更新

访问：
```bash
open web/ai_arena.html
```

---

## 💡 使用建议

1. **从3个开始**
   - 先用 DeepSeek + Qwen + Gemini
   - 这三个最便宜
   - 测试几天

2. **逐步增加**
   - 如果效果好，加入 Claude
   - 再考虑 GPT-4 和 Grok

3. **观察对比**
   - 看哪个AI决策质量最高
   - 哪个盈利最稳定
   - 成本效益比

4. **优化配置**
   - 移除表现差的AI
   - 保留表现好的
   - 调整资金分配

---

## ❓ 常见问题

### Q: 6个AI会不会太多？
A: 可以选择性启用。不配置API Key的AI不会启动。

### Q: 成本会翻倍吗？
A: 是的，6个AI成本约为3个AI的2倍。建议选择经济型组合。

### Q: 哪个AI最好？
A: 需要实际运行对比。一般来说：
- 质量：Claude > GPT-4 > Grok > Qwen > Gemini > DeepSeek
- 性价比：DeepSeek > Qwen > Gemini > GPT-4 > Claude > Grok

### Q: 可以混合使用吗？
A: 可以！这就是竞技场的意义，让不同AI竞争。

---

**准备好让6个AI开始竞争了吗？** 🤖⚔️🤖

配置好API Keys后运行：
```bash
python3 ai_arena_full.py
```

