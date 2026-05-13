import aiohttp
import socketio
from typing import Optional, Dict, Any, List, Callable
from config import Config

class VSCAPIClient:
    def __init__(self):
        self.base_url = Config.BASE_URL
        self.api_url = Config.API_URL
        self.api_key = Config.API_KEY
        self.sio: Optional[socketio.AsyncClient] = None
        self._callbacks: Dict[str, Callable] = {}

    def _get_headers(self) -> Dict[str, str]:
        headers = {}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    # ==================== SOCKET.IO ====================

    async def connect_socketio(self):
        if self.sio and self.sio.connected:
            return
        if self.sio:
            try:
                await self.sio.disconnect()
            except:
                pass
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=1,
            reconnection_delay_max=5,
        )

        @self.sio.on('connect')
        async def on_connect():
            print("[WS] Connected")

        @self.sio.on('disconnect')
        async def on_disconnect():
            print("[WS] Disconnected")

        @self.sio.on('new_message')
        async def on_new_message(data):
            room_id = data.get('room_id', '')
            callback = self._callbacks.get(room_id)
            if callback:
                await callback(data)

        @self.sio.on('edit_message')
        async def on_edit_message(data):
            pass

        @self.sio.on('delete_message')
        async def on_delete_message(data):
            pass

        await self.sio.connect(
            self.base_url,
            headers=self._get_headers(),
            transports=['websocket', 'polling']
        )

    async def disconnect_socketio(self):
        if self.sio and self.sio.connected:
            await self.sio.disconnect()
        self.sio = None

    async def join_room_ws(self, room_id: str):
        if self.sio and self.sio.connected:
            await self.sio.emit('join', {'room_id': room_id})
            print(f"[WS] Joined room {room_id}")

    async def leave_room_ws(self, room_id: str):
        if self.sio and self.sio.connected:
            await self.sio.emit('leave', {'room_id': room_id})

    def on_message(self, room_id: str, callback: Callable):
        self._callbacks[room_id] = callback

    def off_message(self, room_id: str):
        self._callbacks.pop(room_id, None)

    # ==================== HTTP API ====================

    async def verify_login(self, login: str, password: str) -> bool:
        import re
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/login") as resp:
                text = await resp.text()
                # Улучшенный regex — ловит разные кавычки и порядок атрибутов
                csrf_match = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', text)
                if not csrf_match:
                    csrf_match = re.search(r'value=["\']([^"\']+)["\'][^>]*name=["\']csrf_token["\']', text)
                csrf_token = csrf_match.group(1) if csrf_match else ""
            
            data = {
                "csrf_token": csrf_token,
                "login": login,
                "password": password,
            }
            
            async with session.post(
                f"{self.base_url}/login",
                data=data,
                allow_redirects=False
            ) as resp:
                location = resp.headers.get('Location', '')
                # Успех: редирект на / или /room/... (не на /login)
                return resp.status == 302 and '/login' not in location

    async def list_rooms(self) -> List[Dict[str, Any]]:
        async with aiohttp.ClientSession(headers=self._get_headers()) as session:
            async with session.get(f"{self.api_url}/rooms") as resp:
                if resp.status == 200:
                    return await resp.json()
                return []

    async def get_room_messages(self, room_id: str, after: int = 0) -> List[Dict[str, Any]]:
        async with aiohttp.ClientSession(headers=self._get_headers()) as session:
            async with session.get(
                f"{self.api_url}/room/{room_id}/messages",
                params={"after": after}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []

    async def send_message(
        self,
        room_id: str,
        text: str,
        author: Optional[str] = None,
        media: Optional[str] = None
    ) -> tuple[bool, Optional[Dict]]:
        async with aiohttp.ClientSession(headers=self._get_headers()) as session:
            data = {"text": text}
            if media:
                data["media"] = media
            headers = dict(self._get_headers())
            if author:
                headers["X-Bot-Author"] = author
            async with session.post(
                f"{self.api_url}/room/{room_id}/message",
                json=data,
                headers=headers
            ) as resp:
                if resp.status == 201:
                    return True, await resp.json()
                try:
                    err_text = await resp.text()
                    print(f"[API Error {resp.status}]: {err_text}")
                except:
                    pass
                return False, None

    async def send_media(
        self,
        room_id: str,
        file_data: bytes,
        filename: str,
        content_type: str
    ) -> tuple[bool, Optional[str]]:
        async with aiohttp.ClientSession(headers=self._get_headers()) as session:
            data = aiohttp.FormData()
            data.add_field(
                "file",
                file_data,
                filename=filename,
                content_type=content_type
            )
            async with session.post(
                f"{self.base_url}/room/{room_id}/upload",
                data=data
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return True, result.get("filename")
                return False, None

api = VSCAPIClient()