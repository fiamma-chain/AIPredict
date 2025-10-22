"""
交易策略使用示例
展示如何创建、导入、导出和使用交易策略
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading.strategy import (
    TradingStrategy, StrategyType, TimeFrame,
    RiskManagement, PositionSizing, IndicatorConfig,
    EntryCondition, ExitCondition, MarketCondition,
    get_strategy_manager, create_aggressive_swing_strategy
)


def example_1_use_predefined_strategy():
    """示例1: 使用预定义策略"""
    print("=" * 60)
    print("示例1: 使用预定义策略")
    print("=" * 60)
    
    manager = get_strategy_manager()
    
    # 列出所有策略
    print("\n所有可用策略:")
    for strategy in manager.list_strategies():
        print(f"  • {strategy.name} ({strategy.strategy_type.value})")
        print(f"    止损: {strategy.risk_management.stop_loss_pct}%")
        print(f"    止盈: {strategy.risk_management.take_profit_pct}%")
        print()
    
    # 获取特定策略
    strategy = manager.get_strategy("aggressive_swing_v1")
    if strategy:
        print(f"选择策略: {strategy.name}")
        print(f"描述: {strategy.description}")


def example_2_create_custom_strategy():
    """示例2: 创建自定义策略"""
    print("\n" + "=" * 60)
    print("示例2: 创建自定义策略")
    print("=" * 60)
    
    # 创建RSI+MACD策略
    my_strategy = TradingStrategy(
        strategy_id="rsi_macd_combo_v1",
        name="RSI+MACD组合策略",
        version="1.0.0",
        description="结合RSI超卖/超买信号和MACD趋势确认",
        author="交易员小明",
        strategy_type=StrategyType.TREND_FOLLOWING,
        timeframe=TimeFrame.H1,
        applicable_coins=["BTC", "ETH"],
        applicable_platforms=["hyperliquid", "aster"],
        min_confidence=65.0,
        
        # 风险管理
        risk_management=RiskManagement(
            stop_loss_pct=4.0,
            take_profit_pct=8.0,
            trailing_stop=True,
            trailing_stop_pct=2.5,
            max_position_size_pct=12.0,
            max_daily_loss_pct=6.0,
            risk_reward_ratio=2.0
        ),
        
        # 仓位管理
        position_sizing=PositionSizing(
            method="fixed_percentage",
            base_size_pct=8.0,
            use_confidence=True,
            confidence_multiplier=1.2,
            max_positions=3
        ),
        
        # 技术指标
        indicators=[
            IndicatorConfig(
                name="RSI",
                enabled=True,
                params={
                    "period": 14,
                    "overbought": 70,
                    "oversold": 30
                },
                weight=0.85
            ),
            IndicatorConfig(
                name="MACD",
                enabled=True,
                params={
                    "fast": 12,
                    "slow": 26,
                    "signal": 9
                },
                weight=0.75
            ),
            IndicatorConfig(
                name="EMA",
                enabled=True,
                params={
                    "period": 50
                },
                weight=0.6
            )
        ],
        
        # 市场条件过滤
        market_conditions=MarketCondition(
            min_volume_24h=100000000,  # 1亿美元
            max_spread_pct=0.5,
            allowed_volatility_range=[0.5, 5.0]
        ),
        
        tags=["rsi", "macd", "trend", "combo"]
    )
    
    print(f"\n✅ 创建策略: {my_strategy.name}")
    print(f"   策略ID: {my_strategy.strategy_id}")
    print(f"   类型: {my_strategy.strategy_type.value}")
    print(f"   时间周期: {my_strategy.timeframe.value}")
    print(f"   适用币种: {', '.join(my_strategy.applicable_coins)}")
    print(f"   风险管理: 止损{my_strategy.risk_management.stop_loss_pct}% / 止盈{my_strategy.risk_management.take_profit_pct}%")
    print(f"   技术指标: {len(my_strategy.indicators)} 个")
    
    return my_strategy


def example_3_add_entry_exit_conditions(strategy):
    """示例3: 添加进场和出场条件"""
    print("\n" + "=" * 60)
    print("示例3: 添加进场和出场条件")
    print("=" * 60)
    
    # 做多进场条件
    long_entry = [
        EntryCondition(
            condition_type="indicator",
            operator="<",
            value=30,
            required=True,
            description="RSI 小于 30 (超卖区域)"
        ),
        EntryCondition(
            condition_type="indicator",
            operator="cross_above",
            value="signal_line",
            required=True,
            description="MACD 上穿信号线 (看涨)"
        ),
        EntryCondition(
            condition_type="price",
            operator=">",
            value="EMA_50",
            required=False,
            description="价格在50日EMA上方 (确认上升趋势)"
        ),
        EntryCondition(
            condition_type="volume",
            operator=">",
            value="1.5x_avg",
            required=False,
            description="成交量放大 (资金流入)"
        )
    ]
    
    # 做空进场条件
    short_entry = [
        EntryCondition(
            condition_type="indicator",
            operator=">",
            value=70,
            required=True,
            description="RSI 大于 70 (超买区域)"
        ),
        EntryCondition(
            condition_type="indicator",
            operator="cross_below",
            value="signal_line",
            required=True,
            description="MACD 下穿信号线 (看跌)"
        ),
        EntryCondition(
            condition_type="price",
            operator="<",
            value="EMA_50",
            required=False,
            description="价格在50日EMA下方 (确认下降趋势)"
        )
    ]
    
    # 做多出场条件
    long_exit = [
        ExitCondition(
            condition_type="price",
            operator="<",
            value="stop_loss",
            priority=10,
            description="触及止损位 (最高优先级)"
        ),
        ExitCondition(
            condition_type="price",
            operator=">",
            value="take_profit",
            priority=9,
            description="触及止盈位"
        ),
        ExitCondition(
            condition_type="indicator",
            operator=">",
            value=70,
            priority=5,
            description="RSI 超过 70 (超买，考虑获利)"
        ),
        ExitCondition(
            condition_type="indicator",
            operator="cross_below",
            value="signal_line",
            priority=6,
            description="MACD 下穿信号线 (趋势反转)"
        )
    ]
    
    # 做空出场条件
    short_exit = [
        ExitCondition(
            condition_type="price",
            operator=">",
            value="stop_loss",
            priority=10,
            description="触及止损位"
        ),
        ExitCondition(
            condition_type="price",
            operator="<",
            value="take_profit",
            priority=9,
            description="触及止盈位"
        ),
        ExitCondition(
            condition_type="indicator",
            operator="<",
            value=30,
            priority=5,
            description="RSI 低于 30 (超卖，考虑获利)"
        )
    ]
    
    # 添加到策略
    strategy.entry_conditions = {
        "long": long_entry,
        "short": short_entry
    }
    strategy.exit_conditions = {
        "long": long_exit,
        "short": short_exit
    }
    
    print(f"\n✅ 已添加进场条件:")
    print(f"   做多: {len(long_entry)} 个条件")
    print(f"   做空: {len(short_entry)} 个条件")
    print(f"\n✅ 已添加出场条件:")
    print(f"   做多: {len(long_exit)} 个条件")
    print(f"   做空: {len(short_exit)} 个条件")
    
    return strategy


def example_4_export_strategy(strategy):
    """示例4: 导出策略"""
    print("\n" + "=" * 60)
    print("示例4: 导出策略")
    print("=" * 60)
    
    # 创建示例目录
    os.makedirs("example_strategies", exist_ok=True)
    
    # 导出为JSON文件
    filename = f"example_strategies/{strategy.strategy_id}.json"
    strategy.save_to_file(filename)
    print(f"\n✅ 策略已导出到: {filename}")
    
    # 显示部分JSON内容
    print(f"\nJSON 预览 (前20行):")
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()[:20]
        for line in lines:
            print(f"  {line.rstrip()}")
    print("  ...")
    
    return filename


def example_5_import_strategy(filename):
    """示例5: 导入策略"""
    print("\n" + "=" * 60)
    print("示例5: 导入策略")
    print("=" * 60)
    
    # 从文件导入
    imported_strategy = TradingStrategy.load_from_file(filename)
    
    print(f"\n✅ 成功导入策略:")
    print(f"   名称: {imported_strategy.name}")
    print(f"   版本: {imported_strategy.version}")
    print(f"   作者: {imported_strategy.author}")
    print(f"   创建时间: {imported_strategy.created_at}")
    
    # 添加到管理器
    manager = get_strategy_manager()
    manager.add_strategy(imported_strategy)
    
    print(f"\n✅ 策略已添加到管理器")
    print(f"   当前策略总数: {len(manager.list_strategies())}")
    
    return imported_strategy


def example_6_generate_ai_prompt(strategy):
    """示例6: 生成AI提示词"""
    print("\n" + "=" * 60)
    print("示例6: 生成AI提示词")
    print("=" * 60)
    
    # 模拟市场数据
    market_data = {
        "price": 67234.50,
        "volume": 125000000,
        "change_24h": 2.3,
        "rsi": 45,
        "macd": 120,
        "signal": 110,
        "ema_50": 66800
    }
    
    # 生成提示词
    prompt = strategy.get_prompt_for_ai(market_data, "BTC")
    
    print("\n生成的AI提示词:")
    print("-" * 60)
    print(prompt)
    print("-" * 60)


def example_7_strategy_validation():
    """示例7: 策略验证"""
    print("\n" + "=" * 60)
    print("示例7: 策略验证")
    print("=" * 60)
    
    manager = get_strategy_manager()
    
    # 获取策略
    strategy = manager.get_strategy("rsi_macd_combo_v1")
    if not strategy:
        print("⚠️  策略不存在")
        return
    
    # 验证币种
    coins_to_test = ["BTC", "ETH", "SOL"]
    print("\n验证适用币种:")
    for coin in coins_to_test:
        is_valid = strategy.validate_for_coin(coin)
        status = "✅" if is_valid else "❌"
        print(f"  {status} {coin}: {'可用' if is_valid else '不可用'}")
    
    # 验证平台
    platforms_to_test = ["hyperliquid", "aster", "binance"]
    print("\n验证适用平台:")
    for platform in platforms_to_test:
        is_valid = strategy.validate_for_platform(platform)
        status = "✅" if is_valid else "❌"
        print(f"  {status} {platform}: {'可用' if is_valid else '不可用'}")


def example_8_strategy_cloning():
    """示例8: 策略克隆和修改"""
    print("\n" + "=" * 60)
    print("示例8: 策略克隆和修改")
    print("=" * 60)
    
    manager = get_strategy_manager()
    
    # 获取原始策略
    original = manager.get_strategy("aggressive_swing_v1")
    if not original:
        print("⚠️  原始策略不存在")
        return
    
    print(f"\n原始策略: {original.name}")
    print(f"  止损: {original.risk_management.stop_loss_pct}%")
    print(f"  止盈: {original.risk_management.take_profit_pct}%")
    
    # 克隆策略
    modified = original.clone()
    modified.name = "改进版激进波段策略"
    modified.risk_management.stop_loss_pct = 6.0
    modified.risk_management.take_profit_pct = 12.0
    modified.position_sizing.base_size_pct = 12.0
    
    print(f"\n克隆策略: {modified.name}")
    print(f"  策略ID: {modified.strategy_id}")
    print(f"  止损: {modified.risk_management.stop_loss_pct}%")
    print(f"  止盈: {modified.risk_management.take_profit_pct}%")
    
    # 添加到管理器
    manager.add_strategy(modified)
    print(f"\n✅ 克隆策略已添加到管理器")


def example_9_strategy_performance():
    """示例9: 记录策略性能"""
    print("\n" + "=" * 60)
    print("示例9: 记录策略性能")
    print("=" * 60)
    
    manager = get_strategy_manager()
    strategy = manager.get_strategy("aggressive_swing_v1")
    
    if not strategy:
        print("⚠️  策略不存在")
        return
    
    # 模拟性能数据
    from datetime import datetime
    strategy.performance_stats = {
        "total_trades": 150,
        "winning_trades": 95,
        "losing_trades": 55,
        "win_rate": 63.33,
        "total_pnl": 2450.75,
        "roi": 24.5,
        "max_drawdown": -4.2,
        "sharpe_ratio": 1.85,
        "profit_factor": 1.72,
        "avg_win": 42.50,
        "avg_loss": -24.30,
        "largest_win": 156.80,
        "largest_loss": -89.20,
        "start_date": "2025-01-01",
        "end_date": "2025-10-22",
        "last_updated": datetime.now().isoformat()
    }
    
    print(f"\n策略: {strategy.name}")
    print(f"性能统计:")
    for key, value in strategy.performance_stats.items():
        if key != "last_updated":
            print(f"  • {key}: {value}")
    
    # 保存
    filename = f"example_strategies/{strategy.strategy_id}_with_performance.json"
    strategy.save_to_file(filename)
    print(f"\n✅ 性能数据已保存到: {filename}")


def main():
    """运行所有示例"""
    print("\n")
    print("🎯 " + "=" * 58)
    print("🎯  交易策略使用示例")
    print("🎯 " + "=" * 58)
    
    # 示例1: 使用预定义策略
    example_1_use_predefined_strategy()
    
    # 示例2: 创建自定义策略
    my_strategy = example_2_create_custom_strategy()
    
    # 示例3: 添加进场出场条件
    my_strategy = example_3_add_entry_exit_conditions(my_strategy)
    
    # 示例4: 导出策略
    filename = example_4_export_strategy(my_strategy)
    
    # 示例5: 导入策略
    imported_strategy = example_5_import_strategy(filename)
    
    # 示例6: 生成AI提示词
    example_6_generate_ai_prompt(imported_strategy)
    
    # 示例7: 策略验证
    example_7_strategy_validation()
    
    # 示例8: 策略克隆
    example_8_strategy_cloning()
    
    # 示例9: 记录性能
    example_9_strategy_performance()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成")
    print("=" * 60)
    print(f"\n导出的策略文件位于: ./example_strategies/")
    print(f"总策略数: {len(get_strategy_manager().list_strategies())}")


if __name__ == "__main__":
    main()

