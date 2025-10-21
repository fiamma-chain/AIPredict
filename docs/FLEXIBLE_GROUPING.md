# 🔄 灵活分组配置指南

## 📋 什么是灵活分组？

系统现在支持**自定义AI分组**，你可以根据自己的策略和偏好，自由组合6个AI到两个组中。

不再局限于固定的"国际AI组 vs 国产AI组"！

---

## 🎯 为什么需要灵活分组？

### 传统固定分组的局限

```
Group A: Claude, GPT-4, Gemini  (国际AI)
Group B: Qwen, Grok, DeepSeek   (国产AI)
```

**问题：**
- 如果你只想用3个AI怎么办？
- 如果你想测试混合组合怎么办？
- 如果你想按AI能力分组怎么办？

### 灵活分组的优势

✅ **自由组合** - 任意搭配6个AI  
✅ **策略测试** - 测试不同组合的效果  
✅ **成本优化** - 只用你需要的AI  
✅ **能力分级** - 按AI强弱分组对比  

---

## ⚙️ 如何配置

### 在 .env 文件中配置

```bash
# 灵活分组配置
GROUP_A_MEMBERS=claude,gpt4,gemini
GROUP_B_MEMBERS=qwen,grok,deepseek
```

### 可用的AI名称

| AI名称 | 对应模型 | API Key配置 |
|--------|---------|-------------|
| `claude` | Claude | CLAUDE_API_KEY |
| `gpt4` | GPT-4 | OPENAI_API_KEY |
| `gemini` | Gemini | GEMINI_API_KEY |
| `qwen` | Qwen | QWEN_API_KEY |
| `grok` | Grok | GROK_API_KEY |
| `deepseek` | DeepSeek | DEEPSEEK_API_KEY |

**注意：**
- 名称不区分大小写
- 用逗号分隔
- 每组至少需要2个AI

---

## 💡 推荐分组方案

### 方案 1：国际 vs 国产（默认）

```bash
GROUP_A_MEMBERS=claude,gpt4,gemini
GROUP_B_MEMBERS=qwen,grok,deepseek
```

**特点：**
- 地域对比
- 文化差异
- 训练数据差异

**适合：** 对比中西方AI的决策差异

---

### 方案 2：强AI vs 弱AI

```bash
GROUP_A_MEMBERS=claude,gpt4,qwen
GROUP_B_MEMBERS=gemini,grok,deepseek
```

**特点：**
- Group A: 顶级模型
- Group B: 性价比模型

**适合：** 测试是否"贵=好"

---

### 方案 3：大模型 vs 快速模型

```bash
GROUP_A_MEMBERS=claude,gpt4
GROUP_B_MEMBERS=qwen,grok,deepseek,gemini
```

**特点：**
- Group A: 最强但贵
- Group B: 多样化快速

**适合：** 质量 vs 速度的权衡

---

### 方案 4：只用3个AI（省钱）

```bash
GROUP_A_MEMBERS=qwen,deepseek
GROUP_B_MEMBERS=gemini
```

或

```bash
GROUP_A_MEMBERS=claude
GROUP_B_MEMBERS=qwen,deepseek
```

**特点：**
- 成本低
- 只需配置3个API Key
- 依然有共识机制

**成本：** ~$3-5/天（vs $15-20/天）

---

### 方案 5：混合测试

```bash
GROUP_A_MEMBERS=claude,qwen,deepseek
GROUP_B_MEMBERS=gpt4,gemini,grok
```

**特点：**
- 每组都有不同类型AI
- 更平衡
- 测试组合效应

**适合：** 研究AI协同

---

### 方案 6：极简模式（2个AI）

```bash
GROUP_A_MEMBERS=claude
GROUP_B_MEMBERS=qwen
```

**特点：**
- 最低成本
- 1 vs 1 对决
- 每组只有1票，所以会频繁无共识

**成本：** ~$5/天

**注意：** 单AI组没有共识优势，建议至少2个

---

## 🔧 配置步骤

### 步骤 1：决定分组策略

思考：
- 你想测试什么？
- 预算多少？
- 关注什么差异？

### 步骤 2：编辑 .env

```bash
nano .env
```

找到并修改：
```bash
# 灵活分组配置
GROUP_A_MEMBERS=你的选择
GROUP_B_MEMBERS=你的选择
```

### 步骤 3：配置对应的API Keys

确保你选择的AI都配置了API Key：
```bash
CLAUDE_API_KEY=sk-ant-xxx...
QWEN_API_KEY=sk-xxx...
DEEPSEEK_API_KEY=sk-xxx...
```

### 步骤 4：配置地址私钥

```bash
# 方式1：使用组私钥
GROUP_A_PRIVATE_KEY=0x...
GROUP_B_PRIVATE_KEY=0x...

# 方式2：使用AI私钥（自动使用第一个AI的私钥）
CLAUDE_PRIVATE_KEY=0x...
QWEN_PRIVATE_KEY=0x...

# 方式3：使用共享私钥
HYPERLIQUID_PRIVATE_KEY=0x...
```

### 步骤 5：启动

```bash
python3 arena_main.py consensus
```

---

## 📊 分组效果示例

### 启动日志

```
================================================================================
🗳️  启动模式：AI 共识决策竞技场（灵活分组）
================================================================================

🔧 配置 AI 组（灵活分组模式）...

📋 分组配置:
   Group A: Claude, Qwen, DeepSeek
   Group B: GPT-4, Gemini, Grok

✅ Group A 配置成功
   成员: Claude, Qwen, DeepSeek
   地址: 0x1234567...abcdef
   余额: $100.00
   共识阈值: 3 个 AI 中至少 2 个同意

✅ Group B 配置成功
   成员: GPT-4, Gemini, Grok
   地址: 0x2345678...bcdef0
   余额: $100.00
   共识阈值: 3 个 AI 中至少 2 个同意
```

---

## 🎯 实战建议

### 第1周：使用默认分组

```bash
GROUP_A_MEMBERS=claude,gpt4,gemini
GROUP_B_MEMBERS=qwen,grok,deepseek
```

观察：
- 哪组表现更好？
- 各AI的决策特点
- 共识达成率

### 第2周：优化分组

根据第1周的观察，调整分组：

**如果某个AI表现突出：**
```bash
# 把它单独成组或配弱组
GROUP_A_MEMBERS=claude  # 最强的单独
GROUP_B_MEMBERS=gpt4,qwen,gemini,grok,deepseek
```

**如果想降低成本：**
```bash
# 只用表现好的3-4个AI
GROUP_A_MEMBERS=claude,qwen
GROUP_B_MEMBERS=deepseek,gemini
```

### 第3周：深度测试

```bash
# 测试混合组合
GROUP_A_MEMBERS=claude,deepseek,gemini
GROUP_B_MEMBERS=gpt4,qwen,grok
```

对比：
- 混合组 vs 纯组
- 强组 vs 均衡组
- 成本 vs 收益

---

## 💡 高级技巧

### 技巧 1：按时间段切换分组

```bash
# 工作日：稳健组合
GROUP_A_MEMBERS=claude,qwen
GROUP_B_MEMBERS=gpt4,deepseek

# 周末：激进组合
GROUP_A_MEMBERS=claude,gpt4,qwen
GROUP_B_MEMBERS=gemini,grok,deepseek
```

### 技巧 2：A/B 测试

```bash
# 版本A（本周）
GROUP_A_MEMBERS=claude,qwen,deepseek
GROUP_B_MEMBERS=gpt4,gemini,grok

# 版本B（下周）
GROUP_A_MEMBERS=claude,gpt4,gemini
GROUP_B_MEMBERS=qwen,grok,deepseek
```

对比两周的表现差异

### 技巧 3：渐进式调整

```bash
# 第1天
GROUP_A_MEMBERS=claude,gpt4,gemini,qwen
GROUP_B_MEMBERS=grok,deepseek

# 几天后根据表现调整
# 如果Group A太强，移一个到Group B
GROUP_A_MEMBERS=claude,gpt4,gemini
GROUP_B_MEMBERS=qwen,grok,deepseek
```

---

## ❓ 常见问题

### Q: 可以只配置一个组吗？
A: 不可以，共识模式需要至少2个组。

### Q: 每组可以有不同数量的AI吗？
A: 可以！比如 Group A 2个，Group B 4个。

### Q: 如果只配置了3个AI怎么办？
A: 可以 2+1 分组，但单AI组没有共识优势。

### Q: 可以动态切换分组吗？
A: 需要停止程序，修改 .env，重新启动。

### Q: 分组会影响成本吗？
A: 成本取决于使用的AI数量，而不是分组方式。

---

## 📈 分组策略总结

| 策略 | Group A | Group B | 成本 | 适合 |
|------|---------|---------|------|------|
| 默认 | 国际AI | 国产AI | $15/天 | 地域对比 |
| 强弱 | 顶级3个 | 其他3个 | $15/天 | 能力对比 |
| 省钱 | 2个AI | 2个AI | $5/天 | 预算有限 |
| 混合 | 随机混 | 随机混 | $15/天 | 协同测试 |
| 极简 | 1个AI | 1个AI | $3/天 | 最低成本 |

---

## 🚀 快速开始

```bash
# 1. 编辑配置
nano .env

# 2. 修改分组（示例）
GROUP_A_MEMBERS=claude,qwen
GROUP_B_MEMBERS=deepseek,gemini

# 3. 确保对应API Key已配置
CLAUDE_API_KEY=xxx
QWEN_API_KEY=xxx
DEEPSEEK_API_KEY=xxx
GEMINI_API_KEY=xxx

# 4. 配置私钥
GROUP_A_PRIVATE_KEY=0x...
GROUP_B_PRIVATE_KEY=0x...

# 5. 启动
python3 arena_main.py consensus
```

---

**灵活分组让你的AI竞技场更加个性化和可控！** 🎯

开始尝试不同的组合，找到最适合你的策略！

