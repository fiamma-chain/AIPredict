# Redis 余额历史存储 - 安装指南 📦

## ✅ 已完成的实现

### 1. 代码实现 ✅
- ✅ Redis管理器 (`utils/redis_manager.py`)
- ✅ 后端保存快照逻辑 (`consensus_arena_multiplatform.py`)
- ✅ API端点 `/api/balance_history`
- ✅ 前端加载历史数据 (`web/index.html`)
- ✅ 配置项 (`config/settings.py`)

### 2. Python库 ✅
- ✅ `redis==5.0.1` 已安装

### 3. 优雅降级 ✅
- ✅ Redis未连接时系统仍正常运行
- ✅ 只显示警告，不影响交易功能

## ⚠️ 当前状态

**Redis服务器**: ❌ 未安装/未运行

系统启动日志显示：
```
❌ Redis 连接失败: Error 61 connecting to localhost:6379. Connection refused.
```

**影响**: 
- ❌ 页面刷新后走势数据仍会清零
- ✅ 其他功能正常使用

## 🚀 启用Redis功能

### 方式1: 使用Homebrew (推荐)

#### 1. 安装Homebrew (如未安装)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. 安装Redis
```bash
brew install redis
```

#### 3. 启动Redis
```bash
# 后台运行
brew services start redis

# 或前台运行 (调试用)
redis-server
```

#### 4. 验证安装
```bash
redis-cli ping
# 应返回: PONG
```

#### 5. 重启交易系统
系统会自动检测并连接Redis，日志显示：
```
✅ Redis 连接成功: localhost:6379
```

### 方式2: 使用Docker

#### 1. 安装Docker Desktop
从 https://www.docker.com/products/docker-desktop 下载安装

#### 2. 运行Redis容器
```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:latest
```

#### 3. 验证运行
```bash
docker ps | grep redis
```

#### 4. 重启交易系统
系统会自动连接到Redis

### 方式3: 手动编译安装

#### 1. 下载Redis
```bash
cd /tmp
curl -O https://download.redis.io/redis-stable.tar.gz
tar xzf redis-stable.tar.gz
cd redis-stable
```

#### 2. 编译安装
```bash
make
sudo make install
```

#### 3. 启动Redis
```bash
redis-server --daemonize yes
```

## 📊 配置选项

### 默认配置 (`.env`)
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
BALANCE_HISTORY_TTL=604800  # 7天
```

### 自定义配置
如果Redis不在本地或使用了密码：
```env
REDIS_HOST=your-redis-host.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-password
```

## 🔍 验证功能

### 1. 检查Redis连接
```bash
tail -100 /tmp/ai_trading.log | grep Redis
```

应该看到：
```
✅ Redis 连接成功: localhost:6379
```

### 2. 检查数据保存
等待一个决策周期（5分钟）后：
```bash
redis-cli LLEN balance_history
```

应该返回一个数字（如：1, 2, 3...）

### 3. 查看最新数据
```bash
redis-cli LRANGE balance_history 0 0
```

### 4. 测试API
```bash
curl http://localhost:8000/api/balance_history | python3 -m json.tool
```

### 5. 测试前端
1. 打开 http://localhost:8000
2. 等待收集一些数据点（约10分钟）
3. 刷新页面 (Cmd+R)
4. ✅ 走势图应该显示历史数据，不再清零

## 🎯 功能对比

### 无Redis（当前状态）
```
页面刷新前: 有10个数据点
      ↓
   刷新页面
      ↓
页面刷新后: 数据清零，从0开始
```

### 有Redis（启用后）
```
页面刷新前: 有10个数据点
      ↓
   刷新页面
      ↓
页面刷新后: 从Redis加载100个历史点
            + 继续实时更新
```

## 📈 数据保存规则

### 保存时机
- 每5分钟决策周期结束后
- 自动保存4个账户的余额快照

### 保存内容
```json
{
  "timestamp": "2025-10-23T00:30:00",
  "accounts": [
    {
      "group": "Alpha组",
      "platform": "Alpha组-Hyperliquid",
      "balance": 250.42,
      "pnl": 0.42,
      "roi": 0.17,
      "total_trades": 5
    }
  ]
}
```

### 数据限制
- **最多保留**: 1000条记录
- **时间跨度**: 约83小时
- **自动过期**: 7天后删除

## 🛠️ 常见问题

### Q1: Redis安装后系统需要重启吗？
**A**: 不需要完全重启，只需：
```bash
# 停止当前系统
lsof -ti:8000 | xargs kill -9

# 重新启动
cd AIPredict
python3 consensus_arena_multiplatform.py
```

### Q2: Redis崩溃会影响交易吗？
**A**: 不会。Redis只用于存储历史数据，不影响实时交易。系统会检测到Redis断开并继续运行。

### Q3: 数据会占用多少内存？
**A**: 约500KB（1000条记录 × 500字节）

### Q4: 可以清空历史数据吗？
**A**: 可以
```bash
redis-cli DEL balance_history
```

### Q5: Redis需要配置持久化吗？
**A**: 建议配置，编辑`/usr/local/etc/redis.conf`:
```
save 900 1      # 15分钟内至少1个key变化就保存
save 300 10     # 5分钟内至少10个key变化就保存
save 60 10000   # 1分钟内至少10000个key变化就保存
```

## 🎓 总结

### 当前实现状态
- ✅ 所有代码已实现
- ✅ Python库已安装
- ✅ 系统正常运行
- ❌ Redis服务器未安装

### 启用步骤
1. 安装Redis (选择上述三种方式之一)
2. 启动Redis服务
3. 重启交易系统
4. ✅ 自动启用历史数据功能

### 预期效果
- 页面刷新不丢失数据
- 完整的收益走势图
- 更好的用户体验

---
*Redis余额历史存储 - 安装指南* 📦

**建议**: 安装Redis后，系统的用户体验会显著提升！

