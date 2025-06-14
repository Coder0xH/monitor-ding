#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main API router

This module aggregates all API routes and provides a single router
for the FastAPI application to include.

Author: Dexter
Date: 2025
"""

from fastapi import APIRouter
from app.api import webhook, futures, orders, positions, accounts


# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(webhook.router)
api_router.include_router(futures.router)
api_router.include_router(orders.router)
api_router.include_router(positions.router)
api_router.include_router(accounts.router)
# api_router.include_router(market.router)  # market module not implemented yet