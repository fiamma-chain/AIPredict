# Redis 持久化快速开始指南

## 🚀 快速开始

### 1. 安装 Redis

使用提供的自动化脚本：

```bash
./setup_redis.sh
```

或手动安装：

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

**Docker:**
```bash
docker run -d --name redis-ai -p 6379:6379 -v redis-data:/data redis:7-alpine redis-server --appendonly yes
```

### 2. 配置系统

在 `.env` 文件中添加 Redis 配置：

```env
# Redis 配置
REDIS_ENABLED=True
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### 3. 启动系统

```bash
python consensus_arena_multiplatform.py
```

系统启动时会自动：
- 连接到 Redis
- 为每个 AI 模型启用持久化
- 将所有决策响应保存到 Redis

### 4. 查询数据

查看统计信息：
```bash
./redis_query_tool.py stats
```

查询特定数据：
```bash
./redis_query_tool.py query hyperliquid DeepSeek BTC --limit 20
```

导出数据：
```bash
./redis_query_tool.py export hyperliquid Claude BTC --output data.json
```

## 📊 数据结构

### Redis 键格式
```
ai_responses:{platform}:{ai_model}:{coin}
```

### 示例键
```
ai_responses:hyperliquid:DeepSeek:BTC
ai_responses:aster:Claude:ETH
ai_responses:hyperliquid:GPT:BTC
```

### 数据内容
每条响应包含：
- `timestamp`: 时间戳
- `platform`: 交易平台
- `ai_model`: AI 模型名称
- `coin`: 币种
- `decision`: 交易决策 (buy/sell/hold)
- `confidence`: 信心度 (0-100)
- `reasoning`: 决策理由
- `raw_response`: 原始响应

## 🔍 常用命令

### 查看所有平台
```bash
./redis_query_tool.py platforms
```

### 查看所有 AI 模型
```bash
./redis_query_tool.py models
./redis_query_tool.py models hyperliquid
```

### 查看统计信息
```bash
./redis_query_tool.py stats
```

输出示例：
```
📊 Redis 数据统计
============================================================

总键数: 12
总响应数: 4850

平台分布:
  • hyperliquid: 2400 条
  • aster: 2450 条

AI 模型分布:
  • DeepSeek: 800 条
  • Claude: 810 条
  • Grok: 820 条
  • GPT: 805 条
  • Gemini: 815 条
  • Qwen: 800 条
```

### 查询响应历史
```bash
# 查询最近10条
./redis_query_tool.py query hyperliquid DeepSeek BTC --limit 10

# 查询最近50条
./redis_query_tool.py query aster Claude BTC --limit 50
```

### 导出数据
```bash
# 导出为 JSON 文件
./redis_query_tool.py export hyperliquid DeepSeek BTC --output deepseek_btc.json

# 导出最近1000条
./redis_query_tool.py export aster Claude BTC --output claude_btc.json --limit 1000
```

## 🛠️ 维护操作

### 检查 Redis 状态
```bash
redis-cli ping
# 应输出: PONG
```

### 查看 Redis 信息
```bash
redis-cli INFO
redis-cli INFO persistence
redis-cli INFO memory
```

### 查看所有键
```bash
redis-cli KEYS "ai_responses:*"
```

### 查看特定键的数据量
```bash
redis-cli LLEN "ai_responses:hyperliquid:DeepSeek:BTC"
```

### 清理数据
```bash
# 清理特定平台
./redis_query_tool.py clear --platform hyperliquid

# 清理特定 AI 模型
./redis_query_tool.py clear --platform hyperliquid --ai-model DeepSeek

# 清理所有数据（谨慎！）
./redis_query_tool.py clear --all
```

## 🔐 数据持久化

### 启用 AOF 持久化（推荐）

编辑 Redis 配置文件：
- macOS: `/usr/local/etc/redis.conf` 或 `/opt/homebrew/etc/redis.conf`
- Linux: `/etc/redis/redis.conf`

添加以下配置：
```conf
# 启用 AOF
appendonly yes

# 同步策略（推荐）
appendfsync everysec

# AOF 文件名
appendfilename "appendonly.aof"
```

重启 Redis：
```bash
# macOS
brew services restart redis

# Linux
sudo systemctl restart redis-server

# Docker
docker restart redis-ai
```

### 验证持久化
```bash
redis-cli CONFIG GET appendonly
# 应输出: 1) "appendonly" 2) "yes"
```

## 💾 备份和恢复

### 手动备份
```bash
# 触发保存
redis-cli SAVE

# 复制 RDB 文件
cp /var/lib/redis/dump.rdb /backup/redis-backup-$(date +%Y%m%d).rdb

# 复制 AOF 文件
cp /var/lib/redis/appendonly.aof /backup/redis-aof-$(date +%Y%m%d).aof
```

### 定期备份（crontab）
```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨2点备份
0 2 * * * redis-cli SAVE && cp /var/lib/redis/dump.rdb /backup/redis-$(date +\%Y\%m\%d).rdb
```

### 恢复数据
```bash
# 停止 Redis
sudo systemctl stop redis-server

# 恢复备份文件
cp /backup/redis-backup-20251022.rdb /var/lib/redis/dump.rdb

# 启动 Redis
sudo systemctl start redis-server
```

## 📈 性能监控

### 查看内存使用
```bash
redis-cli INFO memory | grep used_memory_human
```

### 查看连接数
```bash
redis-cli INFO clients | grep connected_clients
```

### 查看操作统计
```bash
redis-cli INFO stats
```

### 实时监控命令
```bash
redis-cli MONITOR
```

## ⚠️ 注意事项

1. **内存管理**: 系统会自动限制每个键最多存储 1000 条记录
2. **过期时间**: 数据默认保留 30 天后自动清理
3. **密码保护**: 生产环境建议设置 Redis 密码
4. **网络安全**: 不要将 Redis 端口暴露到公网
5. **定期备份**: 重要数据请定期备份

## 🐛 故障排除

### Redis 连接失败
```
❌ Redis 连接失败: Connection refused
```

解决方法：
1. 检查 Redis 是否运行: `redis-cli ping`
2. 检查端口: `netstat -an | grep 6379`
3. 检查配置: `cat /etc/redis/redis.conf | grep bind`

### 内存不足
```
⚠️  Redis 内存不足
```

解决方法：
1. 增加内存限制: `redis-cli CONFIG SET maxmemory 256mb`
2. 启用淘汰策略: `redis-cli CONFIG SET maxmemory-policy allkeys-lru`
3. 清理旧数据: `./redis_query_tool.py clear --platform hyperliquid`

### 持久化失败
```
❌ Redis 持久化失败
```

解决方法：
1. 检查磁盘空间: `df -h`
2. 检查权限: `ls -la /var/lib/redis`
3. 查看日志: `tail -f /var/log/redis/redis-server.log`

## 📚 更多文档

- [完整配置指南](./REDIS_PERSISTENCE_GUIDE.md)
- [Redis 官方文档](https://redis.io/documentation)
- [项目 README](./README.md)

## 💡 提示

- 使用 `./redis_query_tool.py --help` 查看所有命令
- 使用 `./redis_query_tool.py <command> --help` 查看具体命令帮助
- 定期查看统计信息了解数据增长情况
- 导出重要数据进行离线分析

## 🎯 最佳实践

1. ✅ 启用 AOF 持久化
2. ✅ 设置合理的过期时间
3. ✅ 定期备份数据
4. ✅ 监控内存使用
5. ✅ 保护 Redis 密码
6. ✅ 使用查询工具分析数据

---

如有问题，请参考 [完整配置指南](./REDIS_PERSISTENCE_GUIDE.md) 或查看日志文件。

