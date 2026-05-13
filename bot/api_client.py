import re
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

    async def connect_socketio(self):
        if self.sio and self.sio.connected:
            return
        if self.sio:
            try:
                await self.sio.disconnect()
            except Exception:
                pass

        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=10,
            reconnection_delay=2,
            reconnection_delay_max=10,
        )

        @self.sio.on("connect")
        async def on_connect():
            # При переподключении нужно заново вступить во все комнаты
            print("[WS] Подключено, переподписываемся на комнаты:", list(self._callbacks.keys()))
            for room_id in list(self._callbacks.keys()):
                await self.sio.emit("join", {"room_id": room_id})

        @self.sio.on("disconnect")
        async def on_disconnect():
            print("[WS] Отключено")

        @self.sio.on("new_message")
        async def on_new_message(data):
            room_id = str(data.get("room_id", ""))
            callback = self._callbacks.get(room_id)
            if callback:
                try:
                    await callback(data)
                except Exception as e:
                    print(f"[WS] Ошибка колбека для комнаты {room_id}: {e}")

        await self.sio.connect(
            self.base_url,
            headers=self._get_headers(),
            transports=["websocket", "polling"],
            wait_timeout=10,
        )

    async def disconnect_socketio(self):
        if self.sio:
            try:
                await self.sio.disconnect()
            except Exception:
                pass
        self.sio = None

    async def join_room_ws(self, room_id: str):
        if self.sio and self.sio.connected:
            await self.sio.emit("join", {"room_id": room_id})
            print(f"[WS] Вошли в комнату {room_id}")
        else:
            print(f"[WS] Не удалось войти в {room_id}: нет соединения")

    async def leave_room_ws(self, room_id: str):
        if self.sio and self.sio.connected:
            await self.sio.emit("leave", {"room_id": room_id})

    def on_message(self, room_id: str, callback: Callable):
        self._callbacks[room_id] = callback

    def off_message(self, room_id: str):
        self._callbacks.pop(room_id, None)

    async def verify_login(self, login: str, password: str) -> bool:
        login_url = f"{self.base_url}/login"
        # Flask проверяет Referer/Origin — без них возвращает 400
        post_headers = {"Referer": login_url, "Origin": self.base_url}
        async with aiohttp.ClientSession() as session:
            async with session.get(login_url) as resp:
                text = await resp.text()
                match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', text)
                csrf_token = match.group(1) if match else ""

            async with session.post(
                login_url,
                data={"csrf_token": csrf_token, "login": login, "password": password},
                headers=post_headers,
                allow_redirects=False,
            ) as resp:
                location = resp.headers.get("Location", "")
                return resp.status == 302 and "/login" not in location

    async def list_rooms(self) -> List[Dict[str, Any]]:
        async with aiohttp.ClientSession(headers=self._get_headers()) as session:
            url = f"{self.api_url}/rooms/tg" if self.api_key else f"{self.api_url}/rooms"
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []

    async def get_room_messages(self, room_id: str, after: int = 0) -> List[Dict[str, Any]]:
        async with aiohttp.ClientSession(headers=self._get_headers()) as session:
            async with session.get(
                f"{self.api_url}/room/{room_id}/messages",
                params={"after": after},
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []

    async def send_message(
        self,
        room_id: str,
        text: str,
        author: Optional[str] = None,
        media: Optional[str] = None,
    ) -> tuple[bool, Optional[Dict]]:
        async with aiohttp.ClientSession(headers=self._get_headers()) as session:
            body = {"text": text}
            if media:
                body["media"] = media
            headers = dict(self._get_headers())
            if author:
                headers["X-Bot-Author"] = author
            async with session.post(
                f"{self.api_url}/room/{room_id}/message",
                json=body,
                headers=headers,
            ) as resp:
                if resp.status == 201:
                    return True, await resp.json()
                try:
                    print(f"[API] Ошибка {resp.status}: {await resp.text()}")
                except Exception:
                    pass
                return False, None

    async def send_media(
        self,
        room_id: str,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> tuple[bool, Optional[str]]:
        async with aiohttp.ClientSession(headers=self._get_headers()) as session:
            form = aiohttp.FormData()
            form.add_field("file", file_data, filename=filename, content_type=content_type)
            async with session.post(
                f"{self.api_url}/room/{room_id}/upload",
                data=form,
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return True, result.get("filename")
                try:
                    print(f"[API] Ошибка загрузки {resp.status}: {await resp.text()}")
                except Exception:
                    pass
                return False, None


api = VSCAPIClient()
