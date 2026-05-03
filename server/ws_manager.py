from fastapi import WebSocket
from typing import Dict, Set
import json


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.global_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, channel: str = "global"):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        self.global_connections.add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str = "global"):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        self.global_connections.discard(websocket)

    async def broadcast(self, message: dict, channel: str = "global"):
        data = json.dumps(message, ensure_ascii=False)
        targets = self.active_connections.get(channel, set()) | self.global_connections
        disconnected = set()
        for connection in targets:
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.add(connection)
        for conn in disconnected:
            self.global_connections.discard(conn)
            for ch in self.active_connections.values():
                ch.discard(conn)

    async def send_to_channel(self, message: dict, channel: str):
        data = json.dumps(message, ensure_ascii=False)
        connections = self.active_connections.get(channel, set())
        disconnected = set()
        for connection in connections:
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.add(connection)
        for conn in disconnected:
            connections.discard(conn)

    async def send_personal(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception:
            pass


manager = ConnectionManager()
