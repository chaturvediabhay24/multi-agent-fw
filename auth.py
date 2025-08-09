"""
Authentication module for Multi-Agent Framework

Shared authentication functions and session management.
"""

import os
import secrets
from typing import Set

# Simple session storage (in production, use Redis or database)
authenticated_sessions: Set[str] = set()

def get_config_pin() -> str:
    """Get the configuration PIN from environment variable"""
    return os.getenv("CONFIG_PIN", "1234")

def create_session() -> str:
    """Create a new authenticated session"""
    session_id = f"auth_{secrets.token_urlsafe(32)}"
    authenticated_sessions.add(session_id)
    return session_id

def is_session_valid(session_id: str) -> bool:
    """Check if a session ID is valid"""
    print(f"DEBUG AUTH: Checking session ID: {session_id}")
    print(f"DEBUG AUTH: Valid sessions: {authenticated_sessions}")
    result = session_id in authenticated_sessions
    print(f"DEBUG AUTH: Session valid: {result}")
    return result

def revoke_session(session_id: str):
    """Revoke a session"""
    authenticated_sessions.discard(session_id)

def authenticate_pin(pin: str) -> str:
    """Authenticate with PIN and return session ID if successful"""
    config_pin = get_config_pin()
    
    if pin == config_pin:
        return create_session()
    else:
        raise ValueError("Invalid PIN")