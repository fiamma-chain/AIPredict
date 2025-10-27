"""
Get actual account balances from exchanges
Ignore initial balance configuration in config files
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
    Get actual account balance
    
    Args:
        name: Account name
        private_key: Private key
        platform: Platform name
    
    Returns:
        Account information dictionary
    """
    try:
        # Create client
        if platform.lower() == "hyperliquid":
            client = HyperliquidClient(private_key, settings.hyperliquid_testnet)
            platform_display = "Hyperliquid"
        elif platform.lower() == "aster":
            client = AsterClient(private_key, settings.aster_testnet)
            platform_display = "Aster"
        else:
            logger.error(f"❌ Unsupported platform: {platform}")
            return None
        
        # Get account information
        account = await client.get_account_info()
        
        # Get balance (account value)
        account_value = float(account.get('marginSummary', {}).get('accountValue', 0))
        
        # Get withdrawable balance
        withdrawable = float(account.get('withdrawable', 0))
        
        # Get positions
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
                    
                    # Calculate position value (unrealized PnL)
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
        
        # Close session
        await client.close_session()
        
        return {
            'name': name,
            'platform': platform_display,
            'address': client.address if hasattr(client, 'address') else 'N/A',
            'account_value': account_value,  # Total account value (including unrealized PnL)
            'withdrawable': withdrawable,     # Withdrawable balance
            'position_count': len(position_list),
            'positions': position_list,
            'total_position_value': total_position_value
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get {name} ({platform}) balance: {e}")
        return None


async def check_all_accounts():
    """Check actual balances of all accounts"""
    logger.info("=" * 100)
    logger.info("🔍 Get actual margin balances of all accounts from exchanges")
    logger.info("=" * 100)
    
    all_accounts = []
    
    # 1. Check Alpha Group
    logger.info("\n📊 Alpha Group (DeepSeek + Claude + Grok):")
    
    if settings.group_1_private_key:
        # Hyperliquid
        result = await get_account_balance(
            "Alpha Group",
            settings.group_1_private_key,
            "hyperliquid"
        )
        if result:
            all_accounts.append(result)
        
        # Aster
        result = await get_account_balance(
            "Alpha Group",
            settings.group_1_private_key,
            "aster"
        )
        if result:
            all_accounts.append(result)
    else:
        logger.warning("   ⚠️  GROUP_1_PRIVATE_KEY not configured")
    
    # 2. Check Beta Group
    logger.info("\n📊 Beta Group (GPT-4 + Gemini + Qwen):")
    
    if settings.group_2_private_key:
        # Hyperliquid
        result = await get_account_balance(
            "Beta Group",
            settings.group_2_private_key,
            "hyperliquid"
        )
        if result:
            all_accounts.append(result)
        
        # Aster
        result = await get_account_balance(
            "Beta Group",
            settings.group_2_private_key,
            "aster"
        )
        if result:
            all_accounts.append(result)
    else:
        logger.warning("   ⚠️  GROUP_2_PRIVATE_KEY not configured")
    
    # 3. Check individual AI traders
    logger.info("\n🎯 Individual AI Traders:")
    
    try:
        individual_configs = get_individual_traders_config()
        
        if individual_configs:
            for config in individual_configs:
                ai_name = config["ai_name"]
                private_key = config["private_key"]
                
                logger.info(f"\n   {ai_name}-Solo:")
                
                # Individual traders only trade on Aster platform
                result = await get_account_balance(
                    f"{ai_name}-Solo",
                    private_key,
                    "aster"
                )
                if result:
                    all_accounts.append(result)
        else:
            logger.info("   No individual AI traders configured")
    
    except ValueError as e:
        logger.error(f"   ❌ Configuration error: {e}")
    
    # Print detailed information
    if not all_accounts:
        logger.warning("\n⚠️  No configured accounts found")
        logger.info("\nPlease configure the following private keys in .env file:")
        logger.info("  - GROUP_1_PRIVATE_KEY (Alpha Group)")
        logger.info("  - GROUP_2_PRIVATE_KEY (Beta Group)")
        logger.info("  - INDIVIDUAL_<AI_NAME>_PRIVATE_KEY (Individual Traders)")
        return
    
    logger.info("\n" + "=" * 100)
    logger.info("💰 Account Actual Margin Details")
    logger.info("=" * 100)
    
    for account in all_accounts:
        logger.info(f"\n{'─' * 100}")
        logger.info(f"📍 {account['name']} - {account['platform']}")
        logger.info(f"{'─' * 100}")
        logger.info(f"   Address: {account['address']}")
        logger.info(f"   💰 Total Account Value: ${account['account_value']:.2f}")
        logger.info(f"   💵 Withdrawable Balance: ${account['withdrawable']:.2f}")
        
        if account['position_count'] > 0:
            logger.info(f"\n   📊 Position Details ({account['position_count']} positions):")
            for i, pos in enumerate(account['positions'], 1):
                logger.info(f"      {i}. {pos['coin']} {pos['side']}")
                logger.info(f"         Size: {pos['size']:.6f}")
                logger.info(f"         Entry Price: ${pos['entry_price']:,.2f}")
                logger.info(f"         Position Value: ${pos['position_value']:,.2f}")
                logger.info(f"         Unrealized PnL: ${pos['unrealized_pnl']:+.2f}")
            
            logger.info(f"\n   📊 Total Position Value: ${account['total_position_value']:,.2f}")
        else:
            logger.info(f"\n   📭 No Positions")
    
    # Statistical Summary
    logger.info("\n" + "=" * 100)
    logger.info("📊 Statistical Summary")
    logger.info("=" * 100)
    
    # Group by account type
    groups = {}
    individuals = {}
    
    for account in all_accounts:
        name = account['name']
        platform = account['platform']
        
        if '-Solo' in name:
            # Individual traders
            if name not in individuals:
                individuals[name] = {}
            individuals[name][platform] = account
        else:
            # AI groups
            if name not in groups:
                groups[name] = {}
            groups[name][platform] = account
    
    # Print AI group summary
    if groups:
        logger.info("\n📊 AI Group Account Summary:")
        for group_name, platforms in groups.items():
            logger.info(f"\n   {group_name}:")
            total_value = 0
            for platform, account in platforms.items():
                logger.info(f"      {platform:12s}: ${account['account_value']:>10.2f}")
                total_value += account['account_value']
            logger.info(f"      {'Total':12s}: ${total_value:>10.2f}")
    
    # Print individual trader summary
    if individuals:
        logger.info("\n🎯 Individual AI Trader Account Summary:")
        for trader_name, platforms in individuals.items():
            logger.info(f"\n   {trader_name}:")
            total_value = 0
            for platform, account in platforms.items():
                logger.info(f"      {platform:12s}: ${account['account_value']:>10.2f}")
                total_value += account['account_value']
            if len(platforms) > 1:
                logger.info(f"      {'Total':12s}: ${total_value:>10.2f}")
    
    # Summary by platform
    logger.info("\n💎 Platform Summary:")
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
        logger.info(f"      Account Count: {stats['account_count']}")
        logger.info(f"      Total Funds: ${stats['total_value']:,.2f}")
        logger.info(f"      Total Positions: {stats['total_positions']}")
    
    # Grand total
    total_all = sum(acc['account_value'] for acc in all_accounts)
    logger.info(f"\n💵 Total Funds Across All Accounts: ${total_all:,.2f}")
    
    logger.info("\n" + "=" * 100)


async def main():
    """Main function"""
    try:
        await check_all_accounts()
    except Exception as e:
        logger.error(f"❌ Check failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

