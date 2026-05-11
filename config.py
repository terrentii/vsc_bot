import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    BASE_URL = "https://soufos.ru"
    API_URL = f"{BASE_URL}/api"
    
    POLL_INTERVAL = 3
    
    MAX_MESSAGE_LENGTH = 4000
    MAX_MEDIA_SIZE_MB = 20
    
    WELCOME_TEXT = (
        "👋 Добро пожаловать в <b>МЫС Web</b>!\n\n"
        "Это анонимный веб-мессенджер без слежки.\n"
        "Вы можете войти в свой аккаунт или продолжить как аноним."
    )
    
    HELP_TEXT = (
        "📋 <b>Доступные команды:</b>\n\n"
        "<code>start</code> — главное меню\n"
        "<code>login логин пароль</code> — войти в аккаунт\n"
        "<code>account</code> — информация об аккаунте/аноне\n"
        "<code>msg room_id сообщение</code> — отправить сообщение в комнату\n"
        "<code>media room_id</code> — отправить медиа/файл в комнату\n"
        "<code>roomslist число</code> — список популярных комнат\n"
        "<code>searchroom Название</code> — найти комнату по имени\n"
        "<code>stalkroom room_id</code> — следить за новыми сообщениями\n"
        "<code>unstalk room_id</code> — остановить слежение\n"
        "<code>help</code> — эта справка\n"
        "<code>logout</code> — выйти из аккаунта\n\n"
        "💡 <i>Сообщения отправляются с припиской _viaBot</i>\n\n"
        "ℹ️ Для использования команд пишите их с префиксом /, например:\n"
        "<code>/msg 1234567890 привет</code>"
    )