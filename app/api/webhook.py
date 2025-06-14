#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook API routes

This module contains API routes for handling webhooks,
specifically TradingView alerts forwarded to DingTalk.

Author: Dexter
Date: 2025
"""

import logging
import json
import requests
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from app.core.config import config


# Configure logger
logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter(
    prefix="/webhook",
    tags=["webhook"]
)


@router.post("/tradingview")
async def receive_tradingview_alert(request: Request):
    """
    Receive TradingView alert and forward to DingTalk
    
    This endpoint accepts any data format from TradingView alerts
    and forwards them to the configured DingTalk webhook.
    
    Args:
        request (Request): FastAPI request object containing the alert data
        
    Returns:
        dict: Response with status information and received data
        
    Raises:
        HTTPException: If alert processing or forwarding fails
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
        
        # Determine webhook URL based on message content
        webhook_url = config.DINGTALK_WEBHOOK_URL  # Default webhook
        
        # Check if message contains BTC or ETH trading pairs
        if "BTCUSD.P" in message_content or "BTC" in message_content:
            webhook_url = config.BTC15_WEBHOOK_URL
            logger.info("Using BTC15 webhook for BTC-related alert")
        elif "ETHUSD.P" in message_content or "ETH" in message_content:
            webhook_url = config.ETH15_WEBHOOK_URL
            logger.info("Using ETH15 webhook for ETH-related alert")
        else:
            logger.info("Using default webhook for general alert")
        
        # Prepare DingTalk message payload
        payload = {
            "msgtype": "text",
            "text": {
                "content": message_content
            }
        }
        
        # Send directly to DingTalk
        response = requests.post(
            webhook_url,
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