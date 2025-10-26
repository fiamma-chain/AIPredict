"""
从交易所获取各个账户的实际余额
忽略配置文件中的初始金额配置
"""
import asyncio
import logging
from config.settings import settings, get_individual_traders_config
from trading.hyperliquid.client import HyperliquidClient
from trading.aster.client import AsterClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_account_balance(name: str, private_key: str, platform: str):
    """
    获取账户实际余额
    
    Args:
        name: 账户名称
        private_key: 私钥
        platform: 平台名称
    
    Returns:
        账户信息字典
    """
    try:
        # 创建客户端
        if platform.lower() == "hyperliquid":
            client = HyperliquidClient(private_key, settings.hyperliquid_testnet)
            platform_display = "Hyperliquid"
        elif platform.lower() == "aster":
            client = AsterClient(private_key, settings.aster_testnet)
            platform_display = "Aster"
        else:
            logger.error(f"❌ 不支持的平台: {platform}")
            return None
        
        # 获取账户信息
        account = await client.get_account_info()
        
        # 获取余额（账户价值）
        account_value = float(account.get('marginSummary', {}).get('accountValue', 0))
        
        # 获取可用余额
        withdrawable = float(account.get('withdrawable', 0))
        
        # 获取持仓
        positions = account.get('assetPositions', [])
        position_list = []
        total_position_value = 0
        
        for pos in positions:
            if 'position' in pos:
                coin = pos['position']['coin']
                size = float(pos['position']['szi'])
                
                if size != 0:
                    entry_px = float(pos['position']['entryPx'])
                    is_long = size > 0
                    abs_size = abs(size)
                    
                    # 计算持仓价值（未实现盈亏）
                    unrealized_pnl = float(pos['position'].get('unrealizedPnl', 0))
                    position_value = abs_size * entry_px
                    
                    position_list.append({
                        'coin': coin,
                        'side': 'LONG' if is_long else 'SHORT',
                        'size': abs_size,
                        'entry_price': entry_px,
                        'unrealized_pnl': unrealized_pnl,
                        'position_value': position_value
                    })
                    
                    total_position_value += position_value
        
        # 关闭会话
        await client.close_session()
        
        return {
            'name': name,
            'platform': platform_display,
            'address': client.address if hasattr(client, 'address') else 'N/A',
            'account_value': account_value,  # 账户总价值（包含未实现盈亏）
            'withdrawable': withdrawable,     # 可提现余额
            'position_count': len(position_list),
            'positions': position_list,
            'total_position_value': total_position_value
        }
    
    except Exception as e:
        logger.error(f"❌ 获取 {name} ({platform}) 余额失败: {e}")
        return None


async def check_all_accounts():
    """检查所有账户的实际余额"""
    logger.info("=" * 100)
    logger.info("🔍 从交易所获取各个账户的实际保证金余额")
    logger.info("=" * 100)
    
    all_accounts = []
    
    # 1. 检查 Alpha 组
    logger.info("\n📊 Alpha组 (DeepSeek + Claude + Grok):")
    
    if settings.group_1_private_key:
        # Hyperliquid
        result = await get_account_balance(
            "Alpha组",
            settings.group_1_private_key,
            "hyperliquid"
        )
        if result:
            all_accounts.append(result)
        
        # Aster
        result = await get_account_balance(
            "Alpha组",
            settings.group_1_private_key,
            "aster"
        )
        if result:
            all_accounts.append(result)
    else:
        logger.warning("   ⚠️  未配置 GROUP_1_PRIVATE_KEY")
    
    # 2. 检查 Beta 组
    logger.info("\n📊 Beta组 (GPT-4 + Gemini + Qwen):")
    
    if settings.group_2_private_key:
        # Hyperliquid
        result = await get_account_balance(
            "Beta组",
            settings.group_2_private_key,
            "hyperliquid"
        )
        if result:
            all_accounts.append(result)
        
        # Aster
        result = await get_account_balance(
            "Beta组",
            settings.group_2_private_key,
            "aster"
        )
        if result:
            all_accounts.append(result)
    else:
        logger.warning("   ⚠️  未配置 GROUP_2_PRIVATE_KEY")
    
    # 3. 检查独立 AI 交易者
    logger.info("\n🎯 独立AI交易者:")
    
    try:
        individual_configs = get_individual_traders_config()
        
        if individual_configs:
            for config in individual_configs:
                ai_name = config["ai_name"]
                private_key = config["private_key"]
                
                logger.info(f"\n   {ai_name}-Solo:")
                
                # 独立交易者只在 Aster 平台
                result = await get_account_balance(
                    f"{ai_name}-Solo",
                    private_key,
                    "aster"
                )
                if result:
                    all_accounts.append(result)
        else:
            logger.info("   没有配置独立AI交易者")
    
    except ValueError as e:
        logger.error(f"   ❌ 配置错误: {e}")
    
    # 打印详细信息
    if not all_accounts:
        logger.warning("\n⚠️  没有找到任何配置的账户")
        logger.info("\n请在 .env 文件中配置以下私钥:")
        logger.info("  - GROUP_1_PRIVATE_KEY (Alpha组)")
        logger.info("  - GROUP_2_PRIVATE_KEY (Beta组)")
        logger.info("  - INDIVIDUAL_<AI_NAME>_PRIVATE_KEY (独立交易者)")
        return
    
    logger.info("\n" + "=" * 100)
    logger.info("💰 账户实际保证金详情")
    logger.info("=" * 100)
    
    for account in all_accounts:
        logger.info(f"\n{'─' * 100}")
        logger.info(f"📍 {account['name']} - {account['platform']}")
        logger.info(f"{'─' * 100}")
        logger.info(f"   地址: {account['address']}")
        logger.info(f"   💰 账户总价值: ${account['account_value']:.2f}")
        logger.info(f"   💵 可提现余额: ${account['withdrawable']:.2f}")
        
        if account['position_count'] > 0:
            logger.info(f"\n   📊 持仓详情 ({account['position_count']}个):")
            for i, pos in enumerate(account['positions'], 1):
                logger.info(f"      {i}. {pos['coin']} {pos['side']}")
                logger.info(f"         数量: {pos['size']:.6f}")
                logger.info(f"         开仓价: ${pos['entry_price']:,.2f}")
                logger.info(f"         持仓价值: ${pos['position_value']:,.2f}")
                logger.info(f"         未实现盈亏: ${pos['unrealized_pnl']:+.2f}")
            
            logger.info(f"\n   📊 总持仓价值: ${account['total_position_value']:,.2f}")
        else:
            logger.info(f"\n   📭 无持仓")
    
    # 统计汇总
    logger.info("\n" + "=" * 100)
    logger.info("📊 统计汇总")
    logger.info("=" * 100)
    
    # 按账户类型分组
    groups = {}
    individuals = {}
    
    for account in all_accounts:
        name = account['name']
        platform = account['platform']
        
        if '-Solo' in name:
            # 独立交易者
            if name not in individuals:
                individuals[name] = {}
            individuals[name][platform] = account
        else:
            # AI组
            if name not in groups:
                groups[name] = {}
            groups[name][platform] = account
    
    # 打印 AI 组汇总
    if groups:
        logger.info("\n📊 AI组账户汇总:")
        for group_name, platforms in groups.items():
            logger.info(f"\n   {group_name}:")
            total_value = 0
            for platform, account in platforms.items():
                logger.info(f"      {platform:12s}: ${account['account_value']:>10.2f}")
                total_value += account['account_value']
            logger.info(f"      {'总计':12s}: ${total_value:>10.2f}")
    
    # 打印独立交易者汇总
    if individuals:
        logger.info("\n🎯 独立AI交易者账户汇总:")
        for trader_name, platforms in individuals.items():
            logger.info(f"\n   {trader_name}:")
            total_value = 0
            for platform, account in platforms.items():
                logger.info(f"      {platform:12s}: ${account['account_value']:>10.2f}")
                total_value += account['account_value']
            if len(platforms) > 1:
                logger.info(f"      {'总计':12s}: ${total_value:>10.2f}")
    
    # 按平台汇总
    logger.info("\n💎 平台汇总:")
    platform_summary = {}
    
    for account in all_accounts:
        platform = account['platform']
        if platform not in platform_summary:
            platform_summary[platform] = {
                'account_count': 0,
                'total_value': 0,
                'total_positions': 0
            }
        
        platform_summary[platform]['account_count'] += 1
        platform_summary[platform]['total_value'] += account['account_value']
        platform_summary[platform]['total_positions'] += account['position_count']
    
    for platform, stats in sorted(platform_summary.items()):
        logger.info(f"\n   {platform}:")
        logger.info(f"      账户数量: {stats['account_count']}")
        logger.info(f"      总资金: ${stats['total_value']:,.2f}")
        logger.info(f"      总持仓数: {stats['total_positions']}")
    
    # 总计
    total_all = sum(acc['account_value'] for acc in all_accounts)
    logger.info(f"\n💵 所有账户总资金: ${total_all:,.2f}")
    
    logger.info("\n" + "=" * 100)


async def main():
    """主函数"""
    try:
        await check_all_accounts()
    except Exception as e:
        logger.error(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

