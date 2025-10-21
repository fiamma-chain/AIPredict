# 🔄 模式切换指南

## 📋 两种运行模式

系统现在支持两种运行模式，可以随时切换：

### 1. 共识模式（默认）🗳️

**特点：**
- 6个AI分为2组
- 每组通过投票达成共识
- 至少2/3的AI同意才执行
- 2个地址，成本低

**适合场景：**
- 稳健交易
- 长期运营
- 预算有限
- 注重风险控制

### 2. 独立模式 🤖

**特点：**
- 6个AI各自独立决策
- 每个AI使用独立地址
- 交易频率更高
- 可以对比各AI表现

**适合场景：**
- AI性能对比
- 测试不同策略
- 预算充足
- 追求多样性

---

## 🚀 启动方式

### 方式一：使用启动脚本（推荐）

```bash
./start.sh
```

会显示菜单：
```
请选择启动模式：
  1. 共识模式（默认）- 多AI投票决策
  2. 独立模式 - 每个AI独立决策

请输入选项 (1/2，直接回车选择共识模式):
```

### 方式二：命令行参数

```bash
# 启动共识模式
python3 arena_main.py consensus

# 启动独立模式
python3 arena_main.py independent

# 默认（不指定参数）启动共识模式
python3 arena_main.py
```

### 方式三：简写

```bash
# 共识模式
python3 arena_main.py c

# 独立模式
python3 arena_main.py i
```

---

## 💰 资金配置对比

### 共识模式

```
需要地址数: 2 个
Group A: 100 USDC
Group B: 100 USDC
─────────────────
总计:    200 USDC
```

配置：
```bash
# Group A 地址
CLAUDE_PRIVATE_KEY=0x...
# 或
HYPERLIQUID_PRIVATE_KEY=0x...

# Group B 地址
QWEN_PRIVATE_KEY=0x...
# 或
HYPERLIQUID_PRIVATE_KEY=0x...
```

### 独立模式

```
需要地址数: 6 个
Claude:   100 USDC
GPT-4:    100 USDC
Gemini:   100 USDC
Qwen:     100 USDC
Grok:     100 USDC
DeepSeek: 100 USDC
─────────────────────
总计:     600 USDC
```

配置：
```bash
CLAUDE_PRIVATE_KEY=0x...
GPT_PRIVATE_KEY=0x...
GEMINI_PRIVATE_KEY=0x...
QWEN_PRIVATE_KEY=0x...
GROK_PRIVATE_KEY=0x...
DEEPSEEK_PRIVATE_KEY=0x...
```

---

## 🎯 如何选择模式

### 选择共识模式如果你：

- ✅ 预算有限（200U vs 600U）
- ✅ 追求稳健，不想频繁交易
- ✅ 相信集体智慧 > 个体判断
- ✅ 长期运营，注重风控

### 选择独立模式如果你：

- ✅ 预算充足
- ✅ 想对比各个AI的表现
- ✅ 想要更高的交易频率
- ✅ 测试阶段，收集数据

---

## 🔄 模式切换

### 切换前的准备

1. **停止当前运行的竞技场**
   ```bash
   # Ctrl + C 或
   pkill -f arena_main
   ```

2. **检查配置**
   
   切换到共识模式：
   ```bash
   # 确保至少配置了2个组的私钥
   # Group A 和 Group B
   ```
   
   切换到独立模式：
   ```bash
   # 确保配置了每个AI的私钥
   # 6个独立私钥
   ```

3. **启动新模式**
   ```bash
   ./start.sh
   # 或
   python3 arena_main.py [mode]
   ```

### 注意事项

- ⚠️ 切换模式会重新开始统计
- ⚠️ 持仓不会自动转移
- ⚠️ 建议在没有持仓时切换

---

## 📊 前端访问

### 共识模式前端
```bash
open web/consensus_arena.html
```

显示：
- 组排行榜
- 投票详情
- 共识历史
- 决策理由

### 独立模式前端
```bash
open web/ai_arena.html
```

显示：
- AI排行榜
- 权益曲线
- 个人决策
- 交易历史

### 统一前端（自动识别模式）
```bash
open web/index.html
```

会根据后端模式自动切换显示

---

## ⚙️ 配置示例

### 共识模式配置

```bash
# .env 文件

# 共识模式只需要2个地址
HYPERLIQUID_TESTNET=False

# AI API Keys（6个）
CLAUDE_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-proj-xxx
GEMINI_API_KEY=AIza-xxx
QWEN_API_KEY=sk-xxx
GROK_API_KEY=xai-xxx
DEEPSEEK_API_KEY=sk-xxx

# Group A 地址（可以使用共享）
CLAUDE_PRIVATE_KEY=0x...地址1
# 或
HYPERLIQUID_PRIVATE_KEY=0x...地址1

# Group B 地址
QWEN_PRIVATE_KEY=0x...地址2

# 配置
AI_MAX_POSITION_SIZE=30.0
DAILY_LOSS_LIMIT=50.0
ARENA_UPDATE_INTERVAL=600
```

### 独立模式配置

```bash
# .env 文件

# 独立模式需要6个地址
HYPERLIQUID_TESTNET=False

# AI API Keys（6个）
CLAUDE_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-proj-xxx
GEMINI_API_KEY=AIza-xxx
QWEN_API_KEY=sk-xxx
GROK_API_KEY=xai-xxx
DEEPSEEK_API_KEY=sk-xxx

# 6个独立地址
CLAUDE_PRIVATE_KEY=0x...地址1
GPT_PRIVATE_KEY=0x...地址2
GEMINI_PRIVATE_KEY=0x...地址3
QWEN_PRIVATE_KEY=0x...地址4
GROK_PRIVATE_KEY=0x...地址5
DEEPSEEK_PRIVATE_KEY=0x...地址6

# 配置
AI_MAX_POSITION_SIZE=30.0
DAILY_LOSS_LIMIT=50.0
ARENA_UPDATE_INTERVAL=600
```

---

## 📈 性能对比

| 指标 | 共识模式 | 独立模式 |
|------|---------|---------|
| 初始投入 | 200 USDC | 600 USDC |
| 地址数量 | 2 个 | 6 个 |
| 交易频率 | 中低 | 高 |
| 风险控制 | 更好 | 一般 |
| 决策质量 | 稳定 | 多样 |
| 手续费 | 低 | 高 |
| 管理复杂度 | 简单 | 复杂 |
| AI对比 | 组级别 | 个体级别 |

---

## 💡 实用建议

### 新手建议

1. **第一周：共识模式**
   - 成本低（200U）
   - 风险小
   - 观察效果

2. **第二周：根据表现决定**
   - 如果稳定盈利 → 继续共识或增加资金
   - 如果想对比 → 切换到独立模式

### 进阶玩法

1. **双模式运行**
   ```bash
   # 终端1：共识模式
   python3 arena_main.py consensus
   
   # 终端2：独立模式（不同端口）
   python3 arena_main.py independent
   ```
   
   对比两种模式的表现

2. **定期切换**
   ```bash
   # 周一到周五：共识模式（稳健）
   # 周末：独立模式（测试）
   ```

---

## ❓ 常见问题

### Q: 可以同时运行两种模式吗？
A: 可以，但需要使用不同的地址集和端口。

### Q: 切换模式会丢失数据吗？
A: 不会，交易历史保存在区块链上。但竞技场内存数据会重置。

### Q: 哪种模式更赚钱？
A: 取决于市场和AI表现。共识模式更稳健，独立模式更灵活。

### Q: 可以自定义分组吗？
A: 可以，修改 `arena_main.py` 中的分组逻辑。

### Q: 切换需要重新配置吗？
A: 只需确保对应模式的私钥已配置即可。

---

## 🚀 快速开始

### 第一次启动（推荐共识模式）

```bash
# 1. 配置 .env
nano .env
# 填入：
# - 6个AI API Keys
# - 2个地址私钥（Group A 和 Group B）

# 2. 验证
python3 verify_setup.py

# 3. 启动
./start.sh
# 选择 1（共识模式）

# 4. 查看前端
open web/consensus_arena.html
```

### 后续切换

```bash
# 停止当前
Ctrl + C

# 切换到独立模式
./start.sh
# 选择 2

# 或直接
python3 arena_main.py independent
```

---

## 📚 相关文档

- [共识模式详解](CONSENSUS_MODE.md)
- [多地址配置](MULTI_ADDRESS_SETUP.md)
- [交易策略](TRADING_STRATEGY.md)

祝交易顺利！🎉

