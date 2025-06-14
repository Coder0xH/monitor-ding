#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingView Alert to DingTalk FastAPI Service with Binance Futures Trading

This is the main application entry point that initializes the FastAPI app
and includes all API routes from the app.api package.

Author: Dexter
Date: 2025
"""

import logging
import uvicorn
from fastapi import FastAPI
from app.core.config import config
from app.api.router import api_router


# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    # Initialize FastAPI app
    app = FastAPI(
        title="TradingView Alert Monitor & Binance Futures Trading",
        description="Receives TradingView alerts, forwards to DingTalk, and provides Binance futures trading API",
        version="1.0.0"
    )
    
    # Include API routes
    app.include_router(api_router)
    
    return app


# Create app instance
app = create_app()





if __name__ == "__main__":    
    # Run the FastAPI application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=80,
        reload=True,
        log_level="info"
    )
