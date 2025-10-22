#!/usr/bin/env python3
"""
系统配置检查和启动脚本
帮助用户检查配置是否完整，并启动系统
"""
import os
import sys
from pathlib import Path

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

def check_env_file():
    """检查 .env 文件是否存在"""
    print_header("步骤 1: 检查配置文件")
    
    if not os.path.exists('.env'):
        print_error(".env 文件不存在")
        print_info("正在从 env.example.txt 创建...")
        if os.path.exists('env.example.txt'):
            os.system('cp env.example.txt .env')
            print_success(".env 文件已创建")
        else:
            print_error("env.example.txt 也不存在，无法创建配置文件")
            return False
    else:
        print_success(".env 文件已存在")
    
    return True

def check_configuration():
    """检查关键配置项"""
    print_header("步骤 2: 检查配置项")
    
    # 加载 .env 文件
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print_error(f"读取 .env 文件失败: {e}")
        return False
    
    # 检查必需配置
    required_configs = {
        '平台配置': [
            ('ENABLED_PLATFORMS', 'aster', '启用的交易平台'),
        ],
        'API Wallet 配置': [
            ('GROUP_1_PRIVATE_KEY', None, 'Alpha组 API Wallet 私钥'),
        ],
        'AI API Keys (至少需要3个)': [
            ('CLAUDE_API_KEY', None, 'Claude API Key'),
            ('OPENAI_API_KEY', None, 'OpenAI API Key'),
            ('GEMINI_API_KEY', None, 'Gemini API Key'),
            ('QWEN_API_KEY', None, 'Qwen API Key'),
            ('GROK_API_KEY', None, 'Grok API Key'),
            ('DEEPSEEK_API_KEY', None, 'DeepSeek API Key'),
        ],
        '交易配置': [
            ('ALLOWED_TRADING_SYMBOLS', 'BTC', '交易币种'),
            ('CONSENSUS_MIN_VOTES', '2', '最小共识票数'),
            ('MIN_CONFIDENCE', '60.0', '最小信心度'),
        ]
    }
    
    all_ok = True
    api_key_count = 0
    
    for section, configs in required_configs.items():
        print(f"\n{Colors.BOLD}{section}:{Colors.END}")
        
        for key, default, description in configs:
            value = env_vars.get(key, '')
            
            # 检查是否配置
            if not value or value.startswith('your_') or value == '0x你的API_Wallet私钥':
                if 'API' in section and 'KEY' in key:
                    print_warning(f"{description}: 未配置")
                else:
                    print_error(f"{description}: 未配置 (必需)")
                    all_ok = False
            else:
                # 隐藏敏感信息
                if 'KEY' in key or 'PRIVATE' in key:
                    display_value = value[:10] + '...' if len(value) > 10 else '***'
                    if 'API' in key:
                        api_key_count += 1
                else:
                    display_value = value
                print_success(f"{description}: {display_value}")
    
    # 检查 AI API Keys
    if api_key_count < 3:
        print_error(f"\nAI API Keys 不足: 需要至少 3 个，当前只有 {api_key_count} 个")
        print_info("每组需要 3 个 AI 进行共识决策")
        all_ok = False
    else:
        print_success(f"\nAI API Keys 充足: {api_key_count} 个")
    
    return all_ok

def print_configuration_guide():
    """打印配置指南"""
    print_header("配置指南")
    
    print(f"{Colors.BOLD}1. 创建 API Wallet{Colors.END}")
    print("   访问: https://www.asterdex.com/en/api-wallet")
    print("   - 切换到顶部的 'Pro API' 标签")
    print("   - 点击创建新的 API Wallet")
    print("   - 保存 Private Key（只显示一次）")
    
    print(f"\n{Colors.BOLD}2. 配置 .env 文件{Colors.END}")
    print("   编辑 .env 文件，填入以下信息：")
    print("   - GROUP_1_PRIVATE_KEY: 你的 API Wallet 私钥")
    print("   - CLAUDE_API_KEY: Claude API Key (如果有)")
    print("   - OPENAI_API_KEY: OpenAI API Key (如果有)")
    print("   - 至少配置 3 个 AI API Key")
    
    print(f"\n{Colors.BOLD}3. 可选配置{Colors.END}")
    print("   - ENABLED_PLATFORMS: aster (或 hyperliquid,aster)")
    print("   - ALLOWED_TRADING_SYMBOLS: BTC (或其他币种)")
    print("   - CONSENSUS_MIN_VOTES: 2 (最小共识票数)")
    
    print(f"\n{Colors.BOLD}4. 运行系统{Colors.END}")
    print("   配置完成后重新运行此脚本")

def confirm_start():
    """确认启动"""
    print_header("准备启动")
    
    print(f"{Colors.YELLOW}⚠️  重要提示:{Colors.END}")
    print("1. AsterDex 没有测试网，将使用真实资金")
    print("2. 建议先用小额资金测试")
    print("3. 系统会根据 AI 共识自动下单")
    print("4. 请确保已充分了解风险")
    
    print(f"\n{Colors.BOLD}是否继续启动系统？{Colors.END}")
    print("输入 'yes' 确认，或按 Ctrl+C 取消")
    
    try:
        response = input("\n请输入: ").strip().lower()
        return response in ['yes', 'y', '是']
    except KeyboardInterrupt:
        print("\n\n已取消")
        return False

def start_system():
    """启动系统"""
    print_header("启动系统")
    
    print_info("正在启动 AI 共识交易系统（多平台版）...")
    print_info("按 Ctrl+C 可以随时停止系统\n")
    
    # 运行系统
    os.system('python3 consensus_arena_multiplatform.py')

def main():
    """主函数"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║        AI 共识交易系统 - 配置检查和启动向导              ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    # 步骤 1: 检查 .env 文件
    if not check_env_file():
        sys.exit(1)
    
    # 步骤 2: 检查配置
    config_ok = check_configuration()
    
    if not config_ok:
        print_error("\n配置不完整，无法启动系统")
        print_configuration_guide()
        
        print(f"\n{Colors.BOLD}下一步操作:{Colors.END}")
        print("1. 按照上面的指南配置 .env 文件")
        print("2. 重新运行此脚本: python3 setup_and_run.py")
        print("3. 或者先测试连接: python3 test_aster_connection.py")
        sys.exit(1)
    
    print_success("\n✨ 配置检查完成，系统已就绪！")
    
    # 步骤 3: 确认启动
    if not confirm_start():
        print_info("\n已取消启动")
        print_info("如需测试连接，运行: python3 test_aster_connection.py")
        sys.exit(0)
    
    # 步骤 4: 启动系统
    try:
        start_system()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}系统已停止{Colors.END}")
    except Exception as e:
        print_error(f"\n启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}操作已取消{Colors.END}")
        sys.exit(0)

