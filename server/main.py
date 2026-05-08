import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from database import init_db
from ws_manager import manager
from routes_auth import router as auth_router, verify_token
from routes_im import router as im_router
from routes_friends import router as friends_router
from routes_agent import router as agent_router
from routes_documents import router as doc_router
from routes_presentations import router as pres_router
from config import HOST, PORT


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="JarvisAgent Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(im_router, prefix="/api")
app.include_router(friends_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(doc_router, prefix="/api")
app.include_router(pres_router, prefix="/api")

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default=None)):
    user_id = None
    if token:
        try:
            user_id = verify_token(token)
        except Exception:
            pass

    await manager.connect(websocket, "global", user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "global", user_id=user_id)


@app.websocket("/ws/chat/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: str, token: str = Query(default=None)):
    user_id = None
    if token:
        try:
            user_id = verify_token(token)
        except Exception:
            pass

    await manager.connect(websocket, f"chat:{chat_id}", user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"chat:{chat_id}", user_id=user_id)


app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
