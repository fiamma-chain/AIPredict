#!/usr/bin/env python3
"""
交易策略命令行管理工具
"""
import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from trading.strategy import (
    get_strategy_manager,
    TradingStrategy,
    StrategyType
)


def cmd_list(args):
    """列出所有策略"""
    manager = get_strategy_manager()
    
    # 过滤策略
    strategies = manager.list_strategies()
    if args.type:
        try:
            strategy_type = StrategyType(args.type)
            strategies = [s for s in strategies if s.strategy_type == strategy_type]
        except ValueError:
            print(f"❌ 无效的策略类型: {args.type}")
            return
    
    if not strategies:
        print("没有找到策略")
        return
    
    print(f"\n📊 找到 {len(strategies)} 个策略:\n")
    print(f"{'ID':<25} {'名称':<20} {'类型':<15} {'止损%':<8} {'止盈%':<8}")
    print("=" * 85)
    
    for strategy in strategies:
        print(f"{strategy.strategy_id:<25} "
              f"{strategy.name:<20} "
              f"{strategy.strategy_type.value:<15} "
              f"{strategy.risk_management.stop_loss_pct:<8.1f} "
              f"{strategy.risk_management.take_profit_pct:<8.1f}")


def cmd_show(args):
    """显示策略详情"""
    manager = get_strategy_manager()
    strategy = manager.get_strategy(args.strategy_id)
    
    if not strategy:
        print(f"❌ 策略不存在: {args.strategy_id}")
        return
    
    print(f"\n📋 策略详情")
    print("=" * 60)
    print(f"ID: {strategy.strategy_id}")
    print(f"名称: {strategy.name}")
    print(f"版本: {strategy.version}")
    print(f"类型: {strategy.strategy_type.value}")
    print(f"时间周期: {strategy.timeframe.value}")
    print(f"作者: {strategy.author or '未知'}")
    print(f"描述: {strategy.description}")
    print(f"创建时间: {strategy.created_at}")
    print(f"更新时间: {strategy.updated_at}")
    
    print(f"\n💰 风险管理:")
    rm = strategy.risk_management
    print(f"  止损: {rm.stop_loss_pct}%")
    print(f"  止盈: {rm.take_profit_pct}%")
    print(f"  移动止损: {'是' if rm.trailing_stop else '否'}")
    if rm.trailing_stop:
        print(f"  移动止损: {rm.trailing_stop_pct}%")
    print(f"  风险回报比: {rm.risk_reward_ratio:.1f}")
    print(f"  最大仓位: {rm.max_position_size_pct}%")
    
    print(f"\n📊 仓位管理:")
    ps = strategy.position_sizing
    print(f"  方法: {ps.method}")
    print(f"  基础仓位: {ps.base_size_pct}%")
    print(f"  使用信心度调整: {'是' if ps.use_confidence else '否'}")
    print(f"  最大持仓数: {ps.max_positions}")
    
    if strategy.indicators:
        print(f"\n📈 技术指标 ({len(strategy.indicators)} 个):")
        for ind in strategy.indicators:
            status = "✅" if ind.enabled else "❌"
            print(f"  {status} {ind.name} (权重: {ind.weight:.2f})")
            if ind.params:
                print(f"     参数: {ind.params}")
    
    if strategy.tags:
        print(f"\n🏷️  标签: {', '.join(strategy.tags)}")
    
    print(f"\n🎯 适用范围:")
    print(f"  币种: {', '.join(strategy.applicable_coins) if strategy.applicable_coins else '全部'}")
    print(f"  平台: {', '.join(strategy.applicable_platforms) if strategy.applicable_platforms else '全部'}")
    
    if strategy.performance_stats:
        print(f"\n📊 性能统计:")
        for key, value in strategy.performance_stats.items():
            print(f"  {key}: {value}")


def cmd_export(args):
    """导出策略"""
    manager = get_strategy_manager()
    strategy = manager.get_strategy(args.strategy_id)
    
    if not strategy:
        print(f"❌ 策略不存在: {args.strategy_id}")
        return
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    strategy.save_to_file(str(output_path))
    print(f"✅ 策略已导出到: {output_path}")
    print(f"   文件大小: {output_path.stat().st_size} 字节")


def cmd_import(args):
    """导入策略"""
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return
    
    try:
        manager = get_strategy_manager()
        strategy = manager.import_strategy(str(input_path))
        
        print(f"✅ 成功导入策略:")
        print(f"   ID: {strategy.strategy_id}")
        print(f"   名称: {strategy.name}")
        print(f"   版本: {strategy.version}")
        print(f"   类型: {strategy.strategy_type.value}")
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")


def cmd_validate(args):
    """验证策略文件"""
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return
    
    try:
        strategy = TradingStrategy.load_from_file(str(input_path))
        
        print(f"✅ 策略文件验证通过")
        print(f"   ID: {strategy.strategy_id}")
        print(f"   名称: {strategy.name}")
        print(f"   版本: {strategy.version}")
        
        # 验证关键字段
        errors = []
        
        if strategy.risk_management.stop_loss_pct <= 0:
            errors.append("止损百分比必须大于0")
        
        if strategy.risk_management.take_profit_pct <= 0:
            errors.append("止盈百分比必须大于0")
        
        if strategy.risk_management.risk_reward_ratio < 1:
            errors.append("风险回报比应该至少为1")
        
        if strategy.min_confidence < 0 or strategy.min_confidence > 100:
            errors.append("最小信心度必须在0-100之间")
        
        if errors:
            print(f"\n⚠️  发现 {len(errors)} 个警告:")
            for error in errors:
                print(f"   • {error}")
        else:
            print("\n✅ 所有验证通过")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")


def cmd_delete(args):
    """删除策略"""
    manager = get_strategy_manager()
    strategy = manager.get_strategy(args.strategy_id)
    
    if not strategy:
        print(f"❌ 策略不存在: {args.strategy_id}")
        return
    
    if not args.force:
        confirm = input(f"确认删除策略 '{strategy.name}'? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ 取消删除")
            return
    
    manager.remove_strategy(args.strategy_id)
    print(f"✅ 已删除策略: {strategy.name}")


def cmd_clone(args):
    """克隆策略"""
    manager = get_strategy_manager()
    strategy = manager.get_strategy(args.strategy_id)
    
    if not strategy:
        print(f"❌ 策略不存在: {args.strategy_id}")
        return
    
    # 克隆策略
    new_strategy = strategy.clone()
    
    # 如果提供了新名称，使用新名称
    if args.new_name:
        new_strategy.name = args.new_name
    
    # 添加到管理器
    manager.add_strategy(new_strategy)
    
    print(f"✅ 成功克隆策略:")
    print(f"   原策略: {strategy.name} ({strategy.strategy_id})")
    print(f"   新策略: {new_strategy.name} ({new_strategy.strategy_id})")


def cmd_export_all(args):
    """导出所有策略"""
    manager = get_strategy_manager()
    strategies = manager.list_strategies()
    
    if not strategies:
        print("没有策略可导出")
        return
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n导出 {len(strategies)} 个策略到 {output_dir}:")
    
    for strategy in strategies:
        filename = output_dir / f"{strategy.strategy_id}.json"
        strategy.save_to_file(str(filename))
        print(f"  ✅ {strategy.name} -> {filename}")
    
    print(f"\n✅ 所有策略已导出")


def main():
    parser = argparse.ArgumentParser(
        description="交易策略管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有策略
  python strategy_cli.py list
  
  # 列出特定类型的策略
  python strategy_cli.py list --type swing
  
  # 查看策略详情
  python strategy_cli.py show aggressive_swing_v1
  
  # 导出策略
  python strategy_cli.py export aggressive_swing_v1 my_strategy.json
  
  # 导入策略
  python strategy_cli.py import user_strategy.json
  
  # 验证策略文件
  python strategy_cli.py validate my_strategy.json
  
  # 克隆策略
  python strategy_cli.py clone aggressive_swing_v1 --new-name "我的策略"
  
  # 删除策略
  python strategy_cli.py delete my_custom_strategy_v1
  
  # 导出所有策略
  python strategy_cli.py export-all ./strategies
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # list 命令
    parser_list = subparsers.add_parser('list', help='列出所有策略')
    parser_list.add_argument('--type', help='按类型过滤')
    parser_list.set_defaults(func=cmd_list)
    
    # show 命令
    parser_show = subparsers.add_parser('show', help='显示策略详情')
    parser_show.add_argument('strategy_id', help='策略ID')
    parser_show.set_defaults(func=cmd_show)
    
    # export 命令
    parser_export = subparsers.add_parser('export', help='导出策略')
    parser_export.add_argument('strategy_id', help='策略ID')
    parser_export.add_argument('output', help='输出文件路径')
    parser_export.set_defaults(func=cmd_export)
    
    # import 命令
    parser_import = subparsers.add_parser('import', help='导入策略')
    parser_import.add_argument('input', help='输入文件路径')
    parser_import.set_defaults(func=cmd_import)
    
    # validate 命令
    parser_validate = subparsers.add_parser('validate', help='验证策略文件')
    parser_validate.add_argument('input', help='输入文件路径')
    parser_validate.set_defaults(func=cmd_validate)
    
    # delete 命令
    parser_delete = subparsers.add_parser('delete', help='删除策略')
    parser_delete.add_argument('strategy_id', help='策略ID')
    parser_delete.add_argument('--force', action='store_true', help='强制删除，不确认')
    parser_delete.set_defaults(func=cmd_delete)
    
    # clone 命令
    parser_clone = subparsers.add_parser('clone', help='克隆策略')
    parser_clone.add_argument('strategy_id', help='策略ID')
    parser_clone.add_argument('--new-name', help='新策略名称')
    parser_clone.set_defaults(func=cmd_clone)
    
    # export-all 命令
    parser_export_all = subparsers.add_parser('export-all', help='导出所有策略')
    parser_export_all.add_argument('output_dir', help='输出目录')
    parser_export_all.set_defaults(func=cmd_export_all)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行命令
    args.func(args)


if __name__ == '__main__':
    main()

