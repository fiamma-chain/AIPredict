# 🚀 启动交易系统

## 当前运行的系统：DeepSeek AI 超短线波段交易

### 快速启动

```bash
cd /Users/cyimon/Work/Dev/AITrading
python3 dual_cycle_trader.py
```

系统将：
- ✅ 每 15 分钟进行一次开仓决策分析
- ✅ 每 2 分钟检查持仓状态（止损/止盈）
- ✅ 自动执行交易策略（1.5%止损，3%止盈）
- ✅ 提供实时Web监控界面

### 访问前端

浏览器打开：**http://localhost:8000/**

### 配置文件

主配置文件：`.env`

重要参数：
- `HYPERLIQUID_PRIVATE_KEY` - 您的私钥
- `HYPERLIQUID_TESTNET=False` - 主网模式
- `DEEPSEEK_API_KEY` - DeepSeek API密钥
- `ALLOWED_TRADING_SYMBOLS=BTC` - 交易币种
- `ARENA_UPDATE_INTERVAL=120` - 持仓检查间隔（秒）

### 停止系统

```bash
kill $(cat arena.pid)
```

### 查看日志

```bash
tail -f arena.log
```

### 安全提示

⚠️ 主网交易涉及真实资金，请确保：
1. 理解交易策略和风险
2. 设置合理的止损止盈
3. 不要投入超过您能承受损失的资金
4. 定期检查系统状态和交易结果

### 工具脚本

- `generate_account.py` - 生成新的交易账户
- `verify_setup.py` - 验证系统配置
- `switch_to_mainnet.sh` - 切换到主网

### 技术支持

如遇问题，请检查：
1. `arena.log` - 系统运行日志
2. Hyperliquid余额是否充足
3. API密钥是否有效
4. 网络连接是否正常

---

**当前状态**：✅ 系统已启动并正常运行
**持仓检查**：每2分钟
**开仓决策**：每15分钟
**策略类型**：超短线波段（快进快出）
