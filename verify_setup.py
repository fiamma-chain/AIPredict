"""
验证主网配置
"""
import asyncio
from config.settings import settings
from eth_account import Account
from trading.hyperliquid.client import HyperliquidClient


async def verify_setup():
    """验证配置是否正确"""
    print("=" * 60)
    print("🔍 验证 AI Trading Arena 配置")
    print("=" * 60)
    print()
    
    errors = []
    warnings = []
    
    # 1. 检查 Hyperliquid 配置
    print("1️⃣  检查 Hyperliquid 配置...")
    if not settings.hyperliquid_private_key:
        errors.append("未配置 Hyperliquid 私钥")
    else:
        try:
            account = Account.from_key(settings.hyperliquid_private_key)
            print(f"   ✅ 钱包地址: {account.address}")
            
            # 检查网络
            if settings.hyperliquid_testnet:
                print(f"   ⚠️  当前网络: 测试网")
                warnings.append("当前使用测试网，不会使用真实资金")
            else:
                print(f"   🚨 当前网络: 主网 (真实资金!)")
        except Exception as e:
            errors.append(f"私钥无效: {e}")
    
    # 2. 检查账户余额
    print()
    print("2️⃣  检查账户余额...")
    if settings.hyperliquid_private_key:
        try:
            client = HyperliquidClient(
                private_key=settings.hyperliquid_private_key,
                testnet=settings.hyperliquid_testnet
            )
            
            async with client:
                balance = await client.get_balance()
                print(f"   💰 总价值: ${balance['total_value']:.2f}")
                print(f"   💵 可用余额: ${balance['available_balance']:.2f}")
                print(f"   📊 未实现盈亏: ${balance['unrealized_pnl']:.2f}")
                
                if balance['available_balance'] < 100:
                    warnings.append(f"账户余额较低: ${balance['available_balance']:.2f}")
        except Exception as e:
            errors.append(f"无法连接到 Hyperliquid: {e}")
    
    # 3. 检查 AI API 配置
    print()
    print("3️⃣  检查 AI API 配置...")
    ai_count = 0
    
    if settings.claude_api_key:
        print(f"   ✅ Claude API 已配置")
        ai_count += 1
    else:
        print(f"   ⚪ Claude API 未配置")
    
    if settings.openai_api_key:
        print(f"   ✅ OpenAI API 已配置")
        ai_count += 1
    else:
        print(f"   ⚪ OpenAI API 未配置")
    
    if settings.gemini_api_key:
        print(f"   ✅ Gemini API 已配置")
        ai_count += 1
    else:
        print(f"   ⚪ Gemini API 未配置")
    
    if ai_count == 0:
        errors.append("没有配置任何 AI API！至少需要一个")
    else:
        print(f"   📊 已配置 {ai_count} 个 AI 模型")
    
    # 4. 检查风险配置
    print()
    print("4️⃣  检查风险管理配置...")
    print(f"   每日亏损限制: ${settings.daily_loss_limit:.2f}")
    print(f"   最大持仓数: {settings.max_open_positions}")
    print(f"   最大仓位: ${settings.max_position_size:.2f}")
    print(f"   最大杠杆: {settings.max_leverage}x")
    
    if settings.max_leverage > 5:
        warnings.append(f"杠杆过高: {settings.max_leverage}x (建议 ≤ 3x)")
    
    if settings.daily_loss_limit > 500:
        warnings.append(f"日亏损限制较高: ${settings.daily_loss_limit}")
    
    # 5. 检查 AI 配置
    print()
    print("5️⃣  检查 AI 交易配置...")
    print(f"   每个 AI 初始资金: ${settings.ai_initial_balance:.2f}")
    print(f"   每个 AI 最大仓位: ${settings.ai_max_position_size:.2f}")
    print(f"   更新间隔: {settings.arena_update_interval} 秒")
    
    if settings.arena_update_interval < 300 and not settings.hyperliquid_testnet:
        warnings.append("主网建议更新间隔 ≥ 300 秒以降低 API 成本")
    
    # 总结
    print()
    print("=" * 60)
    print("📋 验证总结")
    print("=" * 60)
    
    if errors:
        print()
        print("❌ 发现错误:")
        for error in errors:
            print(f"   • {error}")
    
    if warnings:
        print()
        print("⚠️  警告:")
        for warning in warnings:
            print(f"   • {warning}")
    
    if not errors and not warnings:
        print()
        print("✅ 所有检查通过！")
    
    print()
    
    if not errors:
        print("🚀 可以启动系统:")
        print("   python3 ai_arena_main.py")
    else:
        print("🛑 请先解决上述错误")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(verify_setup())

