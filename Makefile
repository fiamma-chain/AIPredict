.PHONY: help install setup run dev clean test lint

# 默认目标
.DEFAULT_GOAL := help

# 项目配置
VENV := venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
PROJECT_DIR := /Users/payne/Fiamma/AIPredict

# 颜色输出
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## 显示帮助信息
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  AI Trading Arena - 启动命令$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)快速开始:$(NC)"
	@echo "  1. make install    # 安装依赖"
	@echo "  2. make setup      # 配置环境变量"
	@echo "  3. make run        # 运行项目"
	@echo ""

install: ## 安装Python依赖包
	@echo "$(BLUE)📦 安装依赖包...$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)⚠️  虚拟环境不存在，正在创建...$(NC)"; \
		python3 -m venv $(VENV); \
	fi
	@echo "$(GREEN)✓ 虚拟环境就绪$(NC)"
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ 依赖安装完成！$(NC)"

setup: ## 设置环境变量（从env.example.txt创建.env）
	@echo "$(BLUE)⚙️  配置环境变量...$(NC)"
	@if [ ! -f .env ]; then \
		if [ -f env.example.txt ]; then \
			cp env.example.txt .env; \
			echo "$(GREEN)✓ 已创建 .env 文件$(NC)"; \
			echo "$(YELLOW)⚠️  请编辑 .env 文件，填入你的 API Keys 和私钥！$(NC)"; \
			echo "$(YELLOW)   必填项：$(NC)"; \
			echo "   - CLAUDE_API_KEY"; \
			echo "   - OPENAI_API_KEY"; \
			echo "   - GEMINI_API_KEY"; \
			echo "   - QWEN_API_KEY"; \
			echo "   - GROK_API_KEY"; \
			echo "   - DEEPSEEK_API_KEY"; \
			echo "   - GROUP_1_PRIVATE_KEY (Alpha组)"; \
			echo "   - GROUP_2_PRIVATE_KEY (Beta组)"; \
		else \
			echo "$(RED)❌ env.example.txt 文件不存在$(NC)"; \
			exit 1; \
		fi \
	else \
		echo "$(GREEN)✓ .env 文件已存在$(NC)"; \
	fi

run: ## 运行AI交易系统（生产模式）
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  🚀 启动 AI Trading Arena$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)📌 Web界面地址: http://localhost:8000$(NC)"
	@echo "$(YELLOW)📌 按 Ctrl+C 停止服务$(NC)"
	@echo ""
	@cd $(PROJECT_DIR) && $(PYTHON) consensus_arena_multiplatform.py

dev: ## 运行AI交易系统（开发模式，显示详细日志）
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  🔧 启动 AI Trading Arena (开发模式)$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@export LOG_LEVEL=DEBUG && cd $(PROJECT_DIR) && $(PYTHON) consensus_arena_multiplatform.py

clean: ## 清理临时文件和缓存
	@echo "$(BLUE)🧹 清理临时文件...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.log" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ 清理完成$(NC)"

test: ## 运行测试（如果有）
	@echo "$(BLUE)🧪 运行测试...$(NC)"
	@if [ -d "tests" ]; then \
		$(PYTHON) -m pytest tests/; \
	else \
		echo "$(YELLOW)⚠️  未找到测试目录$(NC)"; \
	fi

lint: ## 代码格式检查
	@echo "$(BLUE)🔍 检查代码格式...$(NC)"
	@$(PIP) list | grep -q flake8 || $(PIP) install flake8
	@$(PYTHON) -m flake8 . --exclude=venv,.venv,__pycache__ --max-line-length=120 || echo "$(YELLOW)⚠️  发现代码格式问题$(NC)"

status: ## 显示系统状态
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  📊 系统状态$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(GREEN)Python:$(NC)"
	@$(PYTHON) --version 2>/dev/null || echo "  $(RED)❌ 虚拟环境未激活$(NC)"
	@echo ""
	@echo "$(GREEN)虚拟环境:$(NC)"
	@if [ -d "$(VENV)" ]; then echo "  $(GREEN)✓ 已创建$(NC)"; else echo "  $(RED)❌ 未创建$(NC)"; fi
	@echo ""
	@echo "$(GREEN)配置文件:$(NC)"
	@if [ -f ".env" ]; then echo "  $(GREEN)✓ .env 存在$(NC)"; else echo "  $(RED)❌ .env 不存在$(NC)"; fi
	@echo ""
	@echo "$(GREEN)依赖包:$(NC)"
	@$(PIP) list 2>/dev/null | wc -l | xargs -I {} echo "  已安装 {} 个包"

reinstall: clean ## 重新安装所有依赖
	@echo "$(BLUE)🔄 重新安装依赖...$(NC)"
	@rm -rf $(VENV)
	@$(MAKE) install

update: ## 更新依赖包
	@echo "$(BLUE)⬆️  更新依赖包...$(NC)"
	@$(PIP) install --upgrade -r requirements.txt
	@echo "$(GREEN)✓ 更新完成$(NC)"

# 快捷命令
start: run ## run 的别名

stop: ## 停止所有服务
	@echo "$(BLUE)🛑 停止服务...$(NC)"
	@pkill -f "consensus_arena_multiplatform.py" 2>/dev/null || echo "$(YELLOW)⚠️  服务未运行$(NC)"

restart: stop run ## 重启服务

logs: ## 查看日志（如果有）
	@echo "$(BLUE)📜 显示最近日志...$(NC)"
	@if [ -f "app.log" ]; then tail -f app.log; else echo "$(YELLOW)⚠️  日志文件不存在$(NC)"; fi

check-api-keys: ## 检查API Keys是否配置
	@echo "$(BLUE)🔑 检查 API Keys 配置...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ .env 文件不存在$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)正在检查配置...$(NC)"
	@grep "CLAUDE_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Claude$(NC)" || echo "  $(RED)❌ Claude$(NC)"
	@grep "OPENAI_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ OpenAI$(NC)" || echo "  $(RED)❌ OpenAI$(NC)"
	@grep "GEMINI_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Gemini$(NC)" || echo "  $(RED)❌ Gemini$(NC)"
	@grep "QWEN_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Qwen$(NC)" || echo "  $(RED)❌ Qwen$(NC)"
	@grep "GROK_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Grok$(NC)" || echo "  $(RED)❌ Grok$(NC)"
	@grep "DEEPSEEK_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ DeepSeek$(NC)" || echo "  $(RED)❌ DeepSeek$(NC)"
	@grep "GROUP_1_PRIVATE_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Alpha组私钥$(NC)" || echo "  $(RED)❌ Alpha组私钥$(NC)"
	@grep "GROUP_2_PRIVATE_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Beta组私钥$(NC)" || echo "  $(RED)❌ Beta组私钥$(NC)"

quick-start: install setup ## 一键完整安装和启动
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  ✅ 安装完成！$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)📝 下一步：$(NC)"
	@echo "  1. 编辑 .env 文件，填入你的 API Keys 和私钥"
	@echo "  2. 运行: make check-api-keys 检查配置"
	@echo "  3. 运行: make run 启动系统"
	@echo ""

