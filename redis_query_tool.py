#!/usr/bin/env python3
"""
Redis 数据查询工具
用于查询、导出和管理 AI 响应数据
"""
import argparse
import json
import sys
from datetime import datetime
from typing import Optional

from config.settings import settings
from utils.redis_manager import RedisManager


def print_json(data):
    """格式化打印 JSON"""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def format_response(response: dict, index: int = None):
    """格式化单条响应"""
    prefix = f"[{index}] " if index is not None else ""
    print(f"\n{prefix}{'='*60}")
    print(f"时间: {response.get('timestamp', 'N/A')}")
    print(f"平台: {response.get('platform', 'N/A')}")
    print(f"模型: {response.get('ai_model', 'N/A')}")
    print(f"币种: {response.get('coin', 'N/A')}")
    print(f"决策: {response.get('decision', 'N/A')}")
    print(f"信心: {response.get('confidence', 0):.1f}%")
    print(f"理由: {response.get('reasoning', 'N/A')}")
    print("="*60)


def cmd_stats(redis_mgr: RedisManager):
    """显示统计信息"""
    print("\n📊 Redis 数据统计")
    print("="*60)
    
    stats = redis_mgr.get_statistics()
    
    print(f"\n总键数: {stats.get('total_keys', 0)}")
    print(f"总响应数: {stats.get('total_responses', 0)}")
    
    platforms = stats.get('platforms', {})
    if platforms:
        print("\n平台分布:")
        for platform, count in platforms.items():
            print(f"  • {platform}: {count} 条")
    
    ai_models = stats.get('ai_models', {})
    if ai_models:
        print("\nAI 模型分布:")
        for model, count in ai_models.items():
            print(f"  • {model}: {count} 条")
    
    coins = stats.get('coins', {})
    if coins:
        print("\n币种分布:")
        for coin, count in coins.items():
            print(f"  • {coin}: {count} 条")
    
    print("="*60)


def cmd_platforms(redis_mgr: RedisManager):
    """列出所有平台"""
    print("\n🏢 所有平台")
    print("="*60)
    
    platforms = redis_mgr.get_all_platforms()
    if platforms:
        for i, platform in enumerate(platforms, 1):
            print(f"{i}. {platform}")
    else:
        print("没有找到任何平台数据")
    
    print("="*60)


def cmd_models(redis_mgr: RedisManager, platform: Optional[str] = None):
    """列出 AI 模型"""
    if platform:
        print(f"\n🤖 平台 '{platform}' 的 AI 模型")
    else:
        print("\n🤖 所有 AI 模型")
    print("="*60)
    
    models = redis_mgr.get_all_ai_models(platform)
    if models:
        for i, model in enumerate(models, 1):
            print(f"{i}. {model}")
    else:
        print("没有找到任何 AI 模型数据")
    
    print("="*60)


def cmd_coins(redis_mgr: RedisManager, platform: Optional[str] = None, 
              ai_model: Optional[str] = None):
    """列出币种"""
    if platform and ai_model:
        print(f"\n💰 平台 '{platform}' - 模型 '{ai_model}' 的币种")
    elif platform:
        print(f"\n💰 平台 '{platform}' 的币种")
    else:
        print("\n💰 所有币种")
    print("="*60)
    
    coins = redis_mgr.get_all_coins(platform, ai_model)
    if coins:
        for i, coin in enumerate(coins, 1):
            print(f"{i}. {coin}")
    else:
        print("没有找到任何币种数据")
    
    print("="*60)


def cmd_query(redis_mgr: RedisManager, platform: str, ai_model: str, 
              coin: str, limit: int = 10):
    """查询响应数据"""
    print(f"\n🔍 查询: {platform} - {ai_model} - {coin}")
    print("="*60)
    
    # 获取总数
    total = redis_mgr.get_response_count(platform, ai_model, coin)
    print(f"总记录数: {total}")
    
    # 获取数据
    responses = redis_mgr.get_ai_responses(platform, ai_model, coin, limit)
    
    if responses:
        print(f"\n显示最近 {len(responses)} 条记录:")
        for i, response in enumerate(responses, 1):
            format_response(response, i)
    else:
        print("\n没有找到任何数据")
    
    print("="*60)


def cmd_export(redis_mgr: RedisManager, platform: str, ai_model: str, 
               coin: str, output: str, limit: int = 1000):
    """导出数据到 JSON 文件"""
    print(f"\n📤 导出: {platform} - {ai_model} - {coin}")
    print("="*60)
    
    responses = redis_mgr.get_ai_responses(platform, ai_model, coin, limit)
    
    if responses:
        output_data = {
            "platform": platform,
            "ai_model": ai_model,
            "coin": coin,
            "export_time": datetime.now().isoformat(),
            "total_records": len(responses),
            "responses": responses
        }
        
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 已导出 {len(responses)} 条记录到 {output}")
    else:
        print("❌ 没有找到任何数据")
    
    print("="*60)


def cmd_clear(redis_mgr: RedisManager, platform: Optional[str] = None,
              ai_model: Optional[str] = None, coin: Optional[str] = None,
              clear_all: bool = False):
    """清除数据"""
    if clear_all:
        confirm = input("⚠️  确认清除所有数据？(yes/no): ")
        if confirm.lower() != 'yes':
            print("操作已取消")
            return
        
        deleted = redis_mgr.clear_responses()
        print(f"✅ 已清除 {deleted} 个键的数据")
    
    elif platform:
        if ai_model and coin:
            print(f"\n🗑️  清除: {platform} - {ai_model} - {coin}")
        elif ai_model:
            print(f"\n🗑️  清除: {platform} - {ai_model} - 所有币种")
        else:
            print(f"\n🗑️  清除: {platform} - 所有数据")
        
        confirm = input("确认清除？(yes/no): ")
        if confirm.lower() != 'yes':
            print("操作已取消")
            return
        
        deleted = redis_mgr.clear_responses(platform, ai_model, coin)
        print(f"✅ 已清除 {deleted} 个键的数据")
    
    else:
        print("❌ 请指定要清除的范围（--platform 或 --all）")


def main():
    parser = argparse.ArgumentParser(
        description="Redis 数据查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看统计信息
  python redis_query_tool.py stats
  
  # 查看所有平台
  python redis_query_tool.py platforms
  
  # 查看指定平台的 AI 模型
  python redis_query_tool.py models hyperliquid
  
  # 查询数据
  python redis_query_tool.py query hyperliquid DeepSeek BTC --limit 10
  
  # 导出数据
  python redis_query_tool.py export hyperliquid DeepSeek BTC --output data.json
  
  # 清除数据
  python redis_query_tool.py clear --platform hyperliquid --ai-model DeepSeek
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # stats 命令
    subparsers.add_parser('stats', help='显示统计信息')
    
    # platforms 命令
    subparsers.add_parser('platforms', help='列出所有平台')
    
    # models 命令
    parser_models = subparsers.add_parser('models', help='列出 AI 模型')
    parser_models.add_argument('platform', nargs='?', help='平台名称（可选）')
    
    # coins 命令
    parser_coins = subparsers.add_parser('coins', help='列出币种')
    parser_coins.add_argument('--platform', help='平台名称')
    parser_coins.add_argument('--ai-model', help='AI 模型名称')
    
    # query 命令
    parser_query = subparsers.add_parser('query', help='查询响应数据')
    parser_query.add_argument('platform', help='平台名称')
    parser_query.add_argument('ai_model', help='AI 模型名称')
    parser_query.add_argument('coin', help='币种')
    parser_query.add_argument('--limit', type=int, default=10, help='限制数量（默认10）')
    
    # export 命令
    parser_export = subparsers.add_parser('export', help='导出数据到 JSON 文件')
    parser_export.add_argument('platform', help='平台名称')
    parser_export.add_argument('ai_model', help='AI 模型名称')
    parser_export.add_argument('coin', help='币种')
    parser_export.add_argument('--output', required=True, help='输出文件名')
    parser_export.add_argument('--limit', type=int, default=1000, help='限制数量（默认1000）')
    
    # clear 命令
    parser_clear = subparsers.add_parser('clear', help='清除数据')
    parser_clear.add_argument('--platform', help='平台名称')
    parser_clear.add_argument('--ai-model', help='AI 模型名称')
    parser_clear.add_argument('--coin', help='币种')
    parser_clear.add_argument('--all', action='store_true', help='清除所有数据')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 连接到 Redis
    redis_mgr = RedisManager(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password if settings.redis_password else None
    )
    
    if not redis_mgr.connect():
        print("❌ 无法连接到 Redis")
        sys.exit(1)
    
    try:
        # 执行命令
        if args.command == 'stats':
            cmd_stats(redis_mgr)
        
        elif args.command == 'platforms':
            cmd_platforms(redis_mgr)
        
        elif args.command == 'models':
            cmd_models(redis_mgr, args.platform)
        
        elif args.command == 'coins':
            cmd_coins(redis_mgr, args.platform, getattr(args, 'ai_model', None))
        
        elif args.command == 'query':
            cmd_query(redis_mgr, args.platform, args.ai_model, args.coin, args.limit)
        
        elif args.command == 'export':
            cmd_export(redis_mgr, args.platform, args.ai_model, args.coin, 
                      args.output, args.limit)
        
        elif args.command == 'clear':
            cmd_clear(redis_mgr, args.platform, getattr(args, 'ai_model', None),
                     args.coin, args.all)
    
    finally:
        redis_mgr.disconnect()


if __name__ == '__main__':
    main()

