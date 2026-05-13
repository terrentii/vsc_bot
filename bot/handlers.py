import asyncio
from typing import Dict

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import Config
from bot.states import BotStates
from bot.keyboards import get_start_keyboard, get_main_menu_keyboard, get_login_prompt_keyboard
from bot.api_client import api
from bot.utils import parse_msg_command, parse_login_command, format_room_list, format_stalk_message

router = Router()

# Хранилище: {telegram_id: {"mode": "anon"|"login", "login": str|None, "stalking": set()}}
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


async def send_account_info(target: Message | CallbackQuery):
    if isinstance(target, CallbackQuery):
        tg_id = target.from_user.id
        msg = target.message
    else:
        tg_id = target.from_user.id
        msg = target
    
    info = get_user_info(tg_id)
    
    if info["mode"] == "login":
        text = (
            f"👤 <b>Аккаунт</b>\n\n"
            f"Логин: <code>{info['login']}</code>\n"
            f"Режим: зарегистрированный\n"
            f"Отправка от: <i>{info['login']}_viaBot</i>"
        )
    elif info["mode"] == "anon":
        text = (
            f"👤 <b>Аноним</b>\n\n"
            f"Режим: анонимный\n"
            f"Отправка от: <i>Anon_viaBot</i>\n\n"
            f"💡 Для входа в аккаунт используйте /login"
        )
    else:
        text = "❓ Вы ещё не выбрали режим. Нажмите /start"
    
    if isinstance(target, CallbackQuery):
        await msg.edit_text(text, parse_mode="HTML")
    else:
        await msg.answer(text, parse_mode="HTML")


# ==================== /start ====================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(BotStates.main_menu)
    await message.answer(
        Config.WELCOME_TEXT,
        reply_markup=get_start_keyboard(),
        parse_mode="HTML"
    )


# ==================== Callback: Войти / Анон ====================

@router.callback_query(F.data == "login")
async def cb_login(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_login)
    await callback.message.edit_text(
        "🔐 <b>Вход в аккаунт</b>\n\n"
        "Введите команду:\n"
        "<code>/login ваш_логин ваш_пароль</code>",
        reply_markup=get_login_prompt_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "anon")
async def cb_anon(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    info = get_user_info(tg_id)
    info["mode"] = "anon"

    await state.set_state(BotStates.main_menu)
    await callback.message.edit_text(
        "👤 <b>Режим анона активирован</b>\n\n"
        "Вы можете отправлять сообщения в любые открытые комнаты.\n"
        "Ваши сообщения будут подписаны как <i>Anon_viaBot</i>.",
        reply_markup=get_main_menu_keyboard(is_logged_in=False),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== /login ====================

@router.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext):
    login, password = parse_login_command(message.text)
    if not login or not password:
        await message.answer(
            "❌ Неверный формат.\n"
            "Используйте: <code>/login логин пароль</code>",
            parse_mode="HTML"
        )
        return

    # Проверяем логин/пароль на сервере
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
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Неверный логин или пароль.</b>\n"
            "Проверьте данные и попробуйте снова.",
            parse_mode="HTML"
        )


# ==================== /account ====================

@router.message(Command("account"))
async def cmd_account(message: Message):
    await send_account_info(message)


# ==================== /msg ====================

@router.message(Command("msg"))
async def cmd_msg(message: Message):
    room_id, text = parse_msg_command(message.text)
    if not room_id or not text:
        await message.answer(
            "❌ Неверный формат.\n"
            "Используйте: <code>/msg 1234567890 ваше сообщение</code>\n"
            'Или: <code>/msg 1234567890 \"сообщение в кавычках\"</code>',
            parse_mode="HTML"
        )
        return

    tg_id = message.from_user.id
    info = get_user_info(tg_id)

    if not info["mode"]:
        await message.answer("❌ Сначала выберите режим: /start", parse_mode="HTML")
        return

    display_name = get_display_name(tg_id)
    
    success, result = await api.send_message(room_id, text, author=display_name)

    if success:
        await message.answer(
            f"✅ Сообщение отправлено в комнату <code>{room_id}</code>",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ Не удалось отправить сообщение.\n"
            f"Возможно, комната не существует или у вас нет доступа.",
            parse_mode="HTML"
        )


# ==================== /media ====================

@router.message(Command("media"))
async def cmd_media(message: Message, state: FSMContext):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите ID комнаты.\n"
            "Используйте: <code>/media 1234567890</code>",
            parse_mode="HTML"
        )
        return

    room_id = parts[1].strip()
    if not room_id.isdigit() or len(room_id) != 10:
        await message.answer("❌ ID комнаты должен быть 10 цифр.", parse_mode="HTML")
        return

    tg_id = message.from_user.id
    info = get_user_info(tg_id)

    if not info["mode"]:
        await message.answer("❌ Сначала выберите режим: /start", parse_mode="HTML")
        return

    await state.update_data(media_room_id=room_id)
    await state.set_state(BotStates.waiting_media)

    await message.answer(
        f"📎 <b>Отправка медиа в комнату {room_id}</b>\n\n"
        f"Отправьте мне фото, видео, аудио или документ.\n"
        f"Максимальный размер: {Config.MAX_MEDIA_SIZE_MB} МБ.",
        parse_mode="HTML"
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

    file_obj = None
    if message.photo:
        file_obj = message.photo[-1]
    elif message.video:
        file_obj = message.video
    elif message.audio:
        file_obj = message.audio
    elif message.document:
        file_obj = message.document

    if not file_obj:
        await message.answer("❌ Неподдерживаемый тип файла.", parse_mode="HTML")
        return

    status_msg = await message.answer("⏳ Загрузка файла...", parse_mode="HTML")

    try:
        file = await bot.get_file(file_obj.file_id)
        file_data = await bot.download_file(file.file_path)
        file_bytes = file_data.read()

        filename = getattr(file_obj, "file_name", f"file_{file_obj.file_id}")
        content_type = getattr(file_obj, "mime_type", "application/octet-stream")

        success, server_filename = await api.send_media(
            room_id, file_bytes, filename, content_type
        )

        if success:
            display_name = get_display_name(tg_id)
            # Не передаем пустой text — сервер требует текст
            # Отправляем медиа с минимальным текстом или через другое поле
            msg_success, msg_result = await api.send_message(
                room_id, "📎 Медиа", author=display_name, media=server_filename
            )

            if msg_success:
                await status_msg.edit_text(
                    f"✅ <b>Медиа отправлено!</b>\n"
                    f"Комната: <code>{room_id}</code>",
                    parse_mode="HTML"
                )
            else:
                await status_msg.edit_text(
                    "⚠️ Файл загружен, но не удалось отправить сообщение.",
                    parse_mode="HTML"
                )
        else:
            await status_msg.edit_text(
                "❌ Не удалось загрузить файл.",
                parse_mode="HTML"
            )

    except Exception as e:
        await status_msg.edit_text(
            f"❌ Ошибка: {str(e)}",
            parse_mode="HTML"
        )

    await state.set_state(BotStates.main_menu)


# ==================== /roomslist ====================

@router.message(Command("roomslist"))
async def cmd_roomslist(message: Message):
    parts = message.text.split(maxsplit=1)
    
    if len(parts) > 1:
        try:
            limit = max(1, min(50, int(parts[1])))
        except ValueError:
            limit = Config.DEFAULT_ROOMS_LIMIT
    else:
        limit = Config.DEFAULT_ROOMS_LIMIT

    rooms = await api.list_rooms()
    rooms_sorted = sorted(rooms, key=lambda x: x.get("created_at", ""), reverse=True)

    text = format_room_list(rooms_sorted, limit)
    await message.answer(text, parse_mode="HTML")


# ==================== /searchroom ====================

@router.message(Command("searchroom"))
async def cmd_searchroom(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите название комнаты.\n"
            'Используйте: <code>/searchroom \"Название\"</code>',
            parse_mode="HTML"
        )
        return

    query = parts[1].strip()
    if query.startswith('"') and query.endswith('"'):
        query = query[1:-1]
    elif query.startswith("'") and query.endswith("'"):
        query = query[1:-1]

    rooms = await api.list_rooms()
    found = [r for r in rooms if query.lower() in (r.get("name") or "").lower()]

    if found:
        text = format_room_list(found, 50)
    else:
        text = "😕 Такой комнаты не существует."

    await message.answer(text, parse_mode="HTML")


# ==================== /stalkroom (WebSocket) ====================

@router.message(Command("stalkroom"))
async def cmd_stalkroom(message: Message, state: FSMContext, bot: Bot):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите ID комнаты.\n"
            "Используйте: <code>/stalkroom 1234567890</code>",
            parse_mode="HTML"
        )
        return

    room_id = parts[1].strip()
    if not room_id.isdigit() or len(room_id) != 10:
        await message.answer("❌ ID комнаты должен быть 10 цифр.", parse_mode="HTML")
        return

    tg_id = message.from_user.id
    info = get_user_info(tg_id)

    if not info["mode"]:
        await message.answer("❌ Сначала выберите режим: /start", parse_mode="HTML")
        return

    if room_id in info["stalking"]:
        await message.answer(
            f"⚠️ Вы уже следите за комнатой <code>{room_id}</code>.",
            parse_mode="HTML"
        )
        return

    # Подключаемся к WebSocket
    try:
        await api.connect_socketio()
    except Exception as e:
        await message.answer(
            f"❌ Не удалось подключиться к WebSocket: {e}",
            parse_mode="HTML"
        )
        return

    # Регистрируем callback
    async def on_ws_message(data):
        formatted = format_stalk_message(room_id, data)
        await bot.send_message(tg_id, formatted, parse_mode="HTML")

    api.on_message(room_id, on_ws_message)
    
    try:
        await api.join_room_ws(room_id)
    except Exception as e:
        await message.answer(
            f"❌ Не удалось подписаться: {e}",
            parse_mode="HTML"
        )
        return

    info["stalking"].add(room_id)

    await message.answer(
        f"👁 <b>Слежение за комнатой {room_id}</b>\n\n"
        f"Формат: <code>room_id - sender: message</code>\n"
        f"Для остановки: <code>/unstalk {room_id}</code>",
        parse_mode="HTML"
    )


@router.message(Command("unstalk"))
async def cmd_unstalk(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите ID комнаты: <code>/unstalk 1234567890</code>",
            parse_mode="HTML"
        )
        return

    room_id = parts[1].strip()
    tg_id = message.from_user.id
    info = get_user_info(tg_id)

    if room_id in info["stalking"]:
        info["stalking"].discard(room_id)
        api.off_message(room_id)
        try:
            await api.leave_room_ws(room_id)
        except:
            pass
        await message.answer(
            f"✅ Слежение за комнатой <code>{room_id}</code> остановлено.",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Вы не следили за этой комнатой.", parse_mode="HTML")


# ==================== /help ====================

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(Config.HELP_TEXT, parse_mode="HTML")


# ==================== /logout ====================

@router.message(Command("logout"))
async def cmd_logout(message: Message, state: FSMContext):
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
        f"🚪 <b>Вышли из аккаунта {old_login}</b>\n\n"
        f"Теперь вы в режиме анона.\n"
        f"Сообщения будут от <i>Anon_viaBot</i>.",
        reply_markup=get_main_menu_keyboard(is_logged_in=False),
        parse_mode="HTML"
    )


# ==================== Callback: меню ====================

@router.callback_query(F.data == "account")
async def cb_account(callback: CallbackQuery):
    await send_account_info(callback)
    await callback.answer()


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.message.edit_text(Config.HELP_TEXT, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "logout")
async def cb_logout(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    info = get_user_info(tg_id)

    if info["mode"] != "login":
        await callback.answer("❌ Вы не зашли в аккаунт.", show_alert=True)
        return

    old_login = info["login"]
    info["mode"] = "anon"
    info["login"] = None

    await state.set_state(BotStates.main_menu)
    await callback.message.edit_text(
        f"🚪 <b>Вышли из аккаунта {old_login}</b>\n\n"
        f"Теперь вы в режиме анона.\n"
        f"Сообщения будут от <i>Anon_viaBot</i>.",
        reply_markup=get_main_menu_keyboard(is_logged_in=False),
        parse_mode="HTML"
    )
    await callback.answer("Выполнен выход из аккаунта")


@router.callback_query(F.data == "back_to_menu")
async def cb_back(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    info = get_user_info(tg_id)
    is_logged = info["mode"] == "login"

    await state.set_state(BotStates.main_menu)
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>",
        reply_markup=get_main_menu_keyboard(is_logged_in=is_logged),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== Обработка обычных сообщений ====================

@router.message()
async def handle_text(message: Message):
    await message.answer(
        "❓ Я не понимаю это сообщение.\n\n"
        "Используйте команды:\n"
        "<code>/msg 1234567890 ваше сообщение</code>\n"
        "или нажмите /help для списка команд.",
        parse_mode="HTML"
    )