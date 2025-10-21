"""
多地址竞技场（独立模式）
从 ai_arena_multiaddr.py 重构，便于统一管理
"""
import asyncio
import logging
from typing import Dict, Optional, List, Tuple
from config.settings import settings
from trading.hyperliquid.client import HyperliquidClient
from trading.risk_manager import RiskManager, RiskLimits
from arena.ai_arena import AIArena

logger = logging.getLogger(__name__)


class MultiAddressArena:
    """多地址竞技场 - 每个AI使用独立地址"""
    
    def __init__(self):
        self.ai_models: List[Tuple] = []  # (ai_name, ai_model, client, arena)
        self.clients: Dict[str, HyperliquidClient] = {}
        self.arenas: Dict[str, AIArena] = {}
        self.is_running = False
        
    async def setup_ai_with_address(
        self,
        ai_name: str,
        ai_class,
        api_key: str,
        private_key: str,
        model: str,
        **kwargs
    ) -> Optional[Tuple]:
        """为AI设置独立地址和客户端"""
        if not api_key:
            logger.warning(f"⚠️  {ai_name}: 未配置 API Key，跳过")
            return None
            
        if not private_key:
            logger.warning(f"⚠️  {ai_name}: 未配置独立私钥，跳过")
            return None
        
        try:
            client = HyperliquidClient(
                private_key=private_key,
                testnet=settings.hyperliquid_testnet
            )
            
            address = client.address
            async with client:
                balance_info = await client.get_balance()
                balance = balance_info.get('total_value', 0)
            
            logger.info(f"✅ {ai_name}")
            logger.info(f"   地址: {address[:10]}...{address[-8:]}")
            logger.info(f"   余额: ${balance:.2f}")
            
            risk_limits = RiskLimits(
                max_position_size=settings.ai_max_position_size,
                max_leverage=settings.max_leverage,
                daily_loss_limit=settings.daily_loss_limit,
                max_open_positions=settings.max_open_positions,
                min_account_balance=settings.min_account_balance
            )
            risk_manager = RiskManager(client, risk_limits)
            
            arena = AIArena(client, risk_manager)
            arena.update_interval = settings.arena_update_interval
            
            ai_model = ai_class(
                api_key=api_key,
                model=model,
                initial_balance=balance,
                max_position_size=settings.ai_max_position_size,
                **kwargs
            )
            
            arena.register_ai_model(ai_model)
            
            self.clients[ai_name] = client
            self.arenas[ai_name] = arena
            self.ai_models.append((ai_name, ai_model, client, arena))
            
            return (ai_model, client, arena)
            
        except Exception as e:
            logger.error(f"❌ {ai_name} 设置失败: {e}")
            return None
    
    async def start(self):
        """启动所有AI竞技场"""
        if not self.ai_models:
            logger.error("❌ 没有可用的 AI 模型！")
            return
        
        self.is_running = True
        
        tasks = []
        for ai_name, ai_model, client, arena in self.ai_models:
            task = asyncio.create_task(self._run_arena(ai_name, arena))
            tasks.append(task)
        
        leaderboard_task = asyncio.create_task(self._update_leaderboard())
        tasks.append(leaderboard_task)
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("\n收到中断信号...")
        finally:
            await self.stop_all()
    
    async def _run_arena(self, ai_name: str, arena: AIArena):
        """运行单个AI的竞技场"""
        try:
            await arena.start()
        except Exception as e:
            logger.error(f"❌ {ai_name} 竞技场异常: {e}")
    
    async def _update_leaderboard(self):
        """定期更新总排行榜"""
        while self.is_running:
            try:
                await asyncio.sleep(settings.arena_update_interval)
                self.display_leaderboard()
            except Exception as e:
                logger.error(f"更新排行榜失败: {e}")
    
    def display_leaderboard(self):
        """显示排行榜"""
        logger.info("")
        logger.info("=" * 96)
        logger.info("🏆 多地址竞技场总排行榜")
        logger.info("=" * 96)
        
        rankings = []
        for ai_name, ai_model, client, arena in self.ai_models:
            try:
                pnl = ai_model.current_balance - ai_model.initial_balance
                roi = (pnl / ai_model.initial_balance * 100) if ai_model.initial_balance > 0 else 0
                
                rankings.append({
                    'name': ai_name,
                    'balance': ai_model.current_balance,
                    'initial': ai_model.initial_balance,
                    'pnl': pnl,
                    'roi': roi,
                    'trades': len(ai_model.trade_history),
                    'address': client.address
                })
            except:
                continue
        
        rankings.sort(key=lambda x: x['roi'], reverse=True)
        
        print(f"{'排名':<6}{'AI模型':<20}{'地址':<20}{'余额':<15}{'盈亏':<15}{'ROI':<12}{'交易数':<8}")
        print("-" * 96)
        
        for i, rank in enumerate(rankings, 1):
            addr_short = f"{rank['address'][:6]}...{rank['address'][-4:]}"
            print(
                f"{i:<6}"
                f"{rank['name']:<20}"
                f"{addr_short:<20}"
                f"${rank['balance']:<14.2f}"
                f"${rank['pnl']:<14.2f}"
                f"{rank['roi']:<11.2f}%"
                f"{rank['trades']:<8}"
            )
        
        print("=" * 96)
        logger.info("")
    
    async def stop_all(self):
        """停止所有竞技场"""
        self.is_running = False
        logger.info("正在停止所有竞技场...")
        for ai_name, ai_model, client, arena in self.ai_models:
            try:
                arena.stop()
            except:
                pass
        logger.info("所有竞技场已停止")
    
    def stop(self):
        """停止竞技场"""
        self.is_running = False
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'mode': 'independent',
            'total_ais': len(self.ai_models),
            'ai_models': [
                {
                    'name': ai_name,
                    'stats': ai_model.get_stats(),
                    'address': client.address
                }
                for ai_name, ai_model, client, arena in self.ai_models
            ]
        }

