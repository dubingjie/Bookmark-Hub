from fastapi import FastAPI

from .routers import bookmarks, tags

app = FastAPI(title="Bookmark-Hub", version="1.0")
app.include_router(bookmarks.router)
app.include_router(tags.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
