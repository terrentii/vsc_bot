from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

def get_auth_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔐 Войти в аккаунт")],
            [KeyboardButton(text="👤 Продолжить как аноним")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_main_menu_keyboard(is_logged_in: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="👤 Аккаунт"), KeyboardButton(text="📨 Отправить сообщение")],
        [KeyboardButton(text="📎 Отправить медиа"), KeyboardButton(text="👁 Слежение")],
        [KeyboardButton(text="📋 Список комнат"), KeyboardButton(text="🔍 Поиск комнаты")],
        [KeyboardButton(text="❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

def get_account_keyboard(is_logged_in: bool = False) -> ReplyKeyboardMarkup:
    if is_logged_in:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🚪 Выйти из аккаунта")],
                [KeyboardButton(text="◀️ Назад")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔐 Войти в аккаунт")],
                [KeyboardButton(text="◀️ Назад")]
            ],
            resize_keyboard=True
        )

def get_back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="◀️ Назад")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_back_to_start_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="◀️ Назад")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_stalk_keyboard(room_id: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"🛑 Остановить слежение {room_id}")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )

def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove(remove_keyboard=True)