#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingView Alert to DingTalk FastAPI Service

This module provides a FastAPI service that receives TradingView alerts
and forwards them to DingTalk groups via webhook.

Author: Dexter
Date: 2025
"""

import logging
import json
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
import uvicorn


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DingTalk webhook URL
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=adc9e3e8927b10ccdcdaaae59f8cbf964455feaaf95b43356de0d8f514367235"

# Initialize FastAPI app
app = FastAPI(
    title="TradingView Alert Monitor",
    description="Receives TradingView alerts and forwards to DingTalk",
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


if __name__ == "__main__":    
    # Run the FastAPI application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=80,
        reload=True,
        log_level="info"
    )
