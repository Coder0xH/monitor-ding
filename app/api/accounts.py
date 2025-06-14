#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
账户管理API路由

本模块包含期货账户余额查询、API密钥管理等操作的API路由。
支持多API密钥管理、账户余额查询、交易历史等功能。

Author: Dexter
Date: 2025
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from app.core.config import config
from app.core.models import APIKeyConfig


# 配置日志
logger = logging.getLogger(__name__)

# 创建路由实例
router = APIRouter(
    prefix="/api/accounts",
    tags=["accounts"]
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


@router.get("/balance")
async def get_futures_balance(api_key_id: str = None):
    """
    获取期货账户余额
    
    从币安账户检索期货账户余额信息。
    
    Args:
        api_key_id (str, optional): API密钥ID，如果不提供则使用默认密钥
    
    Returns:
        dict: 包含账户余额详情的响应
        
    Raises:
        HTTPException: 如果币安API不可用或获取余额失败
    """
    # 获取交易所实例
    exchange = get_exchange_instance(api_key_id)
    if not exchange:
        raise HTTPException(
            status_code=503,
            detail="币安期货交易不可用，请检查API凭证"
        )
    
    try:
        balance = exchange.fetch_balance()
        
        logger.info("获取期货账户余额成功")
        return {
            "status": "success",
            "message": "获取期货账户余额成功",
            "balance": balance
        }
        
    except Exception as e:
        logger.error(f"获取余额错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取余额失败: {str(e)}"
        )


@router.get("/info")
async def get_account_info(api_key_id: str = None):
    """
    获取账户信息
    
    获取详细的账户信息，包括权限、费率等。
    
    Args:
        api_key_id (str, optional): API密钥ID，如果不提供则使用默认密钥
        
    Returns:
        dict: 包含账户信息的响应
        
    Raises:
        HTTPException: 如果币安API不可用或获取信息失败
    """
    # 获取交易所实例
    exchange = get_exchange_instance(api_key_id)
    if not exchange:
        raise HTTPException(
            status_code=503,
            detail="币安期货交易不可用，请检查API凭证"
        )
    
    try:
        # 获取账户信息
        account_info = exchange.fetch_account()
        
        logger.info("获取账户信息成功")
        return {
            "status": "success",
            "message": "获取账户信息成功",
            "account_info": account_info
        }
        
    except Exception as e:
        logger.error(f"获取账户信息错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取账户信息失败: {str(e)}"
        )


@router.post("/api-keys")
async def add_api_key(api_config: APIKeyConfig):
    """
    添加API密钥
    
    向系统中添加新的API密钥配置。
    
    Args:
        api_config (APIKeyConfig): API密钥配置信息
        
    Returns:
        dict: 添加结果
        
    Raises:
        HTTPException: 如果添加失败
    """
    try:
        # 添加API密钥到配置
        config.add_api_key(
            key_id=api_config.key_id,
            api_key=api_config.api_key,
            secret=api_config.secret,
            name=api_config.name,
            testnet=api_config.testnet
        )
        
        logger.info(f"API密钥 {api_config.key_id} 添加成功")
        return {
            "status": "success",
            "message": f"API密钥 {api_config.key_id} 添加成功",
            "key_id": api_config.key_id,
            "name": api_config.name
        }
        
    except Exception as e:
        logger.error(f"添加API密钥错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"添加API密钥失败: {str(e)}"
        )


@router.get("/api-keys")
async def list_api_keys():
    """
    列出所有API密钥
    
    获取系统中配置的所有API密钥列表（不包含敏感信息）。
    
    Returns:
        dict: API密钥列表
    """
    try:
        api_keys = config.list_api_keys()
        
        logger.info(f"获取到 {len(api_keys)} 个API密钥")
        return {
            "status": "success",
            "message": f"获取到 {len(api_keys)} 个API密钥",
            "api_keys": api_keys
        }
        
    except Exception as e:
        logger.error(f"获取API密钥列表错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取API密钥列表失败: {str(e)}"
        )


@router.get("/api-keys/{key_id}")
async def get_api_key(key_id: str):
    """
    获取指定API密钥信息
    
    获取指定ID的API密钥信息（不包含敏感信息）。
    
    Args:
        key_id (str): API密钥ID
        
    Returns:
        dict: API密钥信息
        
    Raises:
        HTTPException: 如果密钥不存在
    """
    try:
        api_key_info = config.get_api_key(key_id)
        
        if not api_key_info:
            raise HTTPException(
                status_code=404,
                detail=f"API密钥 {key_id} 不存在"
            )
        
        # 移除敏感信息
        safe_info = {
            "key_id": api_key_info["key_id"],
            "name": api_key_info.get("name", ""),
            "testnet": api_key_info.get("testnet", False),
            "created_at": api_key_info.get("created_at", "")
        }
        
        logger.info(f"获取API密钥 {key_id} 信息成功")
        return {
            "status": "success",
            "message": f"获取API密钥 {key_id} 信息成功",
            "api_key": safe_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取API密钥信息错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取API密钥信息失败: {str(e)}"
        )


@router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: str):
    """
    删除API密钥
    
    从系统中删除指定的API密钥。
    
    Args:
        key_id (str): 要删除的API密钥ID
        
    Returns:
        dict: 删除结果
        
    Raises:
        HTTPException: 如果删除失败
    """
    try:
        success = config.delete_api_key(key_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"API密钥 {key_id} 不存在"
            )
        
        logger.info(f"API密钥 {key_id} 删除成功")
        return {
            "status": "success",
            "message": f"API密钥 {key_id} 删除成功",
            "key_id": key_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除API密钥错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"删除API密钥失败: {str(e)}"
        )


@router.get("/trading-fees")
async def get_trading_fees(api_key_id: str = None):
    """
    获取交易费率
    
    获取当前账户的交易费率信息。
    
    Args:
        api_key_id (str, optional): API密钥ID，如果不提供则使用默认密钥
        
    Returns:
        dict: 交易费率信息
        
    Raises:
        HTTPException: 如果获取失败
    """
    # 获取交易所实例
    exchange = get_exchange_instance(api_key_id)
    if not exchange:
        raise HTTPException(
            status_code=503,
            detail="币安期货交易不可用，请检查API凭证"
        )
    
    try:
        # 获取交易费率
        fees = exchange.fetch_trading_fees()
        
        logger.info("获取交易费率成功")
        return {
            "status": "success",
            "message": "获取交易费率成功",
            "fees": fees
        }
        
    except Exception as e:
        logger.error(f"获取交易费率错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取交易费率失败: {str(e)}"
        )


@router.get("/status")
async def get_account_status(api_key_id: str = None):
    """
    获取账户状态
    
    检查账户的交易权限和状态。
    
    Args:
        api_key_id (str, optional): API密钥ID，如果不提供则使用默认密钥
        
    Returns:
        dict: 账户状态信息
        
    Raises:
        HTTPException: 如果获取失败
    """
    # 获取交易所实例
    exchange = get_exchange_instance(api_key_id)
    if not exchange:
        raise HTTPException(
            status_code=503,
            detail="币安期货交易不可用，请检查API凭证"
        )
    
    try:
        # 获取账户状态
        status = exchange.fetch_status()
        
        logger.info("获取账户状态成功")
        return {
            "status": "success",
            "message": "获取账户状态成功",
            "account_status": status
        }
        
    except Exception as e:
        logger.error(f"获取账户状态错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取账户状态失败: {str(e)}"
        )