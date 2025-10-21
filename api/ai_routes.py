"""
AI 竞技场 API 路由
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime


class AIArenaAPI:
    """AI 竞技场 API"""
    
    def __init__(self, arena):
        """
        初始化 API
        
        Args:
            arena: AI 竞技场实例
        """
        self.app = FastAPI(title="AI Trading Arena API", version="2.0.0")
        self.arena = arena
        
        # 配置 CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册所有路由"""
        
        @self.app.get("/")
        async def root():
            """API 根路径"""
            return {
                "name": "AI Trading Arena API",
                "version": "2.0.0",
                "description": "AI 模型交易竞技场",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/health")
        async def health():
            """健康检查"""
            return {
                "status": "healthy",
                "arena_running": self.arena.is_running,
                "ai_models": len(self.arena.ai_models),
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/arena/status")
        async def get_arena_status():
            """获取竞技场状态"""
            return self.arena.get_status()
        
        @self.app.get("/ai-models")
        async def get_all_ai_models():
            """获取所有 AI 模型"""
            models = []
            for ai_model in self.arena.ai_models.values():
                stats = ai_model.get_stats()
                models.append(stats)
            
            return {
                "total": len(models),
                "models": sorted(models, key=lambda x: x['total_pnl'], reverse=True)
            }
        
        @self.app.get("/ai-models/{model_name}")
        async def get_ai_model(model_name: str):
            """获取单个 AI 模型详情"""
            ai_model = self.arena.ai_models.get(model_name)
            if not ai_model:
                raise HTTPException(status_code=404, detail="AI 模型未找到")
            
            stats = ai_model.get_stats()
            
            return {
                "stats": stats,
                "positions": ai_model.positions,
                "trade_history": ai_model.trade_history[-20:],  # 最近 20 笔
                "ai_responses": ai_model.ai_responses[-10:]  # 最近 10 次决策
            }
        
        @self.app.get("/leaderboard")
        async def get_leaderboard(metric: str = "total_pnl", limit: int = 10):
            """获取排行榜"""
            models = []
            for ai_model in self.arena.ai_models.values():
                stats = ai_model.get_stats()
                models.append(stats)
            
            # 根据指标排序
            if metric == "roi_percentage":
                models.sort(key=lambda x: x['roi_percentage'], reverse=True)
            elif metric == "win_rate":
                models.sort(key=lambda x: x['win_rate'], reverse=True)
            else:  # total_pnl
                models.sort(key=lambda x: x['total_pnl'], reverse=True)
            
            # 添加排名
            for i, model in enumerate(models, 1):
                model['rank'] = i
            
            return {
                "metric": metric,
                "total": len(models),
                "rankings": models[:limit]
            }
        
        @self.app.get("/leaderboard/summary")
        async def get_leaderboard_summary():
            """获取排行榜摘要"""
            if not self.arena.ai_models:
                return {
                    "total_models": 0,
                    "total_trades": 0,
                    "total_pnl": 0,
                    "best_model": None
                }
            
            total_trades = sum(m.total_trades for m in self.arena.ai_models.values())
            total_pnl = sum(m.current_balance - m.initial_balance for m in self.arena.ai_models.values())
            
            best_model = max(
                self.arena.ai_models.values(),
                key=lambda m: m.current_balance - m.initial_balance
            )
            
            return {
                "total_models": len(self.arena.ai_models),
                "total_trades": total_trades,
                "total_pnl": total_pnl,
                "average_pnl": total_pnl / len(self.arena.ai_models),
                "best_model": {
                    "name": best_model.model_name,
                    "pnl": best_model.current_balance - best_model.initial_balance,
                    "roi": ((best_model.current_balance - best_model.initial_balance) / best_model.initial_balance) * 100
                },
                "trading_pairs": self.arena.trading_pairs,
                "update_interval": self.arena.update_interval
            }
        
        @self.app.get("/performance/comparison")
        async def get_performance_comparison():
            """获取性能对比数据"""
            comparison = []
            
            for ai_model in self.arena.ai_models.values():
                equity_curve = []
                balance = ai_model.initial_balance
                
                # 构建权益曲线
                for trade in ai_model.trade_history:
                    balance += trade['pnl']
                    equity_curve.append({
                        "timestamp": trade['exit_time'],
                        "balance": balance
                    })
                
                comparison.append({
                    "model_name": ai_model.model_name,
                    "equity_curve": equity_curve,
                    "final_balance": ai_model.current_balance
                })
            
            return {
                "models": comparison
            }

