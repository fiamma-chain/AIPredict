"""
共识竞技场 API 路由
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List

router = APIRouter()

# 全局竞技场实例（由主程序设置）
consensus_arena = None


def set_arena(arena):
    """设置竞技场实例"""
    global consensus_arena
    consensus_arena = arena


@router.get("/consensus/status")
async def get_consensus_status() -> Dict:
    """获取共识竞技场状态"""
    if not consensus_arena:
        raise HTTPException(status_code=503, detail="竞技场未启动")
    
    return consensus_arena.get_status()


@router.get("/consensus/groups")
async def get_groups() -> List[Dict]:
    """获取所有 AI 组的详细信息"""
    if not consensus_arena:
        raise HTTPException(status_code=503, detail="竞技场未启动")
    
    groups_data = []
    for group in consensus_arena.groups.values():
        stats = group.get_stats()
        groups_data.append(stats)
    
    return groups_data


@router.get("/consensus/group/{group_name}")
async def get_group_detail(group_name: str) -> Dict:
    """获取特定组的详细信息"""
    if not consensus_arena:
        raise HTTPException(status_code=503, detail="竞技场未启动")
    
    group = consensus_arena.groups.get(group_name)
    if not group:
        raise HTTPException(status_code=404, detail="组不存在")
    
    return group.get_stats()


@router.get("/consensus/group/{group_name}/consensus")
async def get_group_consensus_history(group_name: str, limit: int = 10) -> List[Dict]:
    """获取组的共识历史"""
    if not consensus_arena:
        raise HTTPException(status_code=503, detail="竞技场未启动")
    
    group = consensus_arena.groups.get(group_name)
    if not group:
        raise HTTPException(status_code=404, detail="组不存在")
    
    return group.consensus_history[-limit:]


@router.get("/consensus/leaderboard")
async def get_consensus_leaderboard() -> List[Dict]:
    """获取共识竞技场排行榜"""
    if not consensus_arena:
        raise HTTPException(status_code=503, detail="竞技场未启动")
    
    # 按 ROI 排序
    groups = sorted(
        consensus_arena.groups.values(),
        key=lambda g: g.current_balance - g.initial_balance,
        reverse=True
    )
    
    leaderboard = []
    for i, group in enumerate(groups, 1):
        stats = group.get_stats()
        stats['rank'] = i
        leaderboard.append(stats)
    
    return leaderboard


@router.get("/consensus/latest")
async def get_latest_consensus() -> Dict:
    """获取所有组的最新共识"""
    if not consensus_arena:
        raise HTTPException(status_code=503, detail="竞技场未启动")
    
    latest = {}
    for group_name, group in consensus_arena.groups.items():
        if group.consensus_history:
            latest[group_name] = group.consensus_history[-1]
    
    return latest

