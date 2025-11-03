"""
FastAPI Server for MMDVM Dashboard
Provides REST API and WebSocket endpoints
"""
import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .state import state

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MMDVM Dashboard",
    description="Real-time monitoring for MMDVMHost and gateway programs",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.get("/api/config")
async def get_config():
    """Get dashboard configuration"""
    return {
        "title": config.get('dashboard', 'title'),
        "description": config.get('dashboard', 'description'),
        "refresh_interval": config.get('dashboard', 'refresh_interval')
    }


@app.get("/api/status")
async def get_status():
    """Get current system status"""
    return state.get_status()


@app.get("/api/transmissions")
async def get_transmissions():
    """Get active transmissions"""
    return {
        "active": state.get_active_transmissions(),
        "recent": state.get_recent_calls(20)
    }


@app.get("/api/events")
async def get_events(limit: int = 50):
    """Get recent events"""
    return {
        "events": state.get_events(limit)
    }


@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    status = state.get_status()
    return {
        "total_calls_today": status['total_calls_today'],
        "calls_by_mode": status['calls_by_mode'],
        "active_users": status['active_users'],
        "active_transmissions": status['active_transmissions'],
        "networks": status['networks'],
        "current_mode": status['current_mode']
    }


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection for real-time updates"""
    await websocket.accept()
    state.websocket_clients.add(websocket)
    logger.info(f"WebSocket client connected (total: {len(state.websocket_clients)})")
    
    try:
        # Send initial state
        await websocket.send_json({
            'type': 'initial_state',
            'status': state.get_status(),
            'active_transmissions': state.get_active_transmissions(),
            'recent_calls': state.get_recent_calls(10),
            'events': state.get_events(20)
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages (mainly to detect disconnect)
                data = await websocket.receive_text()
                # Could handle commands here in the future
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    
    finally:
        state.websocket_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected (remaining: {len(state.websocket_clients)})")


# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve dashboard HTML"""
    html_path = Path(__file__).parent / 'static' / 'dashboard.html'
    if not html_path.exists():
        return HTMLResponse(
            "<h1>Dashboard HTML not found</h1>"
            "<p>Please create dashboard/static/dashboard.html</p>",
            status_code=404
        )
    with open(html_path, 'r') as f:
        return HTMLResponse(f.read())


# Mount static files
static_path = Path(__file__).parent / 'static'
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize monitors on startup"""
    logger.info("MMDVM Dashboard server starting...")
    # Monitors are initialized in run_dashboard.py


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down MMDVM Dashboard...")
    from .monitor import monitor_manager
    monitor_manager.stop_all()
