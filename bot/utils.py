def parse_msg_command(text: str) -> tuple[str | None, str | None]:
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        return None, None
    room_id = parts[1].strip()
    msg_text = parts[2].strip()
    if not room_id.isdigit() or len(room_id) != 10:
        return None, None
    return room_id, msg_text

def parse_login_command(text: str) -> tuple[str | None, str | None]:
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        return None, None
    return parts[1].strip(), parts[2].strip()

def format_room_list(rooms: list, limit: int = 50) -> str:
    if not rooms:
        return "😕 Нет доступных комнат."
    lines = ["📋 <b>Список комнат:</b>\n"]
    for i, room in enumerate(rooms[:limit], 1):
        name = room.get("name") or room.get("room_id", "???")
        room_id = room.get("room_id", "???")
        created = room.get("created_at", "")[:10]
        lines.append(f"{i}. <b>{name}</b>\n   ID: <code>{room_id}</code> | {created}")
    return "\n".join(lines)

def format_stalk_message(room_id: str, data: dict) -> str:
    author = data.get("author", "???")
    text = data.get("text", "")
    media = data.get("media", "")
    msg = f"👁 <code>{room_id}</code> — <b>{author}</b>:"
    if text:
        msg += f"\n{text}"
    if media:
        msg += f"\n📎 <i>{media}</i>"
    return msg