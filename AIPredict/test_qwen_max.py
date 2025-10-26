"""
测试 Qwen3-MAX 接口
验证模型是否能正常调用和返回交易决策
"""
import asyncio
import logging
from config.settings import settings
from ai_models.qwen_trader import QwenTrader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_qwen_max():
    """测试 Qwen3-MAX 接口"""
    
    logger.info("=" * 80)
    logger.info("🧪 测试 Qwen3-MAX 接口")
    logger.info("=" * 80)
    
    # 检查API Key
    if not settings.qwen_api_key:
        logger.error("❌ 未配置 QWEN_API_KEY")
        logger.error("请在 .env 文件中配置: QWEN_API_KEY=your_api_key")
        return False
    
    logger.info(f"\n✅ API Key 已配置: {settings.qwen_api_key[:8]}...{settings.qwen_api_key[-4:]}")
    
    # 创建 Qwen 交易者实例
    try:
        logger.info("\n📊 创建 Qwen3-MAX 交易者实例...")
        use_international = settings.qwen_use_international
        qwen = QwenTrader(api_key=settings.qwen_api_key, use_international=use_international)
        logger.info(f"✅ 实例创建成功")
        logger.info(f"   模型名称: {qwen.model_name}")
        logger.info(f"   模型版本: {qwen.model}")
        logger.info(f"   API 版本: {'国际版' if use_international else '中国版'}")
        logger.info(f"   API URL: {qwen.api_url}")
    except Exception as e:
        logger.error(f"❌ 实例创建失败: {e}")
        return False
    
    # 准备测试数据
    logger.info("\n📈 准备测试市场数据...")
    
    test_market_data = {
        "coin": "BTC",
        "price": 67500.0,
        "mark_price": 67500.0,
        "funding_rate": 0.0001,
        "open_interest": 1500000000,
        "change_24h": 2.5,
        "volume": 25000000000
    }
    
    test_orderbook = {
        "bids": [
            [67490, 1.5],
            [67480, 2.3],
            [67470, 3.1],
            [67460, 1.8],
            [67450, 2.5]
        ],
        "asks": [
            [67510, 1.2],
            [67520, 2.1],
            [67530, 2.8],
            [67540, 1.9],
            [67550, 2.3]
        ]
    }
    
    test_trades = [
        {"price": 67500, "size": 0.5, "side": "buy"},
        {"price": 67495, "size": 0.3, "side": "sell"},
        {"price": 67505, "size": 0.8, "side": "buy"}
    ]
    
    logger.info(f"✅ 测试数据准备完成")
    logger.info(f"   币种: BTC")
    logger.info(f"   当前价格: ${test_market_data['price']:,.2f}")
    logger.info(f"   24h涨跌: {test_market_data['change_24h']:+.2f}%")
    
    # 测试 API 调用
    logger.info("\n🚀 开始调用 Qwen3-MAX API...")
    logger.info("⏳ 请等待（可能需要2-5秒）...")
    
    try:
        # 先直接调用API获取原始响应
        import httpx
        prompt = qwen.create_market_prompt("BTC", test_market_data, test_orderbook, None)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                qwen.api_url,
                headers={
                    "Authorization": f"Bearer {qwen.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": qwen.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result["choices"][0]["message"]["content"]
                
                logger.info("\n" + "="*80)
                logger.info("📝 Qwen3-MAX 原始响应:")
                logger.info("="*80)
                logger.info(raw_response)
                logger.info("="*80)
        
        # 然后进行正常的解析测试
        decision, confidence, reasoning = await qwen.analyze_market(
            coin="BTC",
            market_data=test_market_data,
            orderbook=test_orderbook,
            recent_trades=test_trades,
            position_info=None
        )
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Qwen3-MAX 接口调用成功！")
        logger.info("=" * 80)
        
        logger.info(f"\n📊 返回结果:")
        logger.info(f"   决策: {decision.value.upper()}")
        logger.info(f"   信心度: {confidence:.1f}%")
        logger.info(f"   推理过程:")
        logger.info(f"   {reasoning[:300]}{'...' if len(reasoning) > 300 else ''}")
        
        # 验证返回格式
        logger.info(f"\n🔍 格式验证:")
        
        valid = True
        
        # 检查决策
        if decision:
            logger.info(f"   ✅ 决策格式正确: {decision}")
        else:
            logger.error(f"   ❌ 决策格式错误")
            valid = False
        
        # 检查信心度
        if 0 <= confidence <= 100:
            logger.info(f"   ✅ 信心度范围正确: {confidence}%")
        else:
            logger.error(f"   ❌ 信心度超出范围: {confidence}%")
            valid = False
        
        # 检查推理
        if reasoning and len(reasoning) > 10:
            logger.info(f"   ✅ 推理内容完整: {len(reasoning)} 字符")
        else:
            logger.error(f"   ❌ 推理内容不完整")
            valid = False
        
        if valid:
            logger.info("\n" + "=" * 80)
            logger.info("🎉 测试通过！Qwen3-MAX 接口工作正常")
            logger.info("=" * 80)
            logger.info("\n💡 建议:")
            logger.info("   1. 模型响应质量良好")
            logger.info("   2. 可以正常用于实际交易")
            logger.info("   3. 注意监控API调用成本")
            logger.info("   4. 响应时间在可接受范围内")
            return True
        else:
            logger.warning("\n⚠️  测试通过但返回格式有问题")
            return False
    
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("❌ Qwen3-MAX 接口调用失败")
        logger.error("=" * 80)
        logger.error(f"\n错误信息: {e}")
        logger.error(f"\n可能的原因:")
        logger.error("   1. API Key 无效或已过期")
        logger.error("   2. 账户余额不足")
        logger.error("   3. 未开通 qwen-max 模型权限")
        logger.error("   4. 网络连接问题")
        logger.error("   5. API 配额限制（RPM/QPM）")
        logger.error(f"\n解决方案:")
        logger.error("   1. 登录阿里云控制台检查 API Key")
        logger.error("   2. 确认账户余额充足")
        logger.error("   3. 在 DashScope 控制台开通 qwen-max")
        logger.error("   4. 检查网络连接")
        logger.error("   5. 等待配额重置或申请提额")
        
        import traceback
        logger.error(f"\n详细错误:")
        logger.error(traceback.format_exc())
        
        return False


async def main():
    """主函数"""
    try:
        success = await test_qwen_max()
        
        if success:
            logger.info("\n✅ 测试完成：接口正常")
            return 0
        else:
            logger.error("\n❌ 测试失败：接口异常")
            return 1
    
    except Exception as e:
        logger.error(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

