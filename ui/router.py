"""
UI Router for Multi-Agent Framework

This module contains all the UI-related routes for serving web pages and static assets.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Create UI router
router = APIRouter()

# Get the UI directory path
UI_DIR = Path(__file__).parent

# Mount static files
def mount_static_files(app):
    """Mount static files for the UI"""
    app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")

@router.get("/", response_class=HTMLResponse)
async def serve_config_page():
    """Serve the agent configuration UI"""
    try:
        config_path = UI_DIR / "pages" / "config.html"
        with open(config_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Configuration UI file not found")

@router.get("/chat", response_class=HTMLResponse)
async def serve_chat_page():
    """Serve the chat UI"""
    try:
        chat_path = UI_DIR / "pages" / "chat.html"
        with open(chat_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat UI file not found")

@router.get("/health")
async def ui_health_check():
    """Health check endpoint for UI services"""
    return {
        "status": "healthy",
        "service": "Multi-Agent Framework UI",
        "ui_directory": str(UI_DIR),
        "pages_available": [
            "/",
            "/chat"
        ]
    }