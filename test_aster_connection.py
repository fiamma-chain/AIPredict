"""
测试 Aster 客户端连接
验证 API 连接和基本功能是否正常
"""
import asyncio
import sys
from trading.aster.client import AsterClient

# 测试用私钥（请替换为你的 API Wallet 私钥）
# ⚠️ 这只是示例，实际使用时应从环境变量读取
TEST_PRIVATE_KEY = "0x你的API_Wallet私钥"  # 请替换为实际私钥


async def test_public_endpoints():
    """测试公共端点（不需要私钥）"""
    print("\n" + "="*60)
    print("📊 测试 AsterDex 公共 API 端点")
    print("="*60)
    
    # 使用任意私钥初始化（公共端点不需要有效私钥）
    client = AsterClient(
        private_key="0x0000000000000000000000000000000000000000000000000000000000000001",
        testnet=False
    )
    
    try:
        # 测试 1: 获取 BTC 市场数据
        print("\n1️⃣ 测试获取 BTC 市场数据...")
        try:
            market_data = await client.get_market_data("BTC")
            print(f"✅ BTC 当前价格: ${market_data['price']:,.2f}")
            print(f"   24h 涨跌: {market_data['change_24h']:+.2f}%")
            print(f"   24h 成交量: ${market_data['volume']:,.0f}")
        except Exception as e:
            print(f"❌ 获取市场数据失败: {e}")
        
        # 测试 2: 获取订单簿
        print("\n2️⃣ 测试获取 BTC 订单簿...")
        try:
            orderbook = await client.get_orderbook("BTC")
            if orderbook['bids'] and orderbook['asks']:
                print(f"✅ 买一价: ${orderbook['bids'][0][0]:,.2f}")
                print(f"   卖一价: ${orderbook['asks'][0][0]:,.2f}")
                print(f"   价差: ${orderbook['asks'][0][0] - orderbook['bids'][0][0]:.2f}")
            else:
                print("❌ 订单簿为空")
        except Exception as e:
            print(f"❌ 获取订单簿失败: {e}")
        
        # 测试 3: 获取最近成交
        print("\n3️⃣ 测试获取最近成交...")
        try:
            trades = await client.get_recent_trades("BTC", limit=5)
            print(f"✅ 获取了 {len(trades)} 条最近成交记录")
            if trades:
                print(f"   最新成交价: ${float(trades[0].get('price', 0)):,.2f}")
        except Exception as e:
            print(f"❌ 获取最近成交失败: {e}")
        
        # 测试 4: 获取 K 线数据
        print("\n4️⃣ 测试获取 K 线数据...")
        try:
            candles = await client.get_candles("BTC", interval="15m", lookback=5)
            print(f"✅ 获取了 {len(candles)} 根 15分钟 K线")
            if candles:
                latest = candles[-1]
                print(f"   最新K线: O:{latest['open']:,.0f} H:{latest['high']:,.0f} "
                      f"L:{latest['low']:,.0f} C:{latest['close']:,.0f}")
        except Exception as e:
            print(f"❌ 获取K线数据失败: {e}")
        
        print("\n" + "="*60)
        print("✅ 公共 API 测试完成")
        print("="*60)
        
    finally:
        await client.close_session()


async def test_private_endpoints(private_key: str):
    """测试私有端点（需要有效的 API Wallet 私钥）"""
    print("\n" + "="*60)
    print("🔐 测试 AsterDex 私有 API 端点")
    print("="*60)
    
    if private_key == "0x你的API_Wallet私钥":
        print("\n⚠️  请先配置有效的 API Wallet 私钥")
        print("   1. 访问 https://www.asterdex.com/en/api-wallet")
        print("   2. 创建 API Wallet")
        print("   3. 将私钥填入本脚本的 TEST_PRIVATE_KEY 变量")
        return
    
    client = AsterClient(private_key=private_key, testnet=False)
    
    try:
        # 测试 1: 获取账户信息
        print("\n1️⃣ 测试获取账户信息...")
        try:
            account = await client.get_account_info()
            balance = account['marginSummary']['accountValue']
            print(f"✅ 账户余额: ${balance:,.2f} USDT")
            
            positions = account.get('assetPositions', [])
            print(f"   持仓数量: {len(positions)}")
        except Exception as e:
            print(f"❌ 获取账户信息失败: {e}")
            print("   请检查:")
            print("   - API Wallet 是否正确创建")
            print("   - 私钥是否正确")
            print("   - 是否有权限访问账户")
        
        # 测试 2: 获取历史成交
        print("\n2️⃣ 测试获取历史成交...")
        try:
            fills = await client.get_user_fills(limit=5)
            print(f"✅ 获取了 {len(fills)} 条历史成交记录")
        except Exception as e:
            print(f"❌ 获取历史成交失败: {e}")
        
        # 测试 3: 获取未成交订单
        print("\n3️⃣ 测试获取未成交订单...")
        try:
            orders = await client.get_open_orders()
            print(f"✅ 当前未成交订单: {len(orders)} 个")
        except Exception as e:
            print(f"❌ 获取未成交订单失败: {e}")
        
        print("\n" + "="*60)
        print("✅ 私有 API 测试完成")
        print("="*60)
        print("\n💡 如果所有测试都通过，说明 Aster 客户端配置正确！")
        print("   现在可以配置 .env 文件并运行 consensus_arena_multiplatform.py")
        
    finally:
        await client.close_session()


async def main():
    """主函数"""
    print("\n" + "🚀 " + "="*56)
    print("   AsterDex 客户端连接测试")
    print("="*60)
    print("\n📖 说明:")
    print("   1. 公共 API 测试不需要私钥，用于验证网络连接")
    print("   2. 私有 API 测试需要 API Wallet 私钥，用于验证账户访问")
    print("   3. 在 https://www.asterdex.com/en/api-wallet 创建 API Wallet")
    
    # 运行公共端点测试
    await test_public_endpoints()
    
    # 询问是否测试私有端点
    print("\n" + "="*60)
    print("是否要测试私有 API？(需要配置 API Wallet 私钥)")
    print("="*60)
    print("如果要测试，请编辑本文件，将 TEST_PRIVATE_KEY 设置为你的私钥")
    print("然后重新运行此脚本")
    
    # 如果配置了私钥，运行私有端点测试
    if TEST_PRIVATE_KEY != "0x你的API_Wallet私钥":
        await test_private_endpoints(TEST_PRIVATE_KEY)
    else:
        print("\n⏭️  跳过私有 API 测试（未配置私钥）")
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

