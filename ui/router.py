"""
UI Router for Multi-Agent Framework

This module contains all the UI-related routes for serving web pages and static assets.
"""

import os
from fastapi import APIRouter, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys

# Add the project root to the Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from auth import is_session_valid, authenticate_pin

# Create UI router
router = APIRouter()

# Get the UI directory path
UI_DIR = Path(__file__).parent

def is_authenticated(request: Request):
    """Check if user is authenticated"""
    session_id = request.headers.get("x-session-id") or request.cookies.get("session-id")
    return session_id and is_session_valid(session_id)

def require_auth(request: Request):
    """Dependency to require authentication"""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")
    return True

# Mount static files
def mount_static_files(app):
    """Mount static files for the UI"""
    app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")

@router.get("/", response_class=HTMLResponse)
async def serve_config_page(request: Request):
    """Serve the agent configuration UI with PIN protection"""
    # Check authentication first
    session_id = request.headers.get("x-session-id") or request.cookies.get("session-id") or request.query_params.get("session_id")
    
    # Validate the session using the session ID directly
    from auth import is_session_valid
    if not session_id or not is_session_valid(session_id):
        return await serve_pin_page()
    
    try:
        config_path = UI_DIR / "pages" / "config.html"
        with open(config_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Configuration UI file not found")

@router.get("/pin", response_class=HTMLResponse)
async def serve_pin_page():
    """Serve the PIN entry page"""
    pin_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configuration Access - Multi-Agent Framework</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .pin-container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            text-align: center;
            min-width: 300px;
        }
        .pin-container h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 24px;
        }
        .pin-container p {
            color: #666;
            margin-bottom: 30px;
        }
        .pin-input {
            width: 100%;
            max-width: 200px;
            padding: 12px 16px;
            font-size: 18px;
            border: 2px solid #ddd;
            border-radius: 6px;
            text-align: center;
            letter-spacing: 4px;
            margin-bottom: 20px;
            transition: border-color 0.3s;
        }
        .pin-input:focus {
            outline: none;
            border-color: #667eea;
        }
        .pin-button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .pin-button:hover {
            background: #5a6fd8;
        }
        .pin-button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .error-message {
            color: #e74c3c;
            margin-top: 15px;
            display: none;
        }
        .lock-icon {
            font-size: 48px;
            color: #667eea;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="pin-container">
        <div class="lock-icon">🔒</div>
        <h1>Configuration Access</h1>
        <p>Enter your 4-digit PIN to access the configuration page</p>
        <form id="pinForm">
            <input type="password" id="pinInput" class="pin-input" maxlength="4" pattern="[0-9]{4}" placeholder="••••" required>
            <br>
            <button type="submit" class="pin-button" id="submitBtn">Access Configuration</button>
        </form>
        <div class="error-message" id="errorMessage">Invalid PIN. Please try again.</div>
    </div>

    <script>
        const pinForm = document.getElementById('pinForm');
        const pinInput = document.getElementById('pinInput');
        const submitBtn = document.getElementById('submitBtn');
        const errorMessage = document.getElementById('errorMessage');

        pinInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
            errorMessage.style.display = 'none';
        });

        pinForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const pin = pinInput.value;
            
            if (pin.length !== 4) {
                errorMessage.textContent = 'PIN must be 4 digits';
                errorMessage.style.display = 'block';
                return;
            }

            submitBtn.disabled = true;
            submitBtn.textContent = 'Verifying...';

            try {
                const response = await fetch('/auth', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams({ pin: pin })
                });

                if (response.ok) {
                    const data = await response.json();
                    localStorage.setItem('session-id', data.session_id);
                    // Add session ID as query param for immediate authentication
                    window.location.href = '/?session_id=' + data.session_id;
                } else {
                    const error = await response.json();
                    errorMessage.textContent = error.detail || 'Invalid PIN';
                    errorMessage.style.display = 'block';
                    pinInput.value = '';
                    pinInput.focus();
                }
            } catch (error) {
                errorMessage.textContent = 'Error connecting to server';
                errorMessage.style.display = 'block';
            }

            submitBtn.disabled = false;
            submitBtn.textContent = 'Access Configuration';
        });

        pinInput.focus();
    </script>
</body>
</html>
    '''
    return HTMLResponse(content=pin_html)

@router.post("/auth")
async def authenticate_with_pin(pin: str = Form(...)):
    """Authenticate with PIN"""
    try:
        session_id = authenticate_pin(pin)
        return {"success": True, "session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

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