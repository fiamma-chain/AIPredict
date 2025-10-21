"""
API 路由
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import asyncio
import json
from datetime import datetime

from arena.leaderboard import LeaderboardMetric, LeaderboardPeriod


class TradingAPI:
    """交易 API"""
    
    def __init__(self, trading_engine, performance_tracker, leaderboard):
        """
        初始化 API
        
        Args:
            trading_engine: 交易引擎
            performance_tracker: 性能追踪器
            leaderboard: 排行榜
        """
        self.app = FastAPI(title="AI Trading Arena API", version="1.0.0")
        self.trading_engine = trading_engine
        self.performance_tracker = performance_tracker
        self.leaderboard = leaderboard
        self.websocket_clients: List[WebSocket] = []
        
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
                "version": "1.0.0",
                "status": "running",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/health")
        async def health():
            """健康检查"""
            return {
                "status": "healthy",
                "engine_running": self.trading_engine.is_running,
                "timestamp": datetime.now().isoformat()
            }
        
        # ========== 策略相关接口 ==========
        
        @self.app.get("/strategies")
        async def get_strategies():
            """获取所有策略"""
            strategies = [
                strategy.get_info()
                for strategy in self.trading_engine.strategies.values()
            ]
            return {
                "total": len(strategies),
                "strategies": strategies
            }
        
        @self.app.get("/strategies/{strategy_id}")
        async def get_strategy(strategy_id: str):
            """获取单个策略详情"""
            strategy = self.trading_engine.strategies.get(strategy_id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            metrics = self.performance_tracker.get_metrics(strategy_id)
            trade_history = self.performance_tracker.get_trade_history(strategy_id, limit=50)
            equity_curve = self.performance_tracker.get_equity_curve(strategy_id)
            
            return {
                "info": strategy.get_info(),
                "metrics": metrics.to_dict() if metrics else None,
                "recent_trades": trade_history,
                "equity_curve": equity_curve[-100:]  # 最近 100 个点
            }
        
        @self.app.get("/strategies/{strategy_id}/trades")
        async def get_strategy_trades(strategy_id: str, limit: int = 100):
            """获取策略交易历史"""
            if strategy_id not in self.trading_engine.strategies:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            trades = self.performance_tracker.get_trade_history(strategy_id, limit=limit)
            return {
                "strategy_id": strategy_id,
                "total": len(trades),
                "trades": trades
            }
        
        @self.app.get("/strategies/{strategy_id}/positions")
        async def get_strategy_positions(strategy_id: str):
            """获取策略当前持仓"""
            strategy = self.trading_engine.strategies.get(strategy_id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")
            
            positions = [
                {
                    "coin": coin,
                    **position
                }
                for coin, position in strategy.state.positions.items()
            ]
            
            return {
                "strategy_id": strategy_id,
                "total": len(positions),
                "positions": positions
            }
        
        # ========== 排行榜相关接口 ==========
        
        @self.app.get("/leaderboard")
        async def get_leaderboard(
            metric: str = "total_pnl",
            period: str = "all_time",
            limit: int = 50
        ):
            """获取排行榜"""
            try:
                metric_enum = LeaderboardMetric(metric)
                period_enum = LeaderboardPeriod(period)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid metric or period")
            
            rankings = self.leaderboard.calculate_rankings(
                metric=metric_enum,
                period=period_enum,
                limit=limit
            )
            
            return {
                "metric": metric,
                "period": period,
                "total": len(rankings),
                "rankings": rankings
            }
        
        @self.app.get("/leaderboard/summary")
        async def get_leaderboard_summary():
            """获取排行榜摘要"""
            return self.leaderboard.get_leaderboard_summary()
        
        @self.app.get("/leaderboard/top")
        async def get_top_performers(metric: str = "total_pnl", limit: int = 10):
            """获取表现最好的策略"""
            try:
                metric_enum = LeaderboardMetric(metric)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid metric")
            
            top = self.leaderboard.get_top_performers(metric=metric_enum, limit=limit)
            return {
                "metric": metric,
                "top_performers": top
            }
        
        @self.app.get("/leaderboard/compare")
        async def compare_strategies(strategy_ids: str):
            """对比多个策略"""
            ids = strategy_ids.split(",")
            comparison = self.leaderboard.get_comparison(ids)
            return {
                "strategies": comparison
            }
        
        # ========== 市场数据接口 ==========
        
        @self.app.get("/market/{coin}")
        async def get_market_data(coin: str):
            """获取市场数据"""
            try:
                market_data = await self.trading_engine.client.get_market_data(coin)
                return market_data
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/market/{coin}/orderbook")
        async def get_orderbook(coin: str):
            """获取订单簿"""
            try:
                orderbook = await self.trading_engine.client.get_orderbook(coin)
                return orderbook
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # ========== 风险管理接口 ==========
        
        @self.app.get("/risk/metrics")
        async def get_risk_metrics():
            """获取风险指标"""
            return self.trading_engine.risk_manager.get_risk_metrics()
        
        # ========== 引擎控制接口 ==========
        
        @self.app.get("/engine/status")
        async def get_engine_status():
            """获取引擎状态"""
            return self.trading_engine.get_status()
        
        # ========== WebSocket 接口 ==========
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket 连接 - 实时数据推送"""
            await websocket.accept()
            self.websocket_clients.append(websocket)
            
            try:
                while True:
                    # 接收客户端消息（心跳）
                    try:
                        await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                    except asyncio.TimeoutError:
                        pass
                    
                    # 推送实时数据
                    await self._broadcast_update(websocket)
                    
                    await asyncio.sleep(5)  # 每 5 秒推送一次
            
            except WebSocketDisconnect:
                self.websocket_clients.remove(websocket)
            except Exception as e:
                print(f"WebSocket error: {e}")
                if websocket in self.websocket_clients:
                    self.websocket_clients.remove(websocket)
    
    async def _broadcast_update(self, websocket: WebSocket):
        """广播更新到 WebSocket 客户端"""
        try:
            # 获取最新数据
            summary = self.leaderboard.get_leaderboard_summary()
            top_performers = self.leaderboard.get_top_performers(limit=10)
            risk_metrics = self.trading_engine.risk_manager.get_risk_metrics()
            
            data = {
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "summary": summary,
                "top_performers": top_performers[:5],
                "risk_metrics": risk_metrics
            }
            
            await websocket.send_json(data)
        
        except Exception as e:
            print(f"Broadcast error: {e}")
    
    async def broadcast_to_all(self, data: dict):
        """广播消息给所有连接的客户端"""
        disconnected = []
        
        for client in self.websocket_clients:
            try:
                await client.send_json(data)
            except:
                disconnected.append(client)
        
        # 清理断开的连接
        for client in disconnected:
            self.websocket_clients.remove(client)

