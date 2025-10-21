"""
竞技场模式配置
"""
from enum import Enum
from pydantic import BaseModel
from typing import Optional


class ArenaMode(str, Enum):
    """竞技场模式"""
    CONSENSUS = "consensus"  # 共识模式
    INDEPENDENT = "independent"  # 独立模式


class ArenaConfig(BaseModel):
    """竞技场配置"""
    mode: ArenaMode = ArenaMode.CONSENSUS
    update_interval: int = 600
    
    # 共识模式配置
    consensus_threshold: int = 2  # 至少2个AI同意
    
    # 独立模式配置
    enable_all_ais: bool = True  # 是否启用所有AI


# 全局配置实例
arena_config = ArenaConfig()


def get_arena_mode() -> ArenaMode:
    """获取当前竞技场模式"""
    return arena_config.mode


def set_arena_mode(mode: ArenaMode):
    """设置竞技场模式"""
    arena_config.mode = mode


def get_config() -> ArenaConfig:
    """获取完整配置"""
    return arena_config

