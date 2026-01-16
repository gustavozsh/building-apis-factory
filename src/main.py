from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import os
from datetime import datetime, timezone

app = FastAPI(
    title="Building APIs Factory",
    description="A factory for building and deploying cloud-ready APIs",
    version="1.0.0"
)

# CORS middleware for cloud deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    environment: str
    version: str


class MessageResponse(BaseModel):
    message: str
    timestamp: str


@app.get("/", response_model=MessageResponse)
async def root():
    """Root endpoint - Welcome message"""
    return {
        "message": "Welcome to the Building APIs Factory - Your cloud-ready API platform",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for cloud monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": os.getenv("ENV", "production"),
        "version": "1.0.0"
    }


@app.get("/api/info", response_model=Dict[str, Any])
async def api_info():
    """API information endpoint"""
    return {
        "name": "Building APIs Factory",
        "description": "A platform for developing and deploying cloud-ready APIs",
        "features": [
            "FastAPI framework",
            "Docker containerization",
            "Cloud deployment ready",
            "Health monitoring",
            "CORS enabled"
        ],
        "cloud_platforms": [
            "AWS (ECS, Lambda, EC2)",
            "Azure (Container Instances, App Service)",
            "Google Cloud (Cloud Run, GKE)"
        ]
    }
