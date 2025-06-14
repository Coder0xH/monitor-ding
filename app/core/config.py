#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application configuration module

This module contains all configuration settings for the application,
including API keys, URLs, and other environment-specific settings.

Author: Dexter
Date: 2025
"""

import os
import logging
import ccxt
from typing import Optional, Dict


class Config:
    """
    应用配置类
    
    管理所有配置设置，包括API凭证、webhook URL和交易所初始化
    支持多个API密钥管理
    """
    
    # DingTalk webhook URL
    DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=adc9e3e8927b10ccdcdaaae59f8cbf964455feaaf95b43356de0d8f514367235"
    BTC15_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=f146db6035ab5ba048bb826d8e7ebd4cb425b8ba343f789be9d970e8740bc140"
    ETH15_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=45a874c63ff28f0695b4982cff42e310eb3e012b764055302c9ef708abe3a49a"
    
    # 默认Binance API配置 (向后兼容)
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
    
    # 多API密钥存储 (内存存储，生产环境建议使用数据库)
    api_keys_storage: Dict[str, dict] = {}
    
    # 日志配置
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @classmethod
    def add_api_key(cls, key_id: str, name: str, api_key: str, secret_key: str, is_testnet: bool = False) -> bool:
        """
        添加API密钥到存储中
        
        Args:
            key_id (str): API密钥唯一标识符
            name (str): API密钥名称/描述
            api_key (str): API密钥
            secret_key (str): 密钥
            is_testnet (bool): 是否为测试网
            
        Returns:
            bool: 是否添加成功
        """
        try:
            cls.api_keys_storage[key_id] = {
                'name': name,
                'api_key': api_key,
                'secret_key': secret_key,
                'is_active': True,
                'is_testnet': is_testnet
            }
            return True
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"添加API密钥失败: {e}")
            return False
    
    @classmethod
    def get_api_key(cls, key_id: str) -> Optional[dict]:
        """
        获取指定的API密钥配置
        
        Args:
            key_id (str): API密钥ID
            
        Returns:
            Optional[dict]: API密钥配置或None
        """
        return cls.api_keys_storage.get(key_id)
    
    @classmethod
    def list_api_keys(cls) -> Dict[str, dict]:
        """
        获取所有API密钥列表
        
        Returns:
            Dict[str, dict]: 所有API密钥配置
        """
        return cls.api_keys_storage.copy()
    
    @classmethod
    def remove_api_key(cls, key_id: str) -> bool:
        """
        删除指定的API密钥
        
        Args:
            key_id (str): API密钥ID
            
        Returns:
            bool: 是否删除成功
        """
        if key_id in cls.api_keys_storage:
            del cls.api_keys_storage[key_id]
            return True
        return False
    
    @classmethod
    def get_binance_futures_exchange(cls, api_key_id: Optional[str] = None) -> Optional[ccxt.binance]:
        """
        初始化并返回币安期货交易所实例
        
        Args:
            api_key_id (Optional[str]): 指定的API密钥ID，如果为None则使用默认配置
            
        Returns:
            Optional[ccxt.binance]: 币安交易所实例或None（如果凭证缺失）
        """
        logger = logging.getLogger(__name__)
        
        api_key = None
        secret_key = None
        is_testnet = False
        
        # 如果指定了API密钥ID，使用指定的密钥
        if api_key_id:
            key_config = cls.get_api_key(api_key_id)
            if key_config and key_config.get('is_active', True):
                api_key = key_config['api_key']
                secret_key = key_config['secret_key']
                is_testnet = key_config.get('is_testnet', False)
            else:
                logger.error(f"API密钥ID {api_key_id} 不存在或未激活")
                return None
        else:
            # 使用默认配置
            api_key = cls.BINANCE_API_KEY
            secret_key = cls.BINANCE_SECRET_KEY
        
        if api_key and secret_key:
            try:
                exchange = ccxt.binance({
                    'apiKey': api_key,
                    'secret': secret_key,
                    'sandbox': is_testnet,  # 根据配置设置是否为测试网
                    'options': {
                        'defaultType': 'future',  # 使用期货交易
                    },
                })
                logger.info(f"币安期货交易所初始化成功 (API密钥ID: {api_key_id or 'default'})")
                return exchange
            except Exception as e:
                logger.error(f"初始化币安期货交易所失败: {e}")
                return None
        else:
            logger.warning("币安API凭证未提供，期货交易将被禁用")
            return None


# Global configuration instance
config = Config()