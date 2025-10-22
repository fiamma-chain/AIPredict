.PHONY: start stop restart status logs clean help

# 配置变量
PYTHON = python3
MAIN_FILE = consensus_arena.py
LOG_FILE = /tmp/trading_output.log
PID_FILE = /tmp/trading.pid

# 默认目标
help:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🤖 AI交易系统 - Makefile 命令"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  make start       - 启动交易系统（后台运行）"
	@echo "  make start-fg    - 启动交易系统（前台运行，按Ctrl+C停止）"
	@echo "  make stop        - 停止交易系统"
	@echo "  make restart     - 重启交易系统"
	@echo "  make status      - 查看运行状态"
	@echo "  make logs        - 查看实时日志"
	@echo "  make clean       - 清理日志和缓存"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🌐 前端页面: http://localhost:8000/"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 启动服务（后台）
start:
	@echo "🚀 启动AI交易系统..."
	@if pgrep -f "$(MAIN_FILE)" > /dev/null; then \
		echo "⚠️  系统已在运行中！"; \
		echo "   使用 'make status' 查看状态"; \
		echo "   使用 'make restart' 重启系统"; \
		exit 1; \
	fi
	@nohup caffeinate -d $(PYTHON) $(MAIN_FILE) > $(LOG_FILE) 2>&1 & echo $$! > $(PID_FILE)
	@sleep 3
	@if pgrep -f "$(MAIN_FILE)" > /dev/null; then \
		echo "✅ 系统启动成功！"; \
		echo ""; \
		echo "📊 访问前端: http://localhost:8000/"; \
		echo "📋 查看日志: make logs"; \
		echo "⏹️  停止服务: make stop"; \
	else \
		echo "❌ 启动失败，请查看日志: make logs"; \
		exit 1; \
	fi

# 启动服务（前台）
start-fg:
	@echo "🚀 启动AI交易系统（前台模式）..."
	@echo "   按 Ctrl+C 停止服务"
	@echo ""
	@caffeinate -d $(PYTHON) $(MAIN_FILE)

# 停止服务
stop:
	@echo "⏹️  停止AI交易系统..."
	@if pgrep -f "$(MAIN_FILE)" > /dev/null; then \
		pkill -f "$(MAIN_FILE)" && \
		sleep 2 && \
		if pgrep -f "$(MAIN_FILE)" > /dev/null; then \
			echo "⚠️  正常停止失败，强制终止..."; \
			pkill -9 -f "$(MAIN_FILE)"; \
		fi; \
		lsof -ti:8000 | xargs kill -9 2>/dev/null || true; \
		rm -f $(PID_FILE); \
		echo "✅ 系统已停止"; \
	else \
		echo "⚠️  系统未运行"; \
	fi

# 重启服务
restart: stop
	@echo ""
	@sleep 2
	@$(MAKE) start

# 查看状态
status:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📊 系统状态"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if pgrep -f "$(MAIN_FILE)" > /dev/null; then \
		echo ""; \
		echo "✅ 系统运行中"; \
		echo ""; \
		echo "进程信息:"; \
		ps aux | grep "$(MAIN_FILE)" | grep -v grep | awk '{printf "  PID: %s\n  CPU: %s%%\n  内存: %s%%\n  运行时间: %s\n", $$2, $$3, $$4, $$10}'; \
		echo ""; \
		echo "端口占用:"; \
		lsof -i:8000 | grep LISTEN || echo "  端口8000未监听"; \
		echo ""; \
		echo "🌐 前端: http://localhost:8000/"; \
	else \
		echo ""; \
		echo "❌ 系统未运行"; \
		echo ""; \
		echo "使用 'make start' 启动系统"; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 查看日志
logs:
	@if [ -f $(LOG_FILE) ]; then \
		echo "📋 实时日志 (按 Ctrl+C 退出):"; \
		echo ""; \
		tail -f $(LOG_FILE); \
	else \
		echo "⚠️  日志文件不存在: $(LOG_FILE)"; \
	fi

# 查看最近日志
logs-tail:
	@if [ -f $(LOG_FILE) ]; then \
		echo "📋 最近50行日志:"; \
		echo ""; \
		tail -50 $(LOG_FILE); \
	else \
		echo "⚠️  日志文件不存在: $(LOG_FILE)"; \
	fi

# 清理日志和缓存
clean:
	@echo "🧹 清理日志和缓存..."
	@rm -f $(LOG_FILE)
	@rm -f $(PID_FILE)
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ 清理完成"

# 检查环境
check:
	@echo "🔍 检查运行环境..."
	@echo ""
	@echo "Python版本:"
	@$(PYTHON) --version
	@echo ""
	@echo ".env 文件:"
	@if [ -f .env ]; then \
		echo "  ✅ 存在"; \
	else \
		echo "  ❌ 不存在"; \
	fi
	@echo ""
	@echo "依赖包:"
	@$(PYTHON) -c "import fastapi, uvicorn, hyperliquid, anthropic, openai" 2>/dev/null && \
		echo "  ✅ 主要依赖已安装" || \
		echo "  ❌ 缺少依赖，请运行: pip install -r requirements.txt"

