#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货交易API路由

本模块包含币安期货交易操作的API路由，
包括订单管理、仓位管理和账户信息。
支持多API密钥管理、动态参数配置、分批交易等功能。

Author: Dexter
Date: 2025
"""

import logging
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.core.config import config
from app.core.models import (
    FuturesOrderRequest, PositionRequest, APIKeyConfig, BulkActionRequest
)


# 配置日志
logger = logging.getLogger(__name__)

# 创建路由实例
router = APIRouter(
    prefix="/api/futures",
    tags=["futures"]
)

# 活跃的分批订单跟踪
active_batch_orders: Dict[str, dict] = {}


def get_exchange_instance(api_key_id: Optional[str] = None):
    """
    获取交易所实例
    
    Args:
        api_key_id (Optional[str]): API密钥ID
        
    Returns:
        交易所实例或None
    """
    return config.get_binance_futures_exchange(api_key_id)


async def calculate_position_amount(exchange, symbol: str, position_type: str, amount: Optional[float], percentage: Optional[float]) -> float:
    """
    计算仓位数量
    
    Args:
        exchange: 交易所实例
        symbol (str): 交易对符号
        position_type (str): 仓位类型 ('full', 'percentage', 'fixed')
        amount (Optional[float]): 固定数量
        percentage (Optional[float]): 百分比
        
    Returns:
        float: 计算后的数量
    """
    if position_type == 'fixed' and amount:
        return amount
    elif position_type == 'percentage' and percentage:
        # 获取账户余额
        balance = exchange.fetch_balance()
        available_balance = balance['USDT']['free'] if 'USDT' in balance else 0
        return (available_balance * percentage) / 100
    elif position_type == 'full':
        # 获取全部可用余额
        balance = exchange.fetch_balance()
        return balance['USDT']['free'] if 'USDT' in balance else 0
    else:
        raise ValueError("无效的仓位类型或参数")


async def set_leverage_internal(exchange, symbol: str, leverage: int):
    """
    内部函数：设置交易对杠杆
    
    Args:
        exchange: 交易所实例
        symbol (str): 交易对符号
        leverage (int): 杠杆倍数
        
    Raises:
        Exception: 如果设置杠杆失败
    """
    try:
        result = exchange.set_leverage(leverage, symbol)
        logger.info(f"杠杆设置为 {leverage}x，交易对: {symbol}")
        return result
    except Exception as e:
        logger.error(f"设置杠杆错误: {str(e)}")
        raise e


async def create_stop_orders(exchange, symbol: str, side: str, position_size: float, 
                           take_profit_percentage: Optional[float], 
                           stop_loss_percentage: Optional[float],
                           is_partial_tp: bool = False,
                           is_partial_sl: bool = False,
                           partial_percentage: Optional[float] = None):
    """
    创建止盈止损订单
    
    Args:
        exchange: 交易所实例
        symbol (str): 交易对符号
        side (str): 订单方向
        position_size (float): 仓位大小
        take_profit_percentage (Optional[float]): 止盈百分比
        stop_loss_percentage (Optional[float]): 止损百分比
        is_partial_tp (bool): 是否部分止盈
        is_partial_sl (bool): 是否部分止损
        partial_percentage (Optional[float]): 部分平仓百分比
    """
    results = []
    
    # 获取当前价格
    ticker = exchange.fetch_ticker(symbol)
    current_price = ticker['last']
    
    # 计算止盈止损数量
    tp_amount = position_size
    sl_amount = position_size
    
    if is_partial_tp and partial_percentage:
        tp_amount = position_size * (partial_percentage / 100)
    if is_partial_sl and partial_percentage:
        sl_amount = position_size * (partial_percentage / 100)
    
    # 创建止盈订单
    if take_profit_percentage:
        if side == 'buy':
            tp_price = current_price * (1 + take_profit_percentage / 100)
            tp_side = 'sell'
        else:
            tp_price = current_price * (1 - take_profit_percentage / 100)
            tp_side = 'buy'
        
        tp_order = exchange.create_order(
            symbol=symbol,
            type='take_profit',
            side=tp_side,
            amount=tp_amount,
            stopPrice=tp_price,
            reduceOnly=True
        )
        results.append(('take_profit', tp_order))
        logger.info(f"止盈订单已创建: {tp_order['id']}")
    
    # 创建止损订单
    if stop_loss_percentage:
        if side == 'buy':
            sl_price = current_price * (1 - stop_loss_percentage / 100)
            sl_side = 'sell'
        else:
            sl_price = current_price * (1 + stop_loss_percentage / 100)
            sl_side = 'buy'
        
        sl_order = exchange.create_order(
            symbol=symbol,
            type='stop',
            side=sl_side,
            amount=sl_amount,
            stopPrice=sl_price,
            reduceOnly=True
        )
        results.append(('stop_loss', sl_order))
        logger.info(f"止损订单已创建: {sl_order['id']}")
    
    return results


async def execute_batch_orders(exchange, symbol: str, side: str, total_amount: float,
                             batch_count: int, duration_minutes: int,
                             min_amount: float, max_amount: float,
                             leverage: Optional[int] = None):
    """
    执行分批订单
    
    Args:
        exchange: 交易所实例
        symbol (str): 交易对符号
        side (str): 订单方向
        total_amount (float): 总数量
        batch_count (int): 分批数量
        duration_minutes (int): 持续时间(分钟)
        min_amount (float): 最小数量
        max_amount (float): 最大数量
        leverage (Optional[int]): 杠杆倍数
    """
    batch_id = f"{symbol}_{side}_{datetime.now().timestamp()}"
    active_batch_orders[batch_id] = {
        'symbol': symbol,
        'side': side,
        'total_amount': total_amount,
        'executed_amount': 0,
        'orders': [],
        'status': 'active'
    }
    
    # 设置杠杆
    if leverage:
        await set_leverage_internal(exchange, symbol, leverage)
    
    # 计算每批间隔时间
    interval_seconds = (duration_minutes * 60) / batch_count
    
    for i in range(batch_count):
        # 随机生成本批次数量
        remaining_amount = total_amount - active_batch_orders[batch_id]['executed_amount']
        remaining_batches = batch_count - i
        
        if remaining_batches == 1:
            # 最后一批，使用剩余全部数量
            batch_amount = remaining_amount
        else:
            # 确保剩余数量能够分配给后续批次
            max_this_batch = min(max_amount, remaining_amount - (remaining_batches - 1) * min_amount)
            min_this_batch = max(min_amount, remaining_amount - (remaining_batches - 1) * max_amount)
            batch_amount = random.uniform(min_this_batch, max_this_batch)
        
        try:
            # 创建市价订单
            order = exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=batch_amount
            )
            
            active_batch_orders[batch_id]['orders'].append(order)
            active_batch_orders[batch_id]['executed_amount'] += batch_amount
            
            logger.info(f"分批订单 {i+1}/{batch_count} 已执行: {order['id']}, 数量: {batch_amount}")
            
        except Exception as e:
            logger.error(f"分批订单执行失败: {str(e)}")
            active_batch_orders[batch_id]['status'] = 'error'
            break
        
        # 等待下一批次（除了最后一批）
        if i < batch_count - 1:
            await asyncio.sleep(interval_seconds)
    
    active_batch_orders[batch_id]['status'] = 'completed'
    return batch_id


@router.post("/order")
async def create_futures_order(order: FuturesOrderRequest, background_tasks: BackgroundTasks):
    """
    创建期货订单
    
    支持市价单、限价单、分批订单等多种类型，
    可动态设置杠杆、止盈止损等参数。
    
    Args:
        order (FuturesOrderRequest): 订单详情，包括交易对、方向、类型、数量等
        background_tasks (BackgroundTasks): 后台任务处理器
        
    Returns:
        dict: 订单创建结果，包含订单ID和详情
        
    Raises:
        HTTPException: 如果币安API不可用或订单创建失败
    """
    # 获取交易所实例
    exchange = get_exchange_instance(order.api_key_id)
    if not exchange:
        raise HTTPException(
            status_code=503,
            detail="币安期货交易不可用，请检查API凭证"
        )
    
    try:
        # 设置杠杆
        if order.leverage is not None:
            await set_leverage_internal(exchange, order.symbol, order.leverage)
        
        results = []
        
        # 处理分批订单
        if order.is_batch_order:
            if not all([order.batch_count, order.batch_duration_minutes, 
                       order.min_amount_per_batch, order.max_amount_per_batch]):
                raise HTTPException(
                    status_code=400,
                    detail="分批订单需要提供所有分批参数"
                )
            
            # 在后台执行分批订单
            background_tasks.add_task(
                execute_batch_orders,
                exchange, order.symbol, order.side, order.amount,
                order.batch_count, order.batch_duration_minutes,
                order.min_amount_per_batch, order.max_amount_per_batch,
                order.leverage
            )
            
            return {
                "status": "success",
                "message": "分批订单已启动",
                "order_type": "batch",
                "batch_info": {
                    "total_amount": order.amount,
                    "batch_count": order.batch_count,
                    "duration_minutes": order.batch_duration_minutes
                }
            }
        
        # 处理市价单
        elif order.is_market_order:
            # 计算实际交易数量
            if order.position_type:
                actual_amount = await calculate_position_amount(
                    exchange, order.symbol, order.position_type, 
                    order.amount, order.percentage
                )
            else:
                actual_amount = order.amount
            
            # 创建市价订单
            main_order = exchange.create_order(
                symbol=order.symbol,
                type='market',
                side=order.side,
                amount=actual_amount
            )
            results.append(('main_order', main_order))
            
            # 创建止盈止损订单
            if order.take_profit_percentage or order.stop_loss_percentage:
                stop_orders = await create_stop_orders(
                    exchange, order.symbol, order.side, actual_amount,
                    order.take_profit_percentage, order.stop_loss_percentage,
                    order.is_partial_tp, order.is_partial_sl, order.partial_percentage
                )
                results.extend(stop_orders)
        
        # 处理普通订单
        else:
            order_params = {
                'symbol': order.symbol,
                'side': order.side,
                'type': order.type,
                'amount': order.amount,
            }
            
            # 添加限价单价格
            if order.type == 'limit' and order.price:
                order_params['price'] = order.price
            
            # 添加止损单触发价格
            if order.type in ['stop', 'take_profit'] and order.stop_price:
                order_params['stopPrice'] = order.stop_price
            
            # 添加只减仓标志
            if order.reduce_only:
                order_params['reduceOnly'] = True
            
            # 创建订单
            main_order = exchange.create_order(**order_params)
            results.append(('main_order', main_order))
        
        logger.info(f"期货订单创建成功: {[r[1]['id'] for r in results]}")
        return {
            "status": "success",
            "message": "期货订单创建成功",
            "orders": results
        }
        
    except Exception as e:
        logger.error(f"创建期货订单错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"创建期货订单失败: {str(e)}"
        )


@router.get("/batch-orders/{batch_id}")
async def get_batch_order_status(batch_id: str):
    """
    获取分批订单状态
    
    查询指定分批订单的执行状态和详情。
    
    Args:
        batch_id (str): 分批订单ID
        
    Returns:
        dict: 分批订单状态信息
        
    Raises:
        HTTPException: 如果分批订单不存在
    """
    if batch_id not in active_batch_orders:
        raise HTTPException(
            status_code=404,
            detail=f"分批订单 {batch_id} 不存在"
        )
    
    batch_info = active_batch_orders[batch_id]
    
    return {
        "status": "success",
        "message": "获取分批订单状态成功",
        "batch_id": batch_id,
        "batch_info": batch_info
    }


@router.get("/batch-orders")
async def list_active_batch_orders():
    """
    列出所有活跃的分批订单
    
    获取当前系统中所有活跃的分批订单列表。
    
    Returns:
        dict: 活跃分批订单列表
    """
    return {
        "status": "success",
        "message": f"获取到 {len(active_batch_orders)} 个分批订单",
        "batch_orders": active_batch_orders
    }