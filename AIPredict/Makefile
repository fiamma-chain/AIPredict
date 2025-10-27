.PHONY: help install setup run dev clean test lint status ps port logs logs-list logs-clean

# Default target
.DEFAULT_GOAL := help

# Project configuration
VENV := venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
PROJECT_DIR := $(shell pwd)

# Color output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show help information
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  AI Trading Arena - Startup Commands$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Quick Start:$(NC)"
	@echo "  1. make install    # Install dependencies"
	@echo "  2. make setup      # Configure environment variables"
	@echo "  3. make run        # Run project"
	@echo ""

install: ## Install Python dependencies
	@echo "$(BLUE)📦 Installing dependencies...$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)⚠️  Virtual environment doesn't exist, creating...$(NC)"; \
		python3 -m venv $(VENV); \
	fi
	@echo "$(GREEN)✓ Virtual environment ready$(NC)"
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed!$(NC)"

setup: ## Set environment variables (create .env from env.example.txt)
	@echo "$(BLUE)⚙️  Configuring environment variables...$(NC)"
	@if [ ! -f .env ]; then \
		if [ -f env.example.txt ]; then \
			cp env.example.txt .env; \
			echo "$(GREEN)✓ .env file created$(NC)"; \
			echo "$(YELLOW)⚠️  Please edit .env file and fill in your API Keys and private keys!$(NC)"; \
			echo "$(YELLOW)   Required fields:$(NC)"; \
			echo "   - CLAUDE_API_KEY"; \
			echo "   - OPENAI_API_KEY"; \
			echo "   - GEMINI_API_KEY"; \
			echo "   - QWEN_API_KEY"; \
			echo "   - GROK_API_KEY"; \
			echo "   - DEEPSEEK_API_KEY"; \
			echo "   - GROUP_1_PRIVATE_KEY (Alpha group)"; \
			echo "   - GROUP_2_PRIVATE_KEY (Beta group)"; \
		else \
			echo "$(RED)❌ env.example.txt file not found$(NC)"; \
			exit 1; \
		fi \
	else \
		echo "$(GREEN)✓ .env file already exists$(NC)"; \
	fi

run: ## Run AI trading system (background mode)
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  🚀 Starting AI Trading Arena$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@if ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" > /dev/null; then \
		echo "$(YELLOW)⚠️  Service already running!$(NC)"; \
		echo "$(YELLOW)   View logs: make logs$(NC)"; \
		echo "$(YELLOW)   Stop service: make stop$(NC)"; \
		exit 1; \
	fi
	@mkdir -p logs
	@LOG_FILE="logs/server-$$(date +%Y-%m-%d-%H).log"; \
	echo "$(GREEN)✓ Starting service...$(NC)"; \
	echo "$(YELLOW)📌 Web interface: http://localhost:46000$(NC)"; \
	echo "$(YELLOW)📌 Log file: $$LOG_FILE$(NC)"; \
	echo "$(YELLOW)📌 View logs: make logs$(NC)"; \
	echo "$(YELLOW)📌 Stop service: make stop$(NC)"; \
	cd $(PROJECT_DIR) && nohup $(PYTHON) consensus_arena_multiplatform.py >> $$LOG_FILE 2>&1 & \
	echo $$! > logs/server.pid; \
	sleep 2; \
	if ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" > /dev/null; then \
		echo "$(GREEN)✓ Service started successfully!$(NC)"; \
	else \
		echo "$(RED)❌ Service failed to start, please check logs$(NC)"; \
		exit 1; \
	fi

dev: ## Run AI trading system (development mode with detailed logs)
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  🔧 Starting AI Trading Arena (Development Mode)$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@export LOG_LEVEL=DEBUG && cd $(PROJECT_DIR) && $(PYTHON) consensus_arena_multiplatform.py

clean: ## Clean temporary files and cache (logs preserved)
	@echo "$(BLUE)🧹 Cleaning temporary files...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "nohup.out" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete (log files preserved)$(NC)"
	@echo "$(YELLOW)Tip: Use 'make logs-clean' to clean old logs$(NC)"

test: ## Run tests (if available)
	@echo "$(BLUE)🧪 Running tests...$(NC)"
	@if [ -d "tests" ]; then \
		$(PYTHON) -m pytest tests/; \
	else \
		echo "$(YELLOW)⚠️  Test directory not found$(NC)"; \
	fi

lint: ## Code format checking
	@echo "$(BLUE)🔍 Checking code format...$(NC)"
	@$(PIP) list | grep -q flake8 || $(PIP) install flake8
	@$(PYTHON) -m flake8 . --exclude=venv,.venv,__pycache__ --max-line-length=120 || echo "$(YELLOW)⚠️  Code format issues found$(NC)"

status: ## Show system status
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  📊 System Status$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(GREEN)Service Status:$(NC)"
	@if ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" > /dev/null; then \
		PID=$$(ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" | awk '{print $$2}' | head -1); \
		echo "  $(GREEN)✓ Running (PID: $$PID)$(NC)"; \
		if [ -f "logs/server.pid" ]; then \
			SAVED_PID=$$(cat logs/server.pid); \
			echo "  $(GREEN)✓ PID file: $$SAVED_PID$(NC)"; \
		fi; \
	else \
		echo "  $(RED)❌ Not running$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)Python:$(NC)"
	@$(PYTHON) --version 2>/dev/null || echo "  $(RED)❌ Virtual environment not activated$(NC)"
	@echo ""
	@echo "$(GREEN)Virtual Environment:$(NC)"
	@if [ -d "$(VENV)" ]; then echo "  $(GREEN)✓ Created$(NC)"; else echo "  $(RED)❌ Not created$(NC)"; fi
	@echo ""
	@echo "$(GREEN)Configuration:$(NC)"
	@if [ -f ".env" ]; then echo "  $(GREEN)✓ .env exists$(NC)"; else echo "  $(RED)❌ .env not found$(NC)"; fi
	@echo ""
	@echo "$(GREEN)Dependencies:$(NC)"
	@$(PIP) list 2>/dev/null | wc -l | xargs -I {} echo "  {} packages installed"
	@echo ""
	@echo "$(GREEN)Log Files:$(NC)"
	@if [ -d "logs" ]; then \
		COUNT=$$(ls logs/server-*.log 2>/dev/null | wc -l | tr -d ' '); \
		if [ "$$COUNT" -gt 0 ]; then \
			echo "  $(GREEN)✓ $$COUNT log files$(NC)"; \
			LATEST=$$(ls -t logs/server-*.log 2>/dev/null | head -1); \
			if [ -n "$$LATEST" ]; then \
				SIZE=$$(ls -lh "$$LATEST" | awk '{print $$5}'); \
				echo "  Latest: $$LATEST ($$SIZE)"; \
			fi; \
		else \
			echo "  $(YELLOW)⚠️  No log files$(NC)"; \
		fi; \
	else \
		echo "  $(YELLOW)⚠️  logs directory not found$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)Service Port:$(NC)"
	@if [ -f .env ]; then \
		PORT=$$(grep "^API_PORT=" .env | cut -d'=' -f2 | tr -d ' '); \
		if [ -n "$$PORT" ]; then \
			echo "  $(GREEN)✓ $$PORT$(NC) (configured)"; \
			echo "  $(GREEN)✓ http://localhost:$$PORT$(NC)"; \
		else \
			echo "  $(GREEN)✓ 46000$(NC) (default)"; \
			echo "  $(GREEN)✓ http://localhost:46000$(NC)"; \
		fi; \
	else \
		echo "  $(GREEN)✓ 46000$(NC) (default)"; \
	fi
	@echo "  View details: make port"

ps: ## Show service process information
	@echo "$(BLUE)🔍 Process Information:$(NC)"
	@if ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" > /dev/null; then \
		echo "$(GREEN)✓ Service running$(NC)"; \
		echo ""; \
		ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" | awk '{printf "  PID: %s\n  CPU: %s%%\n  MEM: %s%%\n  Start time: %s %s\n  Command: %s\n", $$2, $$3, $$4, $$9, $$10, $$11}'; \
	else \
		echo "$(RED)❌ Service not running$(NC)"; \
	fi

port: ## View service port information
	@echo "$(BLUE)🌐 Service Port Information:$(NC)"
	@echo ""
	@echo "$(GREEN)Configured Port:$(NC)"
	@if [ -f .env ]; then \
		PORT=$$(grep "^API_PORT=" .env | cut -d'=' -f2 | tr -d ' '); \
		if [ -n "$$PORT" ]; then \
			echo "  Port: $$PORT"; \
			echo "  Address: http://localhost:$$PORT"; \
		else \
			echo "  Port: 46000 (default)"; \
			echo "  Address: http://localhost:46000"; \
		fi; \
	else \
		echo "  Port: 46000 (default)"; \
		echo "  Address: http://localhost:46000"; \
	fi
	@echo ""
	@echo "$(GREEN)Listening Ports:$(NC)"
	@if ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" > /dev/null; then \
		PID=$$(ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" | awk '{print $$2}' | head -1); \
		if command -v lsof > /dev/null 2>&1; then \
			PORTS=$$(lsof -Pan -p $$PID -i 2>/dev/null | grep LISTEN | awk '{print $$9}' | cut -d':' -f2 | sort -u); \
			if [ -n "$$PORTS" ]; then \
				echo "  $(GREEN)✓ Service is listening on:$(NC)"; \
				for port in $$PORTS; do \
					echo "    - $$port"; \
				done; \
			else \
				echo "  $(YELLOW)⚠️  No listening ports detected (service may be starting)$(NC)"; \
			fi; \
		elif command -v netstat > /dev/null 2>&1; then \
			PORTS=$$(netstat -tuln 2>/dev/null | grep LISTEN | grep ":88" | awk '{print $$4}' | cut -d':' -f2 | sort -u); \
			if [ -n "$$PORTS" ]; then \
				echo "  $(GREEN)✓ Service is listening on:$(NC)"; \
				for port in $$PORTS; do \
					echo "    - $$port"; \
				done; \
			else \
				echo "  $(YELLOW)⚠️  No listening ports detected$(NC)"; \
			fi; \
		else \
			echo "  $(YELLOW)⚠️  Cannot detect ports (requires lsof or netstat)$(NC)"; \
		fi; \
	else \
		echo "  $(RED)❌ Service not running$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)Tips:$(NC)"
	@echo "  - Check all listening ports: lsof -i -P | grep LISTEN"
	@echo "  - Check specific port: lsof -i :46000"
	@echo "  - Test port connection: curl http://localhost:46000/api/status"

reinstall: clean ## Reinstall all dependencies
	@echo "$(BLUE)🔄 Reinstalling dependencies...$(NC)"
	@rm -rf $(VENV)
	@$(MAKE) install

update: ## Update dependencies
	@echo "$(BLUE)⬆️  Updating dependencies...$(NC)"
	@$(PIP) install --upgrade -r requirements.txt
	@echo "$(GREEN)✓ Update complete$(NC)"

# Shortcut commands
start: run ## Alias for run

stop: ## Stop all services
	@echo "$(BLUE)🛑 Stopping service...$(NC)"
	@if [ -f logs/server.pid ]; then \
		PID=$$(cat logs/server.pid); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; \
			echo "$(GREEN)✓ Service stopped (PID: $$PID)$(NC)"; \
		else \
			echo "$(YELLOW)⚠️  PID file exists but process not found$(NC)"; \
		fi; \
		rm -f logs/server.pid; \
	else \
		PID=$$(ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" | awk '{print $$2}' | head -1); \
		if [ -n "$$PID" ]; then \
			kill $$PID 2>/dev/null && \
				echo "$(GREEN)✓ Service stopped (PID: $$PID)$(NC)" || \
				echo "$(RED)❌ Stop failed$(NC)"; \
		else \
			echo "$(YELLOW)⚠️  Service not running$(NC)"; \
		fi; \
	fi

restart: ## Restart service
	@$(MAKE) stop || true
	@sleep 1
	@$(MAKE) run

logs: ## View logs in real-time
	@echo "$(BLUE)📜 Viewing logs in real-time...$(NC)"
	@if [ -d "logs" ] && [ -n "$$(ls -t logs/server-*.log 2>/dev/null | head -1)" ]; then \
		LATEST_LOG=$$(ls -t logs/server-*.log | head -1); \
		echo "$(GREEN)Log file: $$LATEST_LOG$(NC)"; \
		echo "$(YELLOW)Press Ctrl+C to exit$(NC)"; \
		echo ""; \
		tail -f $$LATEST_LOG; \
	else \
		echo "$(YELLOW)⚠️  Log file not found$(NC)"; \
		echo "$(YELLOW)   Start service first: make run$(NC)"; \
	fi

logs-list: ## List all log files
	@echo "$(BLUE)📂 Log Files:$(NC)"
	@if [ -d "logs" ]; then \
		ls -lh logs/server-*.log 2>/dev/null | awk '{print "  " $$9 " (" $$5 ")"}' || \
		echo "$(YELLOW)  No log files found$(NC)"; \
	else \
		echo "$(YELLOW)  logs directory not found$(NC)"; \
	fi

logs-clean: ## Clean old logs (keep last 7 days)
	@echo "$(BLUE)🧹 Cleaning old logs...$(NC)"
	@if [ -d "logs" ]; then \
		find logs -name "server-*.log" -type f -mtime +7 -delete 2>/dev/null; \
		echo "$(GREEN)✓ Deleted log files older than 7 days$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  logs directory not found$(NC)"; \
	fi

check-api-keys: ## Check API Keys configuration
	@echo "$(BLUE)🔑 Checking API Keys configuration...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ .env file not found$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Checking configuration...$(NC)"
	@grep "CLAUDE_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Claude$(NC)" || echo "  $(RED)❌ Claude$(NC)"
	@grep "OPENAI_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ OpenAI$(NC)" || echo "  $(RED)❌ OpenAI$(NC)"
	@grep "GEMINI_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Gemini$(NC)" || echo "  $(RED)❌ Gemini$(NC)"
	@grep "QWEN_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Qwen$(NC)" || echo "  $(RED)❌ Qwen$(NC)"
	@grep "GROK_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Grok$(NC)" || echo "  $(RED)❌ Grok$(NC)"
	@grep "DEEPSEEK_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ DeepSeek$(NC)" || echo "  $(RED)❌ DeepSeek$(NC)"
	@grep "GROUP_1_PRIVATE_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Alpha group private key$(NC)" || echo "  $(RED)❌ Alpha group private key$(NC)"
	@grep "GROUP_2_PRIVATE_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Beta group private key$(NC)" || echo "  $(RED)❌ Beta group private key$(NC)"

quick-start: install setup ## One-click complete installation and setup
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  ✅ Installation Complete!$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)📝 Next Steps:$(NC)"
	@echo "  1. Edit .env file and fill in your API Keys and private keys"
	@echo "  2. Run: make check-api-keys to verify configuration"
	@echo "  3. Run: make run to start the system"
	@echo ""

