"""
统一 API 路由 - 支持两种模式
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List
from config.arena_config import ArenaMode, get_arena_mode

router = APIRouter()

# 全局竞技场实例
current_arena = None
current_mode = ArenaMode.CONSENSUS


def set_arena(arena, mode: ArenaMode):
    """设置竞技场实例"""
    global current_arena, current_mode
    current_arena = arena
    current_mode = mode


@router.get("/status")
async def get_status() -> Dict:
    """获取竞技场状态"""
    if not current_arena:
        raise HTTPException(status_code=503, detail="竞技场未启动")
    
    return {
        'mode': current_mode.value,
        'data': current_arena.get_status()
    }


@router.get("/mode")
async def get_mode() -> Dict:
    """获取当前模式"""
    return {
        'mode': current_mode.value,
        'available_modes': ['consensus', 'independent']
    }


@router.get("/leaderboard")
async def get_leaderboard() -> Dict:
    """获取排行榜（兼容两种模式）"""
    if not current_arena:
        raise HTTPException(status_code=503, detail="竞技场未启动")
    
    if current_mode == ArenaMode.CONSENSUS:
        # 共识模式：返回组排行榜
        groups = sorted(
            current_arena.groups.values(),
            key=lambda g: g.current_balance - g.initial_balance,
            reverse=True
        )
        
        leaderboard = []
        for i, group in enumerate(groups, 1):
            stats = group.get_stats()
            stats['rank'] = i
            leaderboard.append(stats)
        
        return {
            'mode': 'consensus',
            'leaderboard': leaderboard
        }
    else:
        # 独立模式：返回AI排行榜
        ai_list = []
        for ai_name, ai_model, client, arena in current_arena.ai_models:
            stats = ai_model.get_stats()
            stats['address'] = client.address
            ai_list.append(stats)
        
        ai_list.sort(key=lambda x: x['roi_percentage'], reverse=True)
        
        for i, ai in enumerate(ai_list, 1):
            ai['rank'] = i
        
        return {
            'mode': 'independent',
            'leaderboard': ai_list
        }


@router.get("/details")
async def get_details() -> Dict:
    """获取详细信息（根据模式返回不同数据）"""
    if not current_arena:
        raise HTTPException(status_code=503, detail="竞技场未启动")
    
    if current_mode == ArenaMode.CONSENSUS:
        # 共识模式：返回所有组的详细信息
        groups_data = []
        for group in current_arena.groups.values():
            stats = group.get_stats()
            groups_data.append(stats)
        
        return {
            'mode': 'consensus',
            'groups': groups_data
        }
    else:
        # 独立模式：返回所有AI的详细信息
        ai_data = []
        for ai_name, ai_model, client, arena in current_arena.ai_models:
            stats = ai_model.get_stats()
            stats['address'] = client.address
            ai_data.append(stats)
        
        return {
            'mode': 'independent',
            'ai_models': ai_data
        }


@router.get("/consensus/latest")
async def get_latest_consensus() -> Dict:
    """获取最新共识（仅共识模式）"""
    if current_mode != ArenaMode.CONSENSUS:
        raise HTTPException(status_code=400, detail="当前不是共识模式")
    
    if not current_arena:
        raise HTTPException(status_code=503, detail="竞技场未启动")
    
    latest = {}
    for group_name, group in current_arena.groups.items():
        if group.consensus_history:
            latest[group_name] = group.consensus_history[-1]
    
    return latest

