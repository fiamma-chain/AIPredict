# Redis 持久化配置指南

## 概述

本系统使用 Redis 来持久化存储每个 AI 模型在每个平台上的所有决策响应，确保系统重启后数据不会丢失。

## 功能特性

- ✅ 按平台和 AI 模型分类存储响应数据
- ✅ 时间序列存储，支持按时间顺序查询
- ✅ 自动限制存储数量，避免内存溢出
- ✅ 支持数据过期和自动清理
- ✅ 提供丰富的数据查询和统计功能
- ✅ 支持 Redis 持久化（RDB/AOF），确保数据不丢失

## 安装 Redis

### macOS

```bash
# 使用 Homebrew 安装
brew install redis

# 启动 Redis 服务
brew services start redis

# 查看 Redis 状态
brew services info redis
```

### Ubuntu/Debian

```bash
# 安装 Redis
sudo apt-get update
sudo apt-get install redis-server

# 启动 Redis 服务
sudo systemctl start redis-server

# 设置开机自启
sudo systemctl enable redis-server
```

### Docker

```bash
# 运行 Redis 容器（带持久化）
docker run -d \
  --name redis-ai-trading \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:7-alpine redis-server --appendonly yes
```

## Redis 持久化配置

### RDB 持久化（快照）

在 Redis 配置文件 `/etc/redis/redis.conf` 中添加：

```conf
# 自动保存配置
save 900 1      # 900秒（15分钟）内至少1个键被修改
save 300 10     # 300秒（5分钟）内至少10个键被修改
save 60 10000   # 60秒内至少10000个键被修改

# RDB 文件名
dbfilename dump.rdb

# 数据存储目录
dir /var/lib/redis
```

### AOF 持久化（推荐）

在 Redis 配置文件中添加：

```conf
# 启用 AOF
appendonly yes

# AOF 文件名
appendfilename "appendonly.aof"

# 同步策略
# always: 每次写操作都同步（最安全，但性能较低）
# everysec: 每秒同步一次（推荐，平衡性能和安全性）
# no: 让操作系统决定何时同步
appendfsync everysec

# AOF 重写配置
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
```

### 重启 Redis 使配置生效

```bash
# macOS
brew services restart redis

# Linux
sudo systemctl restart redis-server

# Docker
docker restart redis-ai-trading
```

## 系统配置

在 `.env` 文件中配置 Redis 连接信息：

```env
# Redis 配置
REDIS_ENABLED=True          # 是否启用 Redis 持久化
REDIS_HOST=localhost        # Redis 主机地址
REDIS_PORT=6379            # Redis 端口
REDIS_DB=0                 # Redis 数据库编号（0-15）
REDIS_PASSWORD=            # Redis 密码（如果有）
```

## 数据存储结构

### 键名格式

```
ai_responses:{platform}:{ai_model}:{coin}
```

示例：
- `ai_responses:hyperliquid:DeepSeek:BTC`
- `ai_responses:aster:Claude:ETH`
- `ai_responses:hyperliquid:GPT:BTC`

### 数据格式

每条响应数据以 JSON 格式存储：

```json
{
  "timestamp": "2025-10-22T10:30:45.123456",
  "platform": "hyperliquid",
  "ai_model": "DeepSeek",
  "coin": "BTC",
  "decision": "buy",
  "confidence": 75.5,
  "reasoning": "价格突破关键阻力位，买盘强劲...",
  "raw_response": "DECISION: BUY\nCONFIDENCE: 75.5\n..."
}
```

### 数据特性

- 使用 Redis List 结构存储
- 最新的数据在列表头部（LPUSH）
- 每个键最多保留 1000 条记录（自动修剪）
- 数据过期时间：30 天（可配置）

## 使用方法

### 启动系统

系统启动时会自动初始化 Redis 连接并启用持久化：

```bash
python consensus_arena_multiplatform.py
```

启动日志：

```
🔄 正在初始化 Redis 持久化...
✅ Redis 连接成功: localhost:6379/0
✅ Redis 持久化已启用
[DeepSeek] ✅ Redis 持久化已启用
[Claude] ✅ Redis 持久化已启用
...
```

### 查询数据

使用提供的查询工具：

```bash
# 查看统计信息
python redis_query_tool.py stats

# 查看所有平台
python redis_query_tool.py platforms

# 查看指定平台的 AI 模型
python redis_query_tool.py models hyperliquid

# 查看指定 AI 在指定平台的响应
python redis_query_tool.py query hyperliquid DeepSeek BTC --limit 10

# 导出数据到 JSON 文件
python redis_query_tool.py export hyperliquid DeepSeek BTC --output data.json
```

### 在代码中使用

```python
from utils.redis_manager import get_redis_manager

# 获取 Redis 管理器
redis_mgr = get_redis_manager()

# 查询响应历史
responses = redis_mgr.get_ai_responses(
    platform="hyperliquid",
    ai_model="DeepSeek",
    coin="BTC",
    limit=100
)

# 获取统计信息
stats = redis_mgr.get_statistics()
print(f"总响应数: {stats['total_responses']}")
print(f"平台分布: {stats['platforms']}")
```

## 数据管理

### 清理数据

```bash
# 清理指定平台的数据
python redis_query_tool.py clear --platform hyperliquid

# 清理指定 AI 模型的数据
python redis_query_tool.py clear --platform hyperliquid --ai-model DeepSeek

# 清理所有数据（谨慎使用）
python redis_query_tool.py clear --all
```

### 备份数据

```bash
# Redis RDB 备份
redis-cli SAVE

# 复制备份文件
cp /var/lib/redis/dump.rdb /backup/dump-$(date +%Y%m%d).rdb

# AOF 备份
cp /var/lib/redis/appendonly.aof /backup/appendonly-$(date +%Y%m%d).aof
```

### 恢复数据

```bash
# 停止 Redis
sudo systemctl stop redis-server

# 恢复备份文件
cp /backup/dump-20251022.rdb /var/lib/redis/dump.rdb

# 启动 Redis
sudo systemctl start redis-server
```

## 性能优化

### 内存使用

- 每条响应约 1-2KB
- 6 个 AI 模型 × 2 个平台 × 1000 条记录 ≈ 12-24MB
- 建议为 Redis 分配至少 128MB 内存

### 连接池配置

系统使用单个 Redis 连接，对于高并发场景可以配置连接池：

```python
# 在 redis_manager.py 中修改
self.client = redis.ConnectionPool(
    host=self.host,
    port=self.port,
    db=self.db,
    max_connections=10
)
```

## 监控和维护

### 检查 Redis 状态

```bash
# 连接到 Redis
redis-cli

# 查看信息
INFO

# 查看内存使用
INFO memory

# 查看持久化信息
INFO persistence

# 查看所有键
KEYS ai_responses:*

# 查看列表长度
LLEN ai_responses:hyperliquid:DeepSeek:BTC
```

### 监控指标

```bash
# 查看统计
python redis_query_tool.py stats

# 输出示例：
{
  "total_keys": 12,
  "total_responses": 8450,
  "platforms": {
    "hyperliquid": 4200,
    "aster": 4250
  },
  "ai_models": {
    "DeepSeek": 1400,
    "Claude": 1410,
    "Grok": 1420,
    ...
  }
}
```

## 故障排除

### Redis 连接失败

```
❌ Redis 连接失败: Connection refused
```

解决方法：
1. 确保 Redis 服务正在运行：`redis-cli ping`
2. 检查防火墙设置
3. 验证连接信息（host、port、password）

### 内存不足

```
⚠️  Redis 内存不足
```

解决方法：
1. 增加 Redis 内存限制：`maxmemory 256mb`
2. 减少保存的历史记录数量
3. 启用数据淘汰策略：`maxmemory-policy allkeys-lru`

### 持久化失败

```
❌ Redis 持久化失败
```

解决方法：
1. 检查磁盘空间：`df -h`
2. 检查目录权限：`ls -la /var/lib/redis`
3. 查看 Redis 日志：`tail -f /var/log/redis/redis-server.log`

## 最佳实践

1. **启用 AOF 持久化**：确保数据不丢失
2. **定期备份**：每天备份 Redis 数据文件
3. **监控内存使用**：避免内存溢出
4. **设置合理的过期时间**：自动清理旧数据
5. **使用密码保护**：生产环境必须设置密码
6. **监控性能指标**：定期检查响应时间和吞吐量

## 常见问题

### Q: 系统重启后数据会丢失吗？

A: 不会。只要配置了 Redis 持久化（RDB 或 AOF），数据会自动保存到磁盘，重启后自动加载。

### Q: 如何查看某个 AI 的历史决策？

A: 使用查询工具：
```bash
python redis_query_tool.py query hyperliquid DeepSeek BTC --limit 50
```

### Q: 数据会占用多少空间？

A: 每个 AI 模型每个平台存储 1000 条记录，约 1-2MB。总共约 12-24MB。

### Q: 可以更改存储时长吗？

A: 可以。在 `redis_manager.py` 中修改：
```python
# 修改过期时间（秒）
self.client.expire(key, 60 * 24 * 60 * 60)  # 60天
```

### Q: 如何导出数据用于分析？

A: 使用导出命令：
```bash
python redis_query_tool.py export hyperliquid DeepSeek BTC --output analysis.json
```

## 相关资源

- [Redis 官方文档](https://redis.io/documentation)
- [Redis 持久化指南](https://redis.io/topics/persistence)
- [Redis 内存优化](https://redis.io/topics/memory-optimization)

## 支持

如有问题，请查看日志文件或联系技术支持。

