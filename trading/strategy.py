"""
交易策略定义模块
支持策略的创建、导入、导出和应用
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import json


class StrategyType(str, Enum):
    """策略类型"""
    TREND_FOLLOWING = "trend_following"  # 趋势跟踪
    MEAN_REVERSION = "mean_reversion"    # 均值回归
    BREAKOUT = "breakout"                # 突破策略
    SCALPING = "scalping"                # 剥头皮
    SWING = "swing"                      # 波段交易
    GRID = "grid"                        # 网格交易
    ARBITRAGE = "arbitrage"              # 套利
    CUSTOM = "custom"                    # 自定义


class TimeFrame(str, Enum):
    """时间周期"""
    M1 = "1m"      # 1分钟
    M5 = "5m"      # 5分钟
    M15 = "15m"    # 15分钟
    M30 = "30m"    # 30分钟
    H1 = "1h"      # 1小时
    H4 = "4h"      # 4小时
    D1 = "1d"      # 1天
    W1 = "1w"      # 1周


class IndicatorConfig(BaseModel):
    """技术指标配置"""
    name: str = Field(..., description="指标名称，如 RSI, MACD, MA 等")
    enabled: bool = Field(True, description="是否启用")
    params: Dict[str, Any] = Field(default_factory=dict, description="指标参数")
    weight: float = Field(1.0, ge=0, le=1, description="权重 (0-1)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "RSI",
                "enabled": True,
                "params": {"period": 14, "overbought": 70, "oversold": 30},
                "weight": 0.8
            }
        }


class EntryCondition(BaseModel):
    """进场条件"""
    condition_type: str = Field(..., description="条件类型: price, indicator, pattern, volume")
    operator: str = Field(..., description="操作符: >, <, ==, >=, <=, cross_above, cross_below")
    value: Any = Field(..., description="目标值")
    required: bool = Field(True, description="是否为必需条件")
    description: str = Field("", description="条件描述")
    
    class Config:
        json_schema_extra = {
            "example": {
                "condition_type": "indicator",
                "operator": "<",
                "value": 30,
                "required": True,
                "description": "RSI 小于 30 (超卖)"
            }
        }


class ExitCondition(BaseModel):
    """出场条件"""
    condition_type: str = Field(..., description="条件类型")
    operator: str = Field(..., description="操作符")
    value: Any = Field(..., description="目标值")
    priority: int = Field(1, ge=1, le=10, description="优先级 (1-10)")
    description: str = Field("", description="条件描述")


class RiskManagement(BaseModel):
    """风险管理配置"""
    stop_loss_pct: float = Field(5.0, gt=0, le=50, description="止损百分比")
    take_profit_pct: float = Field(10.0, gt=0, le=100, description="止盈百分比")
    trailing_stop: bool = Field(False, description="是否使用移动止损")
    trailing_stop_pct: float = Field(3.0, gt=0, le=50, description="移动止损百分比")
    max_position_size_pct: float = Field(10.0, gt=0, le=100, description="最大仓位百分比")
    max_daily_loss_pct: float = Field(5.0, gt=0, le=50, description="单日最大亏损百分比")
    risk_reward_ratio: float = Field(2.0, gt=0, description="风险回报比")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stop_loss_pct": 5.0,
                "take_profit_pct": 10.0,
                "trailing_stop": True,
                "trailing_stop_pct": 3.0,
                "max_position_size_pct": 10.0,
                "max_daily_loss_pct": 5.0,
                "risk_reward_ratio": 2.0
            }
        }


class PositionSizing(BaseModel):
    """仓位管理配置"""
    method: str = Field("fixed_percentage", description="方法: fixed_percentage, kelly, volatility_based")
    base_size_pct: float = Field(10.0, gt=0, le=100, description="基础仓位百分比")
    use_confidence: bool = Field(True, description="是否根据信心度调整")
    confidence_multiplier: float = Field(1.0, ge=0, le=2, description="信心度乘数")
    max_positions: int = Field(3, ge=1, le=10, description="最大同时持仓数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "method": "fixed_percentage",
                "base_size_pct": 10.0,
                "use_confidence": True,
                "confidence_multiplier": 1.0,
                "max_positions": 3
            }
        }


class MarketCondition(BaseModel):
    """市场条件过滤"""
    min_volume_24h: float = Field(0, ge=0, description="最小24h成交量")
    max_spread_pct: float = Field(1.0, ge=0, le=10, description="最大点差百分比")
    allowed_volatility_range: List[float] = Field([0, 100], description="允许的波动率范围")
    avoid_news_events: bool = Field(False, description="是否避开重大新闻")
    trading_hours: Optional[List[int]] = Field(None, description="交易时间段 (小时)")


class TradingStrategy(BaseModel):
    """交易策略完整定义"""
    
    # 基本信息
    strategy_id: str = Field(..., description="策略唯一标识")
    name: str = Field(..., min_length=1, max_length=100, description="策略名称")
    version: str = Field("1.0.0", description="策略版本")
    description: str = Field("", max_length=500, description="策略描述")
    author: str = Field("", description="策略作者")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    # 策略分类
    strategy_type: StrategyType = Field(..., description="策略类型")
    timeframe: TimeFrame = Field(TimeFrame.M15, description="主要时间周期")
    
    # 适用市场
    applicable_coins: List[str] = Field(default_factory=lambda: ["BTC"], description="适用币种")
    applicable_platforms: List[str] = Field(default_factory=lambda: ["hyperliquid", "aster"], description="适用平台")
    
    # 策略参数
    min_confidence: float = Field(50.0, ge=0, le=100, description="最小信心度阈值")
    risk_management: RiskManagement = Field(default_factory=RiskManagement, description="风险管理")
    position_sizing: PositionSizing = Field(default_factory=PositionSizing, description="仓位管理")
    
    # 技术指标
    indicators: List[IndicatorConfig] = Field(default_factory=list, description="技术指标列表")
    
    # 进场和出场条件
    entry_conditions: Dict[str, List[EntryCondition]] = Field(
        default_factory=lambda: {"long": [], "short": []},
        description="进场条件 (long/short)"
    )
    exit_conditions: Dict[str, List[ExitCondition]] = Field(
        default_factory=lambda: {"long": [], "short": []},
        description="出场条件 (long/short)"
    )
    
    # 市场条件过滤
    market_conditions: MarketCondition = Field(default_factory=MarketCondition, description="市场条件过滤")
    
    # 策略提示词模板（用于AI）
    prompt_template: Optional[str] = Field(None, description="自定义AI提示词模板")
    
    # 回测结果（可选）
    backtest_results: Optional[Dict[str, Any]] = Field(None, description="回测结果")
    
    # 性能统计（可选）
    performance_stats: Optional[Dict[str, Any]] = Field(None, description="实盘性能统计")
    
    # 标签和元数据
    tags: List[str] = Field(default_factory=list, description="策略标签")
    is_active: bool = Field(True, description="是否激活")
    is_public: bool = Field(False, description="是否公开")
    
    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        return datetime.now()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_json(self, indent: int = 2) -> str:
        """导出为 JSON 字符串"""
        return self.model_dump_json(indent=indent)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return self.model_dump()
    
    @classmethod
    def from_json(cls, json_str: str) -> "TradingStrategy":
        """从 JSON 字符串加载"""
        return cls.model_validate_json(json_str)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "TradingStrategy":
        """从字典加载"""
        return cls.model_validate(data)
    
    def save_to_file(self, filepath: str):
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
    
    @classmethod
    def load_from_file(cls, filepath: str) -> "TradingStrategy":
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())
    
    def validate_for_coin(self, coin: str) -> bool:
        """验证策略是否适用于指定币种"""
        if not self.applicable_coins:
            return True  # 如果没有限制，则适用所有币种
        return coin.upper() in [c.upper() for c in self.applicable_coins]
    
    def validate_for_platform(self, platform: str) -> bool:
        """验证策略是否适用于指定平台"""
        if not self.applicable_platforms:
            return True
        return platform.lower() in [p.lower() for p in self.applicable_platforms]
    
    def get_prompt_for_ai(self, market_data: Dict, coin: str) -> str:
        """
        生成用于AI的提示词
        
        Args:
            market_data: 市场数据
            coin: 币种
            
        Returns:
            提示词文本
        """
        if self.prompt_template:
            # 使用自定义模板
            return self.prompt_template.format(
                coin=coin,
                strategy_name=self.name,
                strategy_type=self.strategy_type.value,
                **market_data
            )
        
        # 使用默认模板（基于策略配置生成）
        prompt = f"""交易策略: {self.name}
策略类型: {self.strategy_type.value}
币种: {coin}

风险管理:
- 止损: {self.risk_management.stop_loss_pct}%
- 止盈: {self.risk_management.take_profit_pct}%
- 风险回报比: {self.risk_management.risk_reward_ratio}

"""
        
        # 添加技术指标
        if self.indicators:
            prompt += "技术指标:\n"
            for ind in self.indicators:
                if ind.enabled:
                    prompt += f"- {ind.name}: {ind.params}\n"
        
        # 添加进场条件
        if self.entry_conditions.get("long"):
            prompt += "\n做多进场条件:\n"
            for cond in self.entry_conditions["long"]:
                if cond.required:
                    prompt += f"- [必需] {cond.description}\n"
                else:
                    prompt += f"- [可选] {cond.description}\n"
        
        if self.entry_conditions.get("short"):
            prompt += "\n做空进场条件:\n"
            for cond in self.entry_conditions["short"]:
                if cond.required:
                    prompt += f"- [必需] {cond.description}\n"
                else:
                    prompt += f"- [可选] {cond.description}\n"
        
        prompt += f"\n最小信心度阈值: {self.min_confidence}%\n"
        prompt += "\n请根据以上策略规则分析当前市场并给出交易建议。\n"
        
        return prompt
    
    def clone(self) -> "TradingStrategy":
        """克隆策略（创建副本）"""
        import uuid
        data = self.to_dict()
        data['strategy_id'] = str(uuid.uuid4())
        data['name'] = f"{self.name} (副本)"
        data['created_at'] = datetime.now()
        data['updated_at'] = datetime.now()
        return TradingStrategy.from_dict(data)
    
    def merge_with_ai_style(self, ai_analysis: Dict) -> Dict:
        """
        将策略参数与AI分析结果合并
        
        Args:
            ai_analysis: AI分析结果 {decision, confidence, reasoning}
            
        Returns:
            合并后的决策
        """
        # 应用策略的信心度过滤
        if ai_analysis.get('confidence', 0) < self.min_confidence:
            return {
                'decision': 'hold',
                'confidence': ai_analysis.get('confidence', 0),
                'reasoning': f"信心度 {ai_analysis.get('confidence', 0)}% 低于策略阈值 {self.min_confidence}%",
                'strategy_applied': self.name
            }
        
        # 应用风险管理规则
        result = {
            **ai_analysis,
            'strategy_applied': self.name,
            'stop_loss_pct': self.risk_management.stop_loss_pct,
            'take_profit_pct': self.risk_management.take_profit_pct,
            'position_size_pct': self.position_sizing.base_size_pct,
            'risk_reward_ratio': self.risk_management.risk_reward_ratio
        }
        
        # 根据信心度调整仓位
        if self.position_sizing.use_confidence:
            confidence_factor = ai_analysis.get('confidence', 50) / 100.0
            result['position_size_pct'] *= confidence_factor * self.position_sizing.confidence_multiplier
        
        return result


# 预定义策略模板

def create_aggressive_swing_strategy() -> TradingStrategy:
    """创建激进波段策略（默认策略）"""
    return TradingStrategy(
        strategy_id="aggressive_swing_v1",
        name="激进波段策略",
        version="1.0.0",
        description="追求更大收益空间的波段交易策略，止损5%/止盈10%，风险回报比1:2",
        author="System",
        strategy_type=StrategyType.SWING,
        timeframe=TimeFrame.M15,
        min_confidence=50.0,
        risk_management=RiskManagement(
            stop_loss_pct=5.0,
            take_profit_pct=10.0,
            trailing_stop=True,
            trailing_stop_pct=3.0,
            max_position_size_pct=15.0,
            risk_reward_ratio=2.0
        ),
        position_sizing=PositionSizing(
            method="fixed_percentage",
            base_size_pct=10.0,
            use_confidence=True,
            confidence_multiplier=1.0,
            max_positions=3
        ),
        indicators=[
            IndicatorConfig(name="RSI", params={"period": 14}, weight=0.8),
            IndicatorConfig(name="MA", params={"period": 20, "type": "SMA"}, weight=0.6),
            IndicatorConfig(name="Volume", params={"threshold": 1.5}, weight=0.5)
        ],
        tags=["swing", "aggressive", "high_reward"]
    )


def create_conservative_strategy() -> TradingStrategy:
    """创建保守策略"""
    return TradingStrategy(
        strategy_id="conservative_v1",
        name="保守稳健策略",
        version="1.0.0",
        description="风险较低的稳健策略，止损3%/止盈6%，要求更高的信心度",
        author="System",
        strategy_type=StrategyType.TREND_FOLLOWING,
        timeframe=TimeFrame.H1,
        min_confidence=70.0,
        risk_management=RiskManagement(
            stop_loss_pct=3.0,
            take_profit_pct=6.0,
            trailing_stop=True,
            trailing_stop_pct=2.0,
            max_position_size_pct=8.0,
            risk_reward_ratio=2.0
        ),
        position_sizing=PositionSizing(
            method="fixed_percentage",
            base_size_pct=5.0,
            use_confidence=True,
            confidence_multiplier=0.8,
            max_positions=2
        ),
        indicators=[
            IndicatorConfig(name="RSI", params={"period": 14}, weight=0.9),
            IndicatorConfig(name="MA", params={"period": 50, "type": "SMA"}, weight=0.8),
            IndicatorConfig(name="MACD", params={"fast": 12, "slow": 26, "signal": 9}, weight=0.7)
        ],
        tags=["conservative", "low_risk", "trend_following"]
    )


def create_scalping_strategy() -> TradingStrategy:
    """创建剥头皮策略"""
    return TradingStrategy(
        strategy_id="scalping_v1",
        name="高频剥头皮策略",
        version="1.0.0",
        description="快进快出，小止损小止盈，追求高胜率",
        author="System",
        strategy_type=StrategyType.SCALPING,
        timeframe=TimeFrame.M5,
        min_confidence=60.0,
        risk_management=RiskManagement(
            stop_loss_pct=1.0,
            take_profit_pct=2.0,
            trailing_stop=False,
            max_position_size_pct=20.0,
            risk_reward_ratio=2.0
        ),
        position_sizing=PositionSizing(
            method="fixed_percentage",
            base_size_pct=15.0,
            use_confidence=True,
            confidence_multiplier=1.2,
            max_positions=5
        ),
        indicators=[
            IndicatorConfig(name="EMA", params={"period": 9}, weight=0.9),
            IndicatorConfig(name="Bollinger", params={"period": 20, "std": 2}, weight=0.7),
            IndicatorConfig(name="Volume", params={"threshold": 2.0}, weight=0.6)
        ],
        market_conditions=MarketCondition(
            min_volume_24h=1000000,
            max_spread_pct=0.2,
            allowed_volatility_range=[0.5, 3.0]
        ),
        tags=["scalping", "high_frequency", "short_term"]
    )


# 策略管理器

class StrategyManager:
    """策略管理器"""
    
    def __init__(self):
        self.strategies: Dict[str, TradingStrategy] = {}
        self._load_default_strategies()
    
    def _load_default_strategies(self):
        """加载默认策略"""
        default_strategies = [
            create_aggressive_swing_strategy(),
            create_conservative_strategy(),
            create_scalping_strategy()
        ]
        for strategy in default_strategies:
            self.strategies[strategy.strategy_id] = strategy
    
    def add_strategy(self, strategy: TradingStrategy):
        """添加策略"""
        self.strategies[strategy.strategy_id] = strategy
    
    def get_strategy(self, strategy_id: str) -> Optional[TradingStrategy]:
        """获取策略"""
        return self.strategies.get(strategy_id)
    
    def list_strategies(self, strategy_type: Optional[StrategyType] = None) -> List[TradingStrategy]:
        """列出所有策略"""
        strategies = list(self.strategies.values())
        if strategy_type:
            strategies = [s for s in strategies if s.strategy_type == strategy_type]
        return strategies
    
    def remove_strategy(self, strategy_id: str):
        """删除策略"""
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
    
    def export_strategy(self, strategy_id: str, filepath: str):
        """导出策略到文件"""
        strategy = self.get_strategy(strategy_id)
        if strategy:
            strategy.save_to_file(filepath)
    
    def import_strategy(self, filepath: str) -> TradingStrategy:
        """从文件导入策略"""
        strategy = TradingStrategy.load_from_file(filepath)
        self.add_strategy(strategy)
        return strategy
    
    def get_strategy_for_coin_and_platform(
        self,
        coin: str,
        platform: str,
        strategy_type: Optional[StrategyType] = None
    ) -> List[TradingStrategy]:
        """获取适用于指定币种和平台的策略"""
        strategies = []
        for strategy in self.strategies.values():
            if not strategy.is_active:
                continue
            if not strategy.validate_for_coin(coin):
                continue
            if not strategy.validate_for_platform(platform):
                continue
            if strategy_type and strategy.strategy_type != strategy_type:
                continue
            strategies.append(strategy)
        return strategies


# 全局策略管理器实例
_strategy_manager: Optional[StrategyManager] = None


def get_strategy_manager() -> StrategyManager:
    """获取全局策略管理器"""
    global _strategy_manager
    if _strategy_manager is None:
        _strategy_manager = StrategyManager()
    return _strategy_manager

