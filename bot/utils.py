import re
from typing import Optional, Tuple


def parse_msg_command(text: str) -> Tuple[Optional[str], Optional[str]]:
    text = text[4:].strip()
    match = re.match(r'^(\d{10})\s+(.+)$', text, re.DOTALL)
    if match:
        room_id = match.group(1)
        message = match.group(2).strip()
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        elif message.startswith("'") and message.endswith("'"):
            message = message[1:-1]
        return room_id, message
    return None, None


def parse_login_command(text: str) -> Tuple[Optional[str], Optional[str]]:
    parts = text.split(maxsplit=2)
    if len(parts) >= 3:
        return parts[1], parts[2]
    return None, None


def format_room_list(rooms: list, limit: int = 50) -> str:
    if not rooms:
        return "😕 Комнат пока нет."

    lines = [f"📋 <b>Список комнат ({min(len(rooms), limit)}):</b>\n"]
    for i, room in enumerate(rooms[:limit], 1):
        name = room.get("name") or room.get("room_id")
        room_id = room.get("room_id")
        lines.append(f'{i}. "{name}" — <code>{room_id}</code>')

    return "\n".join(lines)


def format_stalk_message(room_id: str, msg: dict) -> str:
    """Формат: <room_id> - <sender>: <message>"""
    author = msg.get("author", "Unknown")
    text = msg.get("text", "")
    return f"<code>{room_id}</code> - <b>{author}</b>: {text}"