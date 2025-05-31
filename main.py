#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingView Alert to DingTalk FastAPI Service

This module provides a FastAPI service that receives TradingView alerts
and forwards them to DingTalk groups via webhook.

Author: Dexter
Date: 2024
"""

import logging
from datetime import datetime

import requests
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

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


class TradingViewAlert(BaseModel):
    """
    TradingView alert data model
    
    This class defines the structure of incoming TradingView alerts.
    """
    symbol: str = Field(..., description="Trading symbol")
    action: str = Field(..., description="Trading action (buy/sell)")
    price: float = Field(..., description="Current price")
    time: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Alert timestamp")
    message: str = Field(default="", description="Additional message")


class DingTalkService:
    """
    DingTalk notification service
    
    This class handles sending messages to DingTalk groups via webhook.
    """
    
    def __init__(self, webhook_url: str):
        """
        Initialize DingTalk service
        
        Args:
            webhook_url (str): DingTalk webhook URL
        """
        self.webhook_url = webhook_url
    
    def send_message(self, alert: TradingViewAlert) -> bool:
        """
        Send alert message to DingTalk
        
        Args:
            alert (TradingViewAlert): Alert data to send
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            # Format message for DingTalk
            message_text = self._format_alert_message(alert)
            
            # Prepare DingTalk message payload
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message_text
                }
            }
            
            # Send request to DingTalk
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.info(f"Successfully sent alert to DingTalk: {alert.symbol}")
                    return True
                else:
                    logger.error(f"DingTalk API error: {result.get('errmsg')}")
                    return False
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending to DingTalk: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to DingTalk: {str(e)}")
            return False
    
    def _format_alert_message(self, alert: TradingViewAlert) -> str:
        """
        Format alert data into readable message
        
        Args:
            alert (TradingViewAlert): Alert data
            
        Returns:
            str: Formatted message string
        """
        action_emoji = "🟢" if alert.action.lower() == "buy" else "🔴"
        
        message = f"""{action_emoji} TradingView Alert

📊 Symbol: {alert.symbol}
🎯 Action: {alert.action.upper()}
💰 Price: ${alert.price}
⏰ Time: {alert.time}
"""
        
        if alert.message:
            message += f"\n📝 Message: {alert.message}"
            
        return message


# Initialize DingTalk service
dingtalk_service = DingTalkService(DINGTALK_WEBHOOK_URL)


@app.get("/")
async def root():
    """
    Root endpoint for health check
    
    Returns:
        dict: Service status information
    """
    return {
        "service": "TradingView Alert Monitor",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/webhook/tradingview")
async def receive_tradingview_alert(alert: TradingViewAlert, request: Request):
    """
    Receive TradingView alert and forward to DingTalk
    
    Args:
        alert (TradingViewAlert): Alert data from TradingView
        request (Request): FastAPI request object
        
    Returns:
        dict: Response with status information
        
    Raises:
        HTTPException: If alert processing fails
    """
    try:
        # Log incoming alert
        client_ip = request.client.host
        logger.info(f"Received alert from {client_ip}: {alert.symbol} - {alert.action}")
        
        # Send to DingTalk
        success = dingtalk_service.send_message(alert)
        
        if success:
            return {
                "status": "success",
                "message": "Alert sent to DingTalk successfully",
                "alert_id": f"{alert.symbol}_{alert.time}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send alert to DingTalk"
            )
            
    except Exception as e:
        logger.error(f"Error processing alert: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/test/dingtalk")
async def test_dingtalk_connection():
    """
    Test DingTalk webhook connection
    
    Returns:
        dict: Test result
    """
    test_alert = TradingViewAlert(
        symbol="TEST",
        action="BUY",
        price=100.0,
        message="This is a test message from TradingView Alert Monitor"
    )
    
    success = dingtalk_service.send_message(test_alert)
    
    return {
        "status": "success" if success else "failed",
        "message": "Test message sent" if success else "Failed to send test message"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the FastAPI application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=80,
        reload=True,
        log_level="info"
    )
