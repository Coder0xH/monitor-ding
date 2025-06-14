#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仓位管理API路由

本模块包含期货仓位的查询、平仓、杠杆调整等操作的API路由。
支持全仓平仓、部分平仓、杠杆设置等功能。

Author: Dexter
Date: 2025
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from app.core.config import config
from app.core.models import PositionRequest


# 配置日志
logger = logging.getLogger(__name__)

# 创建路由实例
router = APIRouter(
    prefix="/api/positions",
    tags=["positions"]
)


def get_exchange_instance(api_key_id: Optional[str] = None):
    """
    获取交易所实例
    
    Args:
        api_key_id (Optional[str]): API密钥ID
        
    Returns:
        交易所实例或None
    """
    return config.get_binance_futures_exchange(api_key_id)


@router.get("/")
async def get_positions(api_key_id: str = None):
    """
    获取所有开仓的期货仓位
    
    从币安账户检索所有开仓的期货仓位。
    
    Args:
        api_key_id (str, optional): API密钥ID，如果不提供则使用默认密钥
    
    Returns:
        dict: 包含仓位详情的开仓仓位列表
        
    Raises:
        HTTPException: 如果币安API不可用或获取仓位失败
    """
    # 获取交易所实例
    exchange = get_exchange_instance(api_key_id)
    if not exchange:
        raise HTTPException(
            status_code=503,
            detail="币安期货交易不可用，请检查API凭证"
        )
    
    try:
        positions = exchange.fetch_positions()
        # 只筛选非零仓位
        open_positions = [pos for pos in positions if float(pos['contracts']) != 0]
        
        logger.info(f"获取到 {len(open_positions)} 个开仓仓位")
        return {
            "status": "success",
            "message": f"获取到 {len(open_positions)} 个开仓仓位",
            "positions": open_positions
        }
        
    except Exception as e:
        logger.error(f"获取仓位错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取仓位失败: {str(e)}"
        )


@router.get("/{symbol}")
async def get_position_by_symbol(symbol: str, api_key_id: str = None):
    """
    获取指定交易对的仓位信息
    
    检索指定交易对的仓位详情。
    
    Args:
        symbol (str): 交易对符号 (例如: 'BTCUSDT')
        api_key_id (str, optional): API密钥ID，如果不提供则使用默认密钥
        
    Returns:
        dict: 指定交易对的仓位信息
        
    Raises:
        HTTPException: 如果币安API不可用或获取仓位失败
    """
    # 获取交易所实例
    exchange = get_exchange_instance(api_key_id)
    if not exchange:
        raise HTTPException(
            status_code=503,
            detail="币安期货交易不可用，请检查API凭证"
        )
    
    try:
        positions = exchange.fetch_positions([symbol])
        position = None
        
        for pos in positions:
            if pos['symbol'] == symbol and float(pos['contracts']) != 0:
                position = pos
                break
        
        if not position:
            return {
                "status": "success",
                "message": f"{symbol} 无开仓仓位",
                "position": None
            }
        
        logger.info(f"获取到 {symbol} 的仓位信息")
        return {
            "status": "success",
            "message": f"获取到 {symbol} 的仓位信息",
            "position": position
        }
        
    except Exception as e:
        logger.error(f"获取仓位错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取仓位失败: {str(e)}"
        )


@router.post("/close")
async def close_position(position: PositionRequest):
    """
    平仓操作
    
    支持全仓平仓或按百分比部分平仓。
    
    Args:
        position (PositionRequest): 仓位管理详情
        
    Returns:
        dict: 平仓结果
        
    Raises:
        HTTPException: 如果平仓失败
    """
    # 获取交易所实例
    exchange = get_exchange_instance(position.api_key_id)
    if not exchange:
        raise HTTPException(
            status_code=503,
            detail="币安期货交易不可用，请检查API凭证"
        )
    
    try:
        # 获取当前仓位
        positions = exchange.fetch_positions([position.symbol])
        current_position = None
        
        for pos in positions:
            if pos['symbol'] == position.symbol and pos['contracts'] > 0:
                current_position = pos
                break
        
        if not current_position:
            raise HTTPException(
                status_code=404,
                detail=f"未找到 {position.symbol} 的开仓仓位"
            )
        
        # 计算平仓数量
        if position.percentage:
            close_amount = current_position['contracts'] * (position.percentage / 100)
        else:
            close_amount = position.amount or current_position['contracts']
        
        # 确定平仓方向（与当前仓位相反）
        close_side = 'sell' if current_position['side'] == 'long' else 'buy'
        
        # 创建平仓订单
        result = exchange.create_order(
            symbol=position.symbol,
            type='market',
            side=close_side,
            amount=close_amount,
            reduceOnly=True
        )
        
        logger.info(f"仓位平仓成功: {result['id']}")
        return {
            "status": "success",
            "message": "仓位平仓成功",
            "order_id": result['id'],
            "closed_amount": close_amount,
            "close_percentage": (close_amount / current_position['contracts']) * 100 if current_position['contracts'] > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"平仓错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"平仓失败: {str(e)}"
        )


@router.post("/leverage")
async def set_leverage(position: PositionRequest):
    """
    设置交易对杠杆
    
    为指定的交易对设置杠杆倍数。
    
    Args:
        position (PositionRequest): 包含交易对和杠杆的仓位详情
        
    Returns:
        dict: 杠杆设置结果
        
    Raises:
        HTTPException: 如果币安API不可用或杠杆设置失败
    """
    # 获取交易所实例
    exchange = get_exchange_instance(position.api_key_id)
    if not exchange:
        raise HTTPException(
            status_code=503,
            detail="币安期货交易不可用，请检查API凭证"
        )
    
    if not position.leverage:
        raise HTTPException(
            status_code=400,
            detail="设置杠杆需要提供杠杆值"
        )
    
    try:
        # 使用ccxt设置杠杆
        result = exchange.set_leverage(position.leverage, position.symbol)
        
        logger.info(f"{position.symbol} 杠杆设置为 {position.leverage}x")
        return {
            "status": "success",
            "message": f"{position.symbol} 杠杆设置为 {position.leverage}x",
            "symbol": position.symbol,
            "leverage": position.leverage,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"设置杠杆错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"设置杠杆失败: {str(e)}"
        )


@router.post("/close-all")
async def close_all_positions(api_key_id: str = None):
    """
    平掉所有仓位
    
    一键平掉账户中的所有开仓仓位。
    
    Args:
        api_key_id (str, optional): API密钥ID，如果不提供则使用默认密钥
        
    Returns:
        dict: 批量平仓结果
        
    Raises:
        HTTPException: 如果批量平仓失败
    """
    # 获取交易所实例
    exchange = get_exchange_instance(api_key_id)
    if not exchange:
        raise HTTPException(
            status_code=503,
            detail="币安期货交易不可用，请检查API凭证"
        )
    
    try:
        # 获取所有开仓仓位
        positions = exchange.fetch_positions()
        open_positions = [pos for pos in positions if float(pos['contracts']) != 0]
        
        if not open_positions:
            return {
                "status": "success",
                "message": "没有需要平仓的仓位",
                "closed_positions": []
            }
        
        closed_orders = []
        failed_positions = []
        
        # 逐个平仓
        for position in open_positions:
            try:
                # 确定平仓方向
                close_side = 'sell' if position['side'] == 'long' else 'buy'
                
                # 创建平仓订单
                result = exchange.create_order(
                    symbol=position['symbol'],
                    type='market',
                    side=close_side,
                    amount=position['contracts'],
                    reduceOnly=True
                )
                
                closed_orders.append({
                    'symbol': position['symbol'],
                    'order_id': result['id'],
                    'amount': position['contracts'],
                    'side': position['side']
                })
                
                logger.info(f"仓位 {position['symbol']} 平仓成功: {result['id']}")
                
            except Exception as e:
                failed_positions.append({
                    'symbol': position['symbol'],
                    'error': str(e)
                })
                logger.error(f"仓位 {position['symbol']} 平仓失败: {str(e)}")
        
        return {
            "status": "success",
            "message": f"批量平仓完成，成功: {len(closed_orders)}，失败: {len(failed_positions)}",
            "closed_positions": closed_orders,
            "failed_positions": failed_positions,
            "summary": {
                "total_positions": len(open_positions),
                "successful_closes": len(closed_orders),
                "failed_closes": len(failed_positions)
            }
        }
        
    except Exception as e:
        logger.error(f"批量平仓错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"批量平仓失败: {str(e)}"
        )