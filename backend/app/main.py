from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import bookmarks, tags


app = FastAPI(title="Bookmark-Hub", version="1.0")
app.include_router(bookmarks.router)
app.include_router(tags.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# 临时由 uvicorn 托管前端静态文件（第 7 步会换成 Nginx 来干这件事）
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")