from fastapi import WebSocket
from typing import Dict, Set
import json


class ConnectionManager:
    """Manages WebSocket connections with per-user multi-device support."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.global_connections: Set[WebSocket] = set()
        self.user_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "global", user_id: str = None):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        self.global_connections.add(websocket)

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str = "global", user_id: str = None):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        self.global_connections.discard(websocket)

        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        # Also clean from all user connections if user_id not provided
        if not user_id:
            for uid in list(self.user_connections.keys()):
                self.user_connections[uid].discard(websocket)
                if not self.user_connections[uid]:
                    del self.user_connections[uid]

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

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send message to all connections of a specific user (multi-device)."""
        connections = self.user_connections.get(user_id, set())
        if not connections:
            return
        data = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        for conn in connections:
            try:
                await conn.send_text(data)
            except Exception:
                disconnected.add(conn)
        for conn in disconnected:
            connections.discard(conn)

    async def broadcast_to_chat_members(self, chat_id: str, message: dict, member_ids: list):
        """Send message to all devices of all members of a chat."""
        data = json.dumps(message, ensure_ascii=False)
        sent_to = set()
        for uid in member_ids:
            connections = self.user_connections.get(uid, set())
            for conn in connections:
                if conn not in sent_to:
                    try:
                        await conn.send_text(data)
                        sent_to.add(conn)
                    except Exception:
                        pass

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

    def get_online_users(self) -> list:
        return list(self.user_connections.keys())


manager = ConnectionManager()
