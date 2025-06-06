#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingView Alert to DingTalk FastAPI Service with Binance Futures Trading

This module provides a FastAPI service that receives TradingView alerts,
forwards them to DingTalk groups via webhook, and provides Binance futures trading API.

Author: Dexter
Date: 2025
"""

import logging
import json
import requests
import ccxt
import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DingTalk webhook URL
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=adc9e3e8927b10ccdcdaaae59f8cbf964455feaaf95b43356de0d8f514367235"

# Binance API configuration
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')

# Initialize Binance exchange for futures trading
binance_futures = None
if BINANCE_API_KEY and BINANCE_SECRET_KEY:
    try:
        binance_futures = ccxt.binance({
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_SECRET_KEY,
            'sandbox': False,  # Set to True for testnet
            'options': {
                'defaultType': 'future',  # Use futures trading
            },
        })
        logger.info("Binance futures exchange initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Binance futures exchange: {e}")
else:
    logger.warning("Binance API credentials not provided. Futures trading will be disabled.")


# Pydantic models for API requests
class FuturesOrderRequest(BaseModel):
    """
    Futures order request model
    
    Attributes:
        symbol (str): Trading pair symbol (e.g., 'BTCUSDT')
        side (str): Order side ('buy' or 'sell')
        type (str): Order type ('market', 'limit', 'stop', 'take_profit')
        amount (float): Order amount in base currency
        price (Optional[float]): Order price for limit orders
        stop_price (Optional[float]): Stop price for stop orders
        reduce_only (bool): Whether this is a reduce-only order
        leverage (Optional[int]): Leverage multiplier (1-125)
    """
    symbol: str
    side: str  # 'buy' or 'sell'
    type: str  # 'market', 'limit', 'stop', 'take_profit'
    amount: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    reduce_only: bool = False
    leverage: Optional[int] = None


class PositionRequest(BaseModel):
    """
    Position management request model
    
    Attributes:
        symbol (str): Trading pair symbol (e.g., 'BTCUSDT')
        leverage (int): Leverage multiplier (1-125)
    """
    symbol: str
    leverage: int


# Initialize FastAPI app
app = FastAPI(
    title="TradingView Alert Monitor & Binance Futures Trading",
    description="Receives TradingView alerts, forwards to DingTalk, and provides Binance futures trading API",
    version="1.0.0"
)


@app.post("/webhook/tradingview")
async def receive_tradingview_alert(request: Request):
    """
    Receive TradingView alert and forward to DingTalk
    Accept any data format and forward as-is
    
    Args:
        request (Request): FastAPI request object
        
    Returns:
        dict: Response with status information
        
    Raises:
        HTTPException: If alert processing fails
    """
    try:
        # Get raw request data
        client_ip = request.client.host
        raw_data = await request.body()
        
        # Get current timestamp for logging
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Try to parse as JSON first, fallback to text
        try:
            data = json.loads(raw_data.decode('utf-8'))
            logger.info(f"Received JSON data from {client_ip}: {data}")
            # Format JSON data for DingTalk - keep original format
            if isinstance(data, dict):
                if data:  # Check if dict is not empty
                    message_content = ""
                    for key, value in data.items():
                        message_content += f"{key}: {value}\n"
                else:
                    message_content = "{}"  # Empty dict
            else:
                message_content = json.dumps(data, indent=2)
        except:
            # If not JSON, treat as plain text
            data = raw_data.decode('utf-8')
            logger.info(f"Received text data from {client_ip}: {data}")
            message_content = data if data.strip() else "Empty message"
        
        # Prepare DingTalk message payload
        payload = {
            "msgtype": "text",
            "text": {
                "content": message_content
            }
        }
        
        # Send directly to DingTalk
        response = requests.post(
            DINGTALK_WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                logger.info(f"Successfully sent alert to DingTalk")
                return {
                    "status": "success",
                    "message": "Alert sent to DingTalk successfully",
                    "received_data": data,
                    "timestamp": timestamp
                }
            else:
                logger.error(f"DingTalk API error: {result.get('errmsg')}")
                raise HTTPException(
                    status_code=500,
                    detail=f"DingTalk API error: {result.get('errmsg')}"
                )
        else:
            logger.error(f"HTTP error {response.status_code}: {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"HTTP error {response.status_code}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing alert: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/api/futures/order")
async def create_futures_order(order: FuturesOrderRequest):
    """
    Create a futures order on Binance
    
    Args:
        order (FuturesOrderRequest): Order details
        
    Returns:
        dict: Order creation result
        
    Raises:
        HTTPException: If order creation fails
    """
    if not binance_futures:
        raise HTTPException(
            status_code=503,
            detail="Binance futures trading is not available. Please check API credentials."
        )
    
    try:
        # Set leverage if specified
        if order.leverage:
            await set_leverage_internal(order.symbol, order.leverage)
        
        # Prepare order parameters
        order_params = {
            'symbol': order.symbol,
            'side': order.side,
            'type': order.type,
            'amount': order.amount,
        }
        
        # Add price for limit orders
        if order.type == 'limit' and order.price:
            order_params['price'] = order.price
        
        # Add stop price for stop orders
        if order.type in ['stop', 'take_profit'] and order.stop_price:
            order_params['stopPrice'] = order.stop_price
        
        # Add reduce only flag
        if order.reduce_only:
            order_params['reduceOnly'] = True
        
        # Create the order
        result = binance_futures.create_order(**order_params)
        
        logger.info(f"Futures order created successfully: {result['id']}")
        return {
            "status": "success",
            "message": "Futures order created successfully",
            "order_id": result['id'],
            "order_details": result
        }
        
    except Exception as e:
        logger.error(f"Error creating futures order: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create futures order: {str(e)}"
        )


async def set_leverage_internal(symbol: str, leverage: int):
    """
    Internal function to set leverage for a trading pair
    
    Args:
        symbol (str): Trading pair symbol
        leverage (int): Leverage multiplier
        
    Raises:
        Exception: If leverage setting fails
    """
    try:
        # Set leverage using ccxt
        result = binance_futures.set_leverage(leverage, symbol)
        logger.info(f"Leverage set to {leverage}x for {symbol}")
        return result
    except Exception as e:
        logger.error(f"Error setting leverage: {str(e)}")
        raise e


@app.post("/api/futures/leverage")
async def set_leverage(position: PositionRequest):
    """
    Set leverage for a trading pair
    
    Args:
        position (PositionRequest): Position details with symbol and leverage
        
    Returns:
        dict: Leverage setting result
        
    Raises:
        HTTPException: If leverage setting fails
    """
    if not binance_futures:
        raise HTTPException(
            status_code=503,
            detail="Binance futures trading is not available. Please check API credentials."
        )
    
    try:
        # Set leverage using ccxt
        result = binance_futures.set_leverage(position.leverage, position.symbol)
        
        logger.info(f"Leverage set to {position.leverage}x for {position.symbol}")
        return {
            "status": "success",
            "message": f"Leverage set to {position.leverage}x for {position.symbol}",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error setting leverage: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set leverage: {str(e)}"
        )


@app.get("/api/futures/positions")
async def get_positions():
    """
    Get all open futures positions
    
    Returns:
        dict: List of open positions
        
    Raises:
        HTTPException: If fetching positions fails
    """
    if not binance_futures:
        raise HTTPException(
            status_code=503,
            detail="Binance futures trading is not available. Please check API credentials."
        )
    
    try:
        positions = binance_futures.fetch_positions()
        # Filter only positions with non-zero size
        open_positions = [pos for pos in positions if float(pos['contracts']) != 0]
        
        logger.info(f"Retrieved {len(open_positions)} open positions")
        return {
            "status": "success",
            "message": f"Retrieved {len(open_positions)} open positions",
            "positions": open_positions
        }
        
    except Exception as e:
        logger.error(f"Error fetching positions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch positions: {str(e)}"
        )


@app.get("/api/futures/balance")
async def get_futures_balance():
    """
    Get futures account balance
    
    Returns:
        dict: Account balance information
        
    Raises:
        HTTPException: If fetching balance fails
    """
    if not binance_futures:
        raise HTTPException(
            status_code=503,
            detail="Binance futures trading is not available. Please check API credentials."
        )
    
    try:
        balance = binance_futures.fetch_balance()
        
        logger.info("Retrieved futures account balance")
        return {
            "status": "success",
            "message": "Retrieved futures account balance",
            "balance": balance
        }
        
    except Exception as e:
        logger.error(f"Error fetching balance: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch balance: {str(e)}"
        )


@app.get("/api/futures/orders/{symbol}")
async def get_open_orders(symbol: str):
    """
    Get open orders for a specific symbol
    
    Args:
        symbol (str): Trading pair symbol
        
    Returns:
        dict: List of open orders
        
    Raises:
        HTTPException: If fetching orders fails
    """
    if not binance_futures:
        raise HTTPException(
            status_code=503,
            detail="Binance futures trading is not available. Please check API credentials."
        )
    
    try:
        orders = binance_futures.fetch_open_orders(symbol)
        
        logger.info(f"Retrieved {len(orders)} open orders for {symbol}")
        return {
            "status": "success",
            "message": f"Retrieved {len(orders)} open orders for {symbol}",
            "orders": orders
        }
        
    except Exception as e:
        logger.error(f"Error fetching orders: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch orders: {str(e)}"
        )


@app.delete("/api/futures/orders/{order_id}")
async def cancel_order(order_id: str, symbol: str):
    """
    Cancel a specific order
    
    Args:
        order_id (str): Order ID to cancel
        symbol (str): Trading pair symbol (query parameter)
        
    Returns:
        dict: Order cancellation result
        
    Raises:
        HTTPException: If order cancellation fails
    """
    if not binance_futures:
        raise HTTPException(
            status_code=503,
            detail="Binance futures trading is not available. Please check API credentials."
        )
    
    try:
        result = binance_futures.cancel_order(order_id, symbol)
        
        logger.info(f"Order {order_id} cancelled successfully")
        return {
            "status": "success",
            "message": f"Order {order_id} cancelled successfully",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel order: {str(e)}"
        )


@app.get("/api/futures/ticker/{symbol}")
async def get_ticker(symbol: str):
    """
    Get ticker information for a specific symbol
    
    Args:
        symbol (str): Trading pair symbol
        
    Returns:
        dict: Ticker information
        
    Raises:
        HTTPException: If fetching ticker fails
    """
    if not binance_futures:
        raise HTTPException(
            status_code=503,
            detail="Binance futures trading is not available. Please check API credentials."
        )
    
    try:
        ticker = binance_futures.fetch_ticker(symbol)
        
        logger.info(f"Retrieved ticker for {symbol}")
        return {
            "status": "success",
            "message": f"Retrieved ticker for {symbol}",
            "ticker": ticker
        }
        
    except Exception as e:
        logger.error(f"Error fetching ticker: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch ticker: {str(e)}"
        )


if __name__ == "__main__":    
    # Run the FastAPI application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=80,
        reload=True,
        log_level="info"
    )
