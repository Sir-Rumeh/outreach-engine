import os
import time
from fastapi.staticfiles import StaticFiles
from app.core.favicon import ensure_favicon_assets
import threading
import webbrowser
from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import router as api_router

app = FastAPI(title=settings.PROJECT_NAME)

# Ensure static directory and favicon assets exist
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
ensure_favicon_assets(static_dir)

try:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
except Exception:
    pass

# Include application API routes
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    import os

    def open_browser():
        time.sleep(2.0)
        webbrowser.open("http://127.0.0.1:8000")

    threading.Thread(target=open_browser, daemon=True).start()

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")

    uvicorn.run("main:app", host=host, port=port, reload=True)
