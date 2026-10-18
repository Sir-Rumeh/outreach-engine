import time
import threading
import webbrowser
from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import router as api_router

app = FastAPI(title=settings.PROJECT_NAME)

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
