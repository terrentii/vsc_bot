from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔐 Войти в аккаунт", callback_data="login"),
            InlineKeyboardButton(text="👤 Продолжить как anon", callback_data="anon"),
        ]
    ])


def get_main_menu_keyboard(is_logged_in: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="👤 Мой аккаунт", callback_data="account"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
        ]
    ]
    if is_logged_in:
        buttons.append([
            InlineKeyboardButton(text="🚪 Выйти из аккаунта", callback_data="logout")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_login_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ])