#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic models for API requests and responses

This module contains all Pydantic models used for request validation
and response serialization in the FastAPI application.

Author: Dexter
Date: 2025
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class FuturesOrderRequest(BaseModel):
    """
    期货订单请求模型
    
    定义在币安创建期货订单的结构
    
    Attributes:
        symbol (str): 交易对符号 (例如: 'BTCUSDT')
        side (str): 订单方向 ('buy' 买入 或 'sell' 卖出)
        type (str): 订单类型 ('market' 市价, 'limit' 限价, 'stop' 止损, 'take_profit' 止盈)
        amount (float): 订单数量
        price (Optional[float]): 限价订单价格
        stop_price (Optional[float]): 止损订单触发价格
        reduce_only (bool): 是否为只减仓订单
        leverage (Optional[int]): 杠杆倍数 (1-125)
        api_key_id (Optional[str]): 指定使用的API密钥ID
        
        # 市价单参数
        is_market_order (bool): 是否为市价单
        position_type (Optional[str]): 仓位类型 ('full' 全仓, 'percentage' 百分比, 'fixed' 固定数量)
        percentage (Optional[float]): 百分比 (当position_type为percentage时)
        
        # 分批下单参数
        is_batch_order (bool): 是否为分批订单
        batch_count (Optional[int]): 分批数量
        batch_duration_minutes (Optional[int]): 分批时长(分钟)
        min_amount_per_batch (Optional[float]): 每批最小数量
        max_amount_per_batch (Optional[float]): 每批最大数量
        
        # 止盈止损参数
        take_profit_percentage (Optional[float]): 止盈百分比
        stop_loss_percentage (Optional[float]): 止损百分比
        is_partial_tp (bool): 是否部分止盈
        is_partial_sl (bool): 是否部分止损
        partial_percentage (Optional[float]): 部分平仓百分比
    """
    symbol: str
    side: str  # 'buy' 买入 或 'sell' 卖出
    type: str  # 'market' 市价, 'limit' 限价, 'stop' 止损, 'take_profit' 止盈
    amount: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    reduce_only: bool = False
    leverage: Optional[int] = None
    api_key_id: Optional[str] = None  # 指定使用的API密钥ID
    
    # 市价单参数
    is_market_order: bool = False
    position_type: Optional[str] = None  # 'full' 全仓, 'percentage' 百分比, 'fixed' 固定数量
    percentage: Optional[float] = None  # 百分比 (0-100)
    
    # 分批下单参数
    is_batch_order: bool = False
    batch_count: Optional[int] = None  # 分批数量
    batch_duration_minutes: Optional[int] = None  # 分批时长(分钟)
    min_amount_per_batch: Optional[float] = None  # 每批最小数量
    max_amount_per_batch: Optional[float] = None  # 每批最大数量
    
    # 止盈止损参数
    take_profit_percentage: Optional[float] = None  # 止盈百分比
    stop_loss_percentage: Optional[float] = None  # 止损百分比
    is_partial_tp: bool = False  # 是否部分止盈
    is_partial_sl: bool = False  # 是否部分止损
    partial_percentage: Optional[float] = None  # 部分平仓百分比 (0-100)


class PositionRequest(BaseModel):
    """
    仓位管理请求模型
    
    定义管理交易仓位的结构
    
    Attributes:
        symbol (str): 交易对符号 (例如: 'BTCUSDT')
        leverage (int): 杠杆倍数 (1-125)
        api_key_id (Optional[str]): 指定使用的API密钥ID
    """
    symbol: str
    leverage: int
    api_key_id: Optional[str] = None  # 指定使用的API密钥ID


class APIKeyConfig(BaseModel):
    """
    API密钥配置模型
    
    用于存储和管理多个API密钥
    
    Attributes:
        key_id (str): API密钥唯一标识符
        name (str): API密钥名称/描述
        api_key (str): API密钥
        secret_key (str): 密钥
        is_active (bool): 是否激活
        is_testnet (bool): 是否为测试网
    """
    key_id: str
    name: str
    api_key: str
    secret_key: str
    is_active: bool = True
    is_testnet: bool = False


class BulkActionRequest(BaseModel):
    """
    批量操作请求模型
    
    用于批量执行止盈止损等操作
    
    Attributes:
        action (str): 操作类型 ('take_profit' 止盈, 'stop_loss' 止损, 'close_all' 全部平仓)
        api_key_ids (Optional[List[str]]): 指定的API密钥ID列表
        symbols (Optional[List[str]]): 指定的交易对列表
        apply_to_all (bool): 是否应用到所有仓位
        percentage (Optional[float]): 操作百分比 (0-100)
    """
    action: str  # 'take_profit', 'stop_loss', 'close_all'
    api_key_ids: Optional[List[str]] = None
    symbols: Optional[List[str]] = None
    apply_to_all: bool = False
    percentage: Optional[float] = None  # 操作百分比 (0-100)


class APIResponse(BaseModel):
    """
    Standard API response model
    
    This model defines the standard structure for API responses.
    
    Attributes:
        status (str): Response status ('success' or 'error')
        message (str): Response message
        data (Optional[dict]): Response data payload
    """
    status: str
    message: str
    data: Optional[dict] = None