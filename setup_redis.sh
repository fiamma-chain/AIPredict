#!/bin/bash

# Redis 安装和配置脚本
# 支持 macOS 和 Linux

set -e

echo "================================"
echo "Redis 安装和配置工具"
echo "================================"
echo ""

# 检测操作系统
OS_TYPE="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
fi

echo "检测到操作系统: $OS_TYPE"
echo ""

# 检查 Redis 是否已安装
check_redis_installed() {
    if command -v redis-server &> /dev/null; then
        echo "✅ Redis 已安装"
        redis-server --version
        return 0
    else
        echo "❌ Redis 未安装"
        return 1
    fi
}

# 安装 Redis (macOS)
install_redis_macos() {
    echo "正在通过 Homebrew 安装 Redis..."
    
    # 检查 Homebrew
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew 未安装。请先安装 Homebrew:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    # 安装 Redis
    brew install redis
    echo "✅ Redis 安装完成"
}

# 安装 Redis (Linux)
install_redis_linux() {
    echo "正在通过包管理器安装 Redis..."
    
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        sudo apt-get update
        sudo apt-get install -y redis-server
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        sudo yum install -y redis
    else
        echo "❌ 不支持的 Linux 发行版"
        exit 1
    fi
    
    echo "✅ Redis 安装完成"
}

# 配置 Redis 持久化
configure_redis_persistence() {
    echo ""
    echo "配置 Redis 持久化..."
    
    if [[ "$OS_TYPE" == "macos" ]]; then
        REDIS_CONF="/usr/local/etc/redis.conf"
        if [ ! -f "$REDIS_CONF" ]; then
            REDIS_CONF="/opt/homebrew/etc/redis.conf"
        fi
    else
        REDIS_CONF="/etc/redis/redis.conf"
    fi
    
    if [ ! -f "$REDIS_CONF" ]; then
        echo "⚠️  找不到 Redis 配置文件: $REDIS_CONF"
        echo "将使用默认配置"
        return
    fi
    
    echo "配置文件位置: $REDIS_CONF"
    
    # 备份原配置文件
    sudo cp "$REDIS_CONF" "${REDIS_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ 已备份原配置文件"
    
    # 启用 AOF 持久化
    if grep -q "^appendonly no" "$REDIS_CONF"; then
        sudo sed -i.bak 's/^appendonly no/appendonly yes/' "$REDIS_CONF"
        echo "✅ 已启用 AOF 持久化"
    elif grep -q "^appendonly yes" "$REDIS_CONF"; then
        echo "ℹ️  AOF 持久化已启用"
    else
        echo "appendonly yes" | sudo tee -a "$REDIS_CONF" > /dev/null
        echo "✅ 已添加 AOF 持久化配置"
    fi
    
    # 设置 AOF 同步策略
    if ! grep -q "^appendfsync everysec" "$REDIS_CONF"; then
        echo "appendfsync everysec" | sudo tee -a "$REDIS_CONF" > /dev/null
        echo "✅ 已设置 AOF 同步策略: everysec"
    fi
}

# 启动 Redis
start_redis() {
    echo ""
    echo "启动 Redis..."
    
    if [[ "$OS_TYPE" == "macos" ]]; then
        brew services start redis
        echo "✅ Redis 服务已启动"
    else
        sudo systemctl start redis-server
        sudo systemctl enable redis-server
        echo "✅ Redis 服务已启动并设置为开机自启"
    fi
}

# 测试 Redis 连接
test_redis() {
    echo ""
    echo "测试 Redis 连接..."
    
    if redis-cli ping | grep -q "PONG"; then
        echo "✅ Redis 连接成功"
        
        # 显示 Redis 信息
        echo ""
        echo "Redis 服务器信息:"
        redis-cli INFO server | grep "redis_version"
        redis-cli INFO persistence | grep "aof_enabled"
        
        return 0
    else
        echo "❌ Redis 连接失败"
        return 1
    fi
}

# 主流程
main() {
    # 检查是否已安装
    if ! check_redis_installed; then
        echo ""
        read -p "是否安装 Redis? (y/n) " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [[ "$OS_TYPE" == "macos" ]]; then
                install_redis_macos
            elif [[ "$OS_TYPE" == "linux" ]]; then
                install_redis_linux
            else
                echo "❌ 不支持的操作系统"
                exit 1
            fi
        else
            echo "❌ 取消安装"
            exit 0
        fi
    fi
    
    # 配置持久化
    echo ""
    read -p "是否配置 Redis 持久化? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        configure_redis_persistence
    fi
    
    # 启动服务
    echo ""
    read -p "是否启动 Redis 服务? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_redis
        sleep 2
        test_redis
    fi
    
    echo ""
    echo "================================"
    echo "✅ Redis 设置完成"
    echo "================================"
    echo ""
    echo "下一步:"
    echo "1. 检查 .env 文件中的 Redis 配置"
    echo "2. 运行系统: python consensus_arena_multiplatform.py"
    echo "3. 使用查询工具: python redis_query_tool.py stats"
    echo ""
}

# 显示帮助信息
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -i, --install  仅安装 Redis"
    echo "  -c, --config   仅配置 Redis"
    echo "  -s, --start    仅启动 Redis"
    echo "  -t, --test     仅测试 Redis 连接"
    echo ""
    echo "不带参数运行将执行交互式安装流程"
}

# 解析命令行参数
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -i|--install)
        check_redis_installed || {
            if [[ "$OS_TYPE" == "macos" ]]; then
                install_redis_macos
            elif [[ "$OS_TYPE" == "linux" ]]; then
                install_redis_linux
            fi
        }
        ;;
    -c|--config)
        configure_redis_persistence
        ;;
    -s|--start)
        start_redis
        ;;
    -t|--test)
        test_redis
        ;;
    *)
        main
        ;;
esac

