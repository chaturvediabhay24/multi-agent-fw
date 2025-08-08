from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from ui.router import router as ui_router, mount_static_files
from api.router import router as api_router

app = FastAPI(
    title="Multi-Agent Framework",
    description="A comprehensive multi-agent system with web UI and REST API",
    version="1.0.0"
)

# Mount static files
mount_static_files(app)

# Include routers
app.include_router(ui_router, tags=["UI"])
app.include_router(api_router, tags=["API"])

# All routes are now handled by modular routers:
# - UI routes: ui.router
# - API routes: api.router

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)