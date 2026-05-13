from typing import Dict

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import Config
from bot.states import BotStates
from bot.keyboards import (
    get_auth_keyboard, get_main_menu_keyboard, get_stalk_keyboard,
    get_account_keyboard, get_back_keyboard, get_back_to_start_keyboard,
)
from bot.utils import parse_msg_command, parse_login_command, format_room_list, format_stalk_message
from bot.api_client import api

router = Router()

# Состояния пользователей хранятся в памяти — сбрасываются при перезапуске бота
user_data: Dict[int, dict] = {}


def get_user_info(tg_id: int) -> dict:
    if tg_id not in user_data:
        user_data[tg_id] = {"mode": None, "login": None, "stalking": set()}
    return user_data[tg_id]


def get_display_name(tg_id: int) -> str:
    info = get_user_info(tg_id)
    if info["mode"] == "login" and info["login"]:
        return f"{info['login']}_viaBot"
    return "Anon_viaBot"


def _is_room_id(text: str) -> bool:
    return text.isdigit() and len(text) == 10


def _main_menu(info: dict):
    return get_main_menu_keyboard(is_logged_in=(info["mode"] == "login"))


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    info = get_user_info(tg_id)
    info["mode"] = None
    info["login"] = None
    await state.set_state(BotStates.auth_choice)
    await message.answer(Config.WELCOME_TEXT, reply_markup=get_auth_keyboard(), parse_mode="HTML")


@router.message(F.text == "🔐 Войти в аккаунт")
async def btn_auth_login(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_login)
    await message.answer(
        "🔐 <b>Вход в аккаунт</b>\n\n"
        "Введите команду:\n"
        "<code>/login ваш_логин ваш_пароль</code>\n\n"
        "◀️ Назад — вернуться к выбору",
        reply_markup=get_back_to_start_keyboard(),
        parse_mode="HTML",
    )


@router.message(F.text == "👤 Продолжить как аноним")
async def btn_auth_anon(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    info = get_user_info(tg_id)
    info["mode"] = "anon"
    await state.set_state(BotStates.main_menu)
    await message.answer(
        "👤 <b>Режим анона активирован</b>\n\n"
        "Вы можете отправлять сообщения в любые открытые комнаты.\n"
        "Ваши сообщения будут подписаны как <i>Anon_viaBot</i>.",
        reply_markup=get_main_menu_keyboard(is_logged_in=False),
        parse_mode="HTML",
    )


@router.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext):
    login, password = parse_login_command(message.text)
    if not login or not password:
        await message.answer(
            "❌ Неверный формат.\nИспользуйте: <code>/login логин пароль</code>",
            parse_mode="HTML",
        )
        return
    success = await api.verify_login(login, password)
    if success:
        tg_id = message.from_user.id
        info = get_user_info(tg_id)
        info["mode"] = "login"
        info["login"] = login
        await state.set_state(BotStates.main_menu)
        await message.answer(
            f"✅ <b>Вход выполнен!</b>\n\n"
            f"Аккаунт: <code>{login}</code>\n"
            f"Сообщения будут от <i>{login}_viaBot</i>.",
            reply_markup=get_main_menu_keyboard(is_logged_in=True),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "❌ <b>Неверный логин или пароль.</b>\n"
            "Проверьте данные и попробуйте снова.",
            parse_mode="HTML",
        )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    info = get_user_info(message.from_user.id)
    await state.set_state(BotStates.main_menu)
    await message.answer("🏠 Главное меню", reply_markup=_main_menu(info), parse_mode="HTML")


async def _go_to_menu(message: Message, state: FSMContext):
    info = get_user_info(message.from_user.id)
    await state.set_state(BotStates.main_menu)
    await message.answer("🏠 Главное меню", reply_markup=_main_menu(info), parse_mode="HTML")


@router.message(F.text == "◀️ Назад", BotStates.waiting_login)
async def btn_back_to_start_from_login(message: Message, state: FSMContext):
    await cmd_start(message, state)


@router.message(F.text == "◀️ Назад", BotStates.waiting_msg_room)
@router.message(F.text == "◀️ Назад", BotStates.waiting_msg_text)
async def btn_back_from_msg(message: Message, state: FSMContext):
    await _go_to_menu(message, state)


@router.message(F.text == "◀️ Назад", BotStates.waiting_media_room)
@router.message(F.text == "◀️ Назад", BotStates.waiting_media)
async def btn_back_from_media(message: Message, state: FSMContext):
    await _go_to_menu(message, state)


@router.message(F.text == "◀️ Назад")
async def btn_back_general(message: Message, state: FSMContext):
    await _go_to_menu(message, state)


@router.message(F.text == "👤 Аккаунт")
async def btn_account(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    info = get_user_info(tg_id)

    if info["mode"] == "login":
        text = (
            f"👤 <b>Аккаунт</b>\n\n"
            f"Логин: <code>{info['login']}</code>\n"
            f"Режим: зарегистрированный\n"
            f"Отправка от: <i>{info['login']}_viaBot</i>"
        )
        keyboard = get_account_keyboard(is_logged_in=True)
    elif info["mode"] == "anon":
        text = (
            "👤 <b>Аноним</b>\n\n"
            "Режим: анонимный\n"
            "Отправка от: <i>Anon_viaBot</i>\n\n"
            "💡 Войдите в аккаунт для доступа к закрытым комнатам"
        )
        keyboard = get_account_keyboard(is_logged_in=False)
    else:
        text = "❓ Вы ещё не выбрали режим."
        keyboard = get_account_keyboard(is_logged_in=False)

    await state.set_state(BotStates.account_menu)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "🔐 Войти в аккаунт", BotStates.account_menu)
async def btn_account_login(message: Message, state: FSMContext):
    await btn_auth_login(message, state)


@router.message(F.text == "🚪 Выйти из аккаунта", BotStates.account_menu)
async def btn_account_logout(message: Message, state: FSMContext):
    await btn_logout(message, state)


@router.message(F.text == "◀️ Назад", BotStates.account_menu)
async def btn_account_back(message: Message, state: FSMContext):
    await _go_to_menu(message, state)


@router.message(F.text == "🚪 Выйти")
async def btn_logout(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    info = get_user_info(tg_id)
    if info["mode"] != "login":
        await message.answer("❌ Вы не зашли в аккаунт.", parse_mode="HTML")
        return
    old_login = info["login"]
    info["mode"] = "anon"
    info["login"] = None
    await state.set_state(BotStates.main_menu)
    await message.answer(
        f"🚪 <b>Вышли из аккаунта {old_login}</b>\n\nТеперь вы в режиме анона.",
        reply_markup=get_main_menu_keyboard(is_logged_in=False),
        parse_mode="HTML",
    )


@router.message(F.text == "📨 Отправить сообщение")
async def btn_send_msg_prompt(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_msg_room)
    await message.answer(
        "📨 <b>Отправка сообщения</b>\n\nВведите ID комнаты (10 цифр):\n\n◀️ Назад — отмена",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )


@router.message(BotStates.waiting_msg_room)
async def process_msg_room(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await btn_back_from_msg(message, state)
        return
    room_id = message.text.strip()
    if not _is_room_id(room_id):
        await message.answer("❌ ID должен быть 10 цифр. Попробуйте снова:", parse_mode="HTML")
        return
    await state.update_data(msg_room_id=room_id)
    await state.set_state(BotStates.waiting_msg_text)
    await message.answer(
        f"✏️ Введите сообщение для комнаты <code>{room_id}</code>:\n\n◀️ Назад — отмена",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )


@router.message(BotStates.waiting_msg_text)
async def process_msg_text(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await btn_back_from_msg(message, state)
        return
    data = await state.get_data()
    room_id = data.get("msg_room_id")
    text = message.text.strip()
    if not text:
        await message.answer("❌ Сообщение не может быть пустым.", parse_mode="HTML")
        return

    tg_id = message.from_user.id
    info = get_user_info(tg_id)
    if not info["mode"]:
        await message.answer("❌ Сначала выберите режим.", parse_mode="HTML")
        await state.set_state(BotStates.main_menu)
        return

    success, _ = await api.send_message(room_id, text, author=get_display_name(tg_id))
    if success:
        await message.answer(
            f"✅ Отправлено в <code>{room_id}</code>",
            reply_markup=_main_menu(info),
            parse_mode="HTML",
        )
    else:
        await message.answer("❌ Не удалось отправить. Возможно, нет доступа.", parse_mode="HTML")
    await state.set_state(BotStates.main_menu)


@router.message(F.text == "📎 Отправить медиа")
async def btn_send_media_prompt(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_media_room)
    await message.answer(
        "📎 <b>Отправка медиа</b>\n\nВведите ID комнаты (10 цифр):\n\n◀️ Назад — отмена",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )


@router.message(BotStates.waiting_media_room)
async def process_media_room(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await btn_back_from_media(message, state)
        return
    room_id = message.text.strip()
    if not _is_room_id(room_id):
        await message.answer("❌ ID должен быть 10 цифр. Попробуйте снова:", parse_mode="HTML")
        return
    await state.update_data(media_room_id=room_id)
    await state.set_state(BotStates.waiting_media)
    await message.answer(
        f"📤 Отправьте фото, видео, аудио или документ для комнаты <code>{room_id}</code>:\n"
        f"Макс. размер: {Config.MAX_MEDIA_SIZE_MB} МБ\n\n◀️ Назад — отмена",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )


@router.message(BotStates.waiting_media, F.photo | F.video | F.audio | F.document)
async def process_media(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    room_id = data.get("media_room_id")
    if not room_id:
        await message.answer("❌ Ошибка: комната не выбрана.", parse_mode="HTML")
        await state.set_state(BotStates.main_menu)
        return

    tg_id = message.from_user.id
    info = get_user_info(tg_id)

    # У фото нет file_name, поэтому задаём расширение вручную
    if message.photo:
        file_obj = message.photo[-1]
        filename = f"photo_{file_obj.file_id}.jpg"
        content_type = "image/jpeg"
    elif message.video:
        file_obj = message.video
        filename = getattr(file_obj, "file_name", None) or f"video_{file_obj.file_id}.mp4"
        content_type = getattr(file_obj, "mime_type", "video/mp4")
    elif message.audio:
        file_obj = message.audio
        filename = getattr(file_obj, "file_name", None) or f"audio_{file_obj.file_id}.mp3"
        content_type = getattr(file_obj, "mime_type", "audio/mpeg")
    elif message.document:
        file_obj = message.document
        filename = getattr(file_obj, "file_name", None) or f"file_{file_obj.file_id}.bin"
        content_type = getattr(file_obj, "mime_type", "application/octet-stream")
    else:
        await message.answer("❌ Неподдерживаемый тип файла.", parse_mode="HTML")
        return

    if hasattr(file_obj, "file_size") and file_obj.file_size > Config.MAX_MEDIA_SIZE_MB * 1024 * 1024:
        await message.answer(f"❌ Файл слишком большой (макс. {Config.MAX_MEDIA_SIZE_MB} МБ)", parse_mode="HTML")
        await state.set_state(BotStates.main_menu)
        return

    status_msg = await message.answer("⏳ Загрузка файла...", parse_mode="HTML")

    try:
        file = await bot.get_file(file_obj.file_id)
        file_bytes = (await bot.download_file(file.file_path)).read()

        success, server_filename = await api.send_media(room_id, file_bytes, filename, content_type)

        if success:
            msg_success, _ = await api.send_message(
                room_id, "📎 Медиа", author=get_display_name(tg_id), media=server_filename
            )
            if msg_success:
                await status_msg.edit_text(
                    f"✅ <b>Медиа отправлено!</b>\nКомната: <code>{room_id}</code>",
                    parse_mode="HTML",
                )
            else:
                await status_msg.edit_text(
                    "⚠️ Файл загружен, но не удалось отправить сообщение.", parse_mode="HTML"
                )
        else:
            await status_msg.edit_text("❌ Не удалось загрузить файл.", parse_mode="HTML")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}", parse_mode="HTML")

    await state.set_state(BotStates.main_menu)
    await message.answer("🏠 Главное меню", reply_markup=_main_menu(info), parse_mode="HTML")


@router.message(F.text == "👁 Слежение")
async def btn_stalk_prompt(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_stalk_room)
    await message.answer(
        "👁 <b>Слежение за комнатой</b>\n\nВведите ID комнаты (10 цифр):\nИли нажмите ◀️ Назад",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )


@router.message(BotStates.waiting_stalk_room)
async def process_stalk_room(message: Message, state: FSMContext, bot: Bot):
    room_id = message.text.strip()
    if not _is_room_id(room_id):
        await message.answer("❌ ID должен быть 10 цифр. Попробуйте снова:", parse_mode="HTML")
        return

    tg_id = message.from_user.id
    info = get_user_info(tg_id)

    if not info["mode"]:
        await message.answer("❌ Сначала выберите режим.", parse_mode="HTML")
        await state.set_state(BotStates.main_menu)
        return

    if room_id in info["stalking"]:
        await message.answer(f"⚠️ Вы уже следите за <code>{room_id}</code>.", parse_mode="HTML")
        return

    try:
        await api.connect_socketio()
    except Exception as e:
        await message.answer(f"❌ Не удалось подключиться: {e}", parse_mode="HTML")
        return

    async def on_ws_message(data):
        await bot.send_message(tg_id, format_stalk_message(room_id, data), parse_mode="HTML")

    api.on_message(room_id, on_ws_message)

    try:
        await api.join_room_ws(room_id)
    except Exception as e:
        await message.answer(f"❌ Не удалось подписаться: {e}", parse_mode="HTML")
        return

    info["stalking"].add(room_id)
    await state.set_state(BotStates.stalking)
    await state.update_data(stalk_room_id=room_id)
    await message.answer(
        f"👁 <b>Слежение за {room_id}</b>\n\n"
        f"Чтобы прекратить — напишите <code>/unstalk {room_id}</code>",
        reply_markup=get_stalk_keyboard(room_id),
        parse_mode="HTML",
    )


@router.message(F.text.startswith("🛑 Остановить слежение"))
async def btn_unstalk(message: Message, state: FSMContext):
    room_id = message.text.strip().replace("🛑 Остановить слежение ", "").strip()
    tg_id = message.from_user.id
    info = get_user_info(tg_id)

    if room_id in info["stalking"]:
        info["stalking"].discard(room_id)
        api.off_message(room_id)
        try:
            await api.leave_room_ws(room_id)
        except Exception:
            pass
        await message.answer(
            f"✅ Слежение за <code>{room_id}</code> остановлено.",
            reply_markup=_main_menu(info),
            parse_mode="HTML",
        )
    else:
        await message.answer("❌ Вы не следили за этой комнатой.", parse_mode="HTML")
    await state.set_state(BotStates.main_menu)


@router.message(F.text == "📋 Список комнат")
async def btn_roomslist(message: Message):
    rooms = await api.list_rooms()
    rooms_sorted = sorted(rooms, key=lambda x: x.get("created_at", ""), reverse=True)
    for part in format_room_list(rooms_sorted, Config.DEFAULT_ROOMS_LIMIT):
        await message.answer(part, parse_mode="HTML")


@router.message(F.text == "🔍 Поиск комнаты")
async def btn_search_prompt(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_search)
    await message.answer(
        "🔍 <b>Поиск комнаты</b>\n\nВведите название комнаты:",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )


@router.message(BotStates.waiting_search)
async def process_search(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await _go_to_menu(message, state)
        return
    query = message.text.strip()
    rooms = await api.list_rooms()
    found = [r for r in rooms if query.lower() in (r.get("name") or "").lower()]
    info = get_user_info(message.from_user.id)
    await state.set_state(BotStates.main_menu)
    kb = _main_menu(info)
    if not found:
        await message.answer("😕 Такой комнаты не найдено.", reply_markup=kb, parse_mode="HTML")
    else:
        parts = format_room_list(found, 50)
        for i, part in enumerate(parts):
            await message.answer(part, reply_markup=(kb if i == len(parts) - 1 else None), parse_mode="HTML")


@router.message(F.text == "❓ Помощь")
async def btn_help(message: Message):
    await message.answer(Config.HELP_TEXT, parse_mode="HTML")


# Текстовые команды — дублируют кнопки для удобства

@router.message(Command("msg"))
async def cmd_msg(message: Message):
    room_id, text = parse_msg_command(message.text)
    if not room_id or not text:
        await message.answer(
            "❌ Неверный формат.\nИспользуйте: <code>/msg 1234567890 ваше сообщение</code>",
            parse_mode="HTML",
        )
        return
    tg_id = message.from_user.id
    info = get_user_info(tg_id)
    if not info["mode"]:
        await message.answer("❌ Сначала выберите режим.", parse_mode="HTML")
        return
    success, _ = await api.send_message(room_id, text, author=get_display_name(tg_id))
    if success:
        await message.answer(f"✅ Отправлено в <code>{room_id}</code>", parse_mode="HTML")
    else:
        await message.answer("❌ Не удалось отправить.", parse_mode="HTML")


@router.message(Command("media"))
async def cmd_media(message: Message, state: FSMContext):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Укажите ID комнаты. <code>/media 1234567890</code>", parse_mode="HTML")
        return
    room_id = parts[1].strip()
    if not _is_room_id(room_id):
        await message.answer("❌ ID должен быть 10 цифр.", parse_mode="HTML")
        return
    info = get_user_info(message.from_user.id)
    if not info["mode"]:
        await message.answer("❌ Сначала выберите режим.", parse_mode="HTML")
        return
    await state.update_data(media_room_id=room_id)
    await state.set_state(BotStates.waiting_media)
    await message.answer(f"📎 Отправьте медиа для комнаты <code>{room_id}</code>:", parse_mode="HTML")


@router.message(Command("stalkroom"))
async def cmd_stalkroom(message: Message, state: FSMContext, bot: Bot):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Укажите ID комнаты. <code>/stalkroom 1234567890</code>", parse_mode="HTML")
        return
    room_id = parts[1].strip()
    if not _is_room_id(room_id):
        await message.answer("❌ ID должен быть 10 цифр.", parse_mode="HTML")
        return
    message.text = room_id
    await process_stalk_room(message, state, bot)


@router.message(Command("unstalk"))
async def cmd_unstalk(message: Message, state: FSMContext):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Укажите ID комнаты.", parse_mode="HTML")
        return
    room_id = parts[1].strip()
    message.text = f"🛑 Остановить слежение {room_id}"
    await btn_unstalk(message, state)


@router.message(Command("roomslist"))
async def cmd_roomslist(message: Message):
    await btn_roomslist(message)


@router.message(Command("searchroom"))
async def cmd_searchroom(message: Message, state: FSMContext):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await btn_search_prompt(message, state)
        return
    query = parts[1].strip().strip("\"'")
    rooms = await api.list_rooms()
    found = [r for r in rooms if query.lower() in (r.get("name") or "").lower()]
    info = get_user_info(message.from_user.id)
    kb = _main_menu(info)
    if not found:
        await message.answer("😕 Такой комнаты не найдено.", reply_markup=kb, parse_mode="HTML")
    else:
        parts = format_room_list(found, 50)
        for i, part in enumerate(parts):
            await message.answer(part, reply_markup=(kb if i == len(parts) - 1 else None), parse_mode="HTML")


@router.message(Command("account"))
async def cmd_account(message: Message, state: FSMContext):
    await btn_account(message, state)


@router.message(Command("logout"))
async def cmd_logout(message: Message, state: FSMContext):
    await btn_logout(message, state)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await btn_help(message)


@router.message()
async def handle_text(message: Message, state: FSMContext):
    # Если пользователь в середине какого-то флоу — молча игнорируем неожиданный текст
    active_states = {
        BotStates.waiting_login.state,
        BotStates.waiting_msg_room.state,
        BotStates.waiting_msg_text.state,
        BotStates.waiting_media_room.state,
        BotStates.waiting_media.state,
        BotStates.waiting_stalk_room.state,
        BotStates.waiting_search.state,
    }
    if await state.get_state() in active_states:
        return
    await message.answer(
        "❓ Используйте кнопки меню или команды.\nНажмите ❓ Помощь для списка команд.",
        parse_mode="HTML",
    )
