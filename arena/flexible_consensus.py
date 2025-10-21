"""
灵活分组的共识竞技场
支持用户自定义AI分组
"""
import asyncio
import logging
from typing import Dict, List, Optional
from config.settings import settings
from trading.hyperliquid.client import HyperliquidClient
from trading.risk_manager import RiskManager, RiskLimits
from arena.consensus_arena import ConsensusArena, AIGroup
from ai_models.claude_trader import ClaudeTrader
from ai_models.gpt_trader import GPTTrader
from ai_models.gemini_trader import GeminiTrader
from ai_models.qwen_trader import QwenTrader
from ai_models.grok_trader import GrokTrader
from ai_models.deepseek_trader import DeepSeekTrader

logger = logging.getLogger(__name__)


class FlexibleConsensusArena:
    """灵活分组的共识竞技场"""
    
    # AI模型配置映射
    AI_CONFIGS = {
        'claude': {
            'class': ClaudeTrader,
            'api_key_attr': 'claude_api_key',
            'private_key_attr': 'claude_private_key',
            'model': 'claude-3-5-sonnet-20241022',
            'display_name': 'Claude'
        },
        'gpt4': {
            'class': GPTTrader,
            'api_key_attr': 'openai_api_key',
            'private_key_attr': 'gpt_private_key',
            'model': 'gpt-4o',
            'display_name': 'GPT-4'
        },
        'gemini': {
            'class': GeminiTrader,
            'api_key_attr': 'gemini_api_key',
            'private_key_attr': 'gemini_private_key',
            'model': 'gemini-pro',
            'display_name': 'Gemini'
        },
        'qwen': {
            'class': QwenTrader,
            'api_key_attr': 'qwen_api_key',
            'private_key_attr': 'qwen_private_key',
            'model': 'qwen-max',
            'display_name': 'Qwen'
        },
        'grok': {
            'class': GrokTrader,
            'api_key_attr': 'grok_api_key',
            'private_key_attr': 'grok_private_key',
            'model': 'grok-beta',
            'display_name': 'Grok'
        },
        'deepseek': {
            'class': DeepSeekTrader,
            'api_key_attr': 'deepseek_api_key',
            'private_key_attr': 'deepseek_private_key',
            'model': 'deepseek-chat',
            'display_name': 'DeepSeek'
        }
    }
    
    def __init__(self):
        """初始化灵活共识竞技场"""
        self.arena = ConsensusArena()
        self.arena.update_interval = settings.arena_update_interval
    
    def _parse_group_members(self, members_str: str) -> List[str]:
        """
        解析分组成员配置
        
        Args:
            members_str: 成员配置字符串，如 "claude,gpt4,gemini"
            
        Returns:
            AI名称列表
        """
        if not members_str:
            return []
        
        members = [m.strip().lower() for m in members_str.split(',')]
        # 验证AI名称
        valid_members = [m for m in members if m in self.AI_CONFIGS]
        
        if len(valid_members) != len(members):
            invalid = set(members) - set(valid_members)
            logger.warning(f"忽略无效的AI名称: {invalid}")
        
        return valid_members
    
    def _create_ai_instance(self, ai_name: str):
        """
        创建AI实例
        
        Args:
            ai_name: AI名称（小写）
            
        Returns:
            AI实例或None
        """
        config = self.AI_CONFIGS.get(ai_name)
        if not config:
            return None
        
        # 获取API Key
        api_key = getattr(settings, config['api_key_attr'], '')
        if not api_key:
            logger.warning(f"⚠️  {config['display_name']}: 未配置 API Key")
            return None
        
        try:
            ai_instance = config['class'](
                api_key=api_key,
                model=config['model'],
                initial_balance=100,
                max_position_size=30
            )
            return ai_instance
        except Exception as e:
            logger.error(f"❌ {config['display_name']} 创建失败: {e}")
            return None
    
    def _get_group_private_key(self, group_name: str, member_names: List[str]) -> Optional[str]:
        """
        获取组的私钥
        
        优先级：
        1. GROUP_A_PRIVATE_KEY / GROUP_B_PRIVATE_KEY
        2. 第一个AI的私钥
        3. HYPERLIQUID_PRIVATE_KEY
        
        Args:
            group_name: 组名（"A" 或 "B"）
            member_names: 组成员名称列表
            
        Returns:
            私钥或None
        """
        # 优先使用组私钥
        group_key_attr = f'group_{group_name.lower()}_private_key'
        group_key = getattr(settings, group_key_attr, '')
        if group_key:
            return group_key
        
        # 尝试使用第一个AI的私钥
        for ai_name in member_names:
            config = self.AI_CONFIGS.get(ai_name)
            if config:
                ai_key = getattr(settings, config['private_key_attr'], '')
                if ai_key:
                    logger.info(f"   使用 {config['display_name']} 的私钥作为 Group {group_name}")
                    return ai_key
        
        # 最后使用共享私钥
        shared_key = settings.hyperliquid_private_key
        if shared_key:
            logger.info(f"   使用共享私钥作为 Group {group_name}")
            return shared_key
        
        return None
    
    async def setup_groups(self) -> bool:
        """
        根据配置设置AI组
        
        Returns:
            是否设置成功
        """
        logger.info("🔧 配置 AI 组（灵活分组模式）...")
        logger.info("")
        
        # 解析分组配置
        group_a_members = self._parse_group_members(settings.group_a_members)
        group_b_members = self._parse_group_members(settings.group_b_members)
        
        logger.info(f"📋 分组配置:")
        logger.info(f"   Group A: {', '.join([self.AI_CONFIGS[m]['display_name'] for m in group_a_members])}")
        logger.info(f"   Group B: {', '.join([self.AI_CONFIGS[m]['display_name'] for m in group_b_members])}")
        logger.info("")
        
        # 创建 Group A
        if len(group_a_members) >= 2:
            group_a_ais = []
            for ai_name in group_a_members:
                ai_instance = self._create_ai_instance(ai_name)
                if ai_instance:
                    group_a_ais.append(ai_instance)
            
            if len(group_a_ais) >= 2:
                group_a_key = self._get_group_private_key('A', group_a_members)
                if not group_a_key:
                    logger.error("❌ Group A: 未配置私钥")
                else:
                    client_a = HyperliquidClient(
                        private_key=group_a_key,
                        testnet=settings.hyperliquid_testnet
                    )
                    
                    risk_limits_a = RiskLimits(
                        max_position_size=30.0,
                        max_leverage=settings.max_leverage,
                        daily_loss_limit=settings.daily_loss_limit,
                        max_open_positions=settings.max_open_positions,
                        min_account_balance=10.0
                    )
                    risk_manager_a = RiskManager(client_a, risk_limits_a)
                    
                    group_a = AIGroup(
                        group_name="Group A",
                        ai_models=group_a_ais,
                        client=client_a,
                        risk_manager=risk_manager_a,
                        consensus_threshold=2
                    )
                    
                    async with client_a:
                        balance_info = await client_a.get_balance()
                        group_a.initial_balance = balance_info.get('total_value', 100)
                        group_a.current_balance = group_a.initial_balance
                    
                    self.arena.register_group(group_a)
                    
                    logger.info(f"✅ Group A 配置成功")
                    logger.info(f"   成员: {', '.join([ai.model_name for ai in group_a_ais])}")
                    logger.info(f"   地址: {client_a.address[:10]}...{client_a.address[-8:]}")
                    logger.info(f"   余额: ${group_a.initial_balance:.2f}")
                    logger.info(f"   共识阈值: {len(group_a_ais)} 个 AI 中至少 2 个同意")
                    logger.info("")
            else:
                logger.warning(f"⚠️  Group A: 可用 AI 数量不足 ({len(group_a_ais)})")
        else:
            logger.warning(f"⚠️  Group A: 配置的 AI 数量不足 ({len(group_a_members)}), 需要至少2个")
        
        # 创建 Group B
        if len(group_b_members) >= 2:
            group_b_ais = []
            for ai_name in group_b_members:
                ai_instance = self._create_ai_instance(ai_name)
                if ai_instance:
                    group_b_ais.append(ai_instance)
            
            if len(group_b_ais) >= 2:
                group_b_key = self._get_group_private_key('B', group_b_members)
                if not group_b_key:
                    logger.error("❌ Group B: 未配置私钥")
                else:
                    client_b = HyperliquidClient(
                        private_key=group_b_key,
                        testnet=settings.hyperliquid_testnet
                    )
                    
                    risk_limits_b = RiskLimits(
                        max_position_size=30.0,
                        max_leverage=settings.max_leverage,
                        daily_loss_limit=settings.daily_loss_limit,
                        max_open_positions=settings.max_open_positions,
                        min_account_balance=10.0
                    )
                    risk_manager_b = RiskManager(client_b, risk_limits_b)
                    
                    group_b = AIGroup(
                        group_name="Group B",
                        ai_models=group_b_ais,
                        client=client_b,
                        risk_manager=risk_manager_b,
                        consensus_threshold=2
                    )
                    
                    async with client_b:
                        balance_info = await client_b.get_balance()
                        group_b.initial_balance = balance_info.get('total_value', 100)
                        group_b.current_balance = group_b.initial_balance
                    
                    self.arena.register_group(group_b)
                    
                    logger.info(f"✅ Group B 配置成功")
                    logger.info(f"   成员: {', '.join([ai.model_name for ai in group_b_ais])}")
                    logger.info(f"   地址: {client_b.address[:10]}...{client_b.address[-8:]}")
                    logger.info(f"   余额: ${group_b.initial_balance:.2f}")
                    logger.info(f"   共识阈值: {len(group_b_ais)} 个 AI 中至少 2 个同意")
                    logger.info("")
            else:
                logger.warning(f"⚠️  Group B: 可用 AI 数量不足 ({len(group_b_ais)})")
        else:
            logger.warning(f"⚠️  Group B: 配置的 AI 数量不足 ({len(group_b_members)}), 需要至少2个")
        
        return len(self.arena.groups) > 0
    
    async def start(self):
        """启动竞技场"""
        await self.arena.start()
    
    def stop(self):
        """停止竞技场"""
        self.arena.stop()
    
    def display_leaderboard(self):
        """显示排行榜"""
        self.arena.display_leaderboard()
    
    def get_status(self):
        """获取状态"""
        return self.arena.get_status()

