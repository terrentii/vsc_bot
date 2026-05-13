import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_KEY = os.getenv("API_KEY", "")
    BASE_URL = "https://soufos.ru"
    API_URL = f"{BASE_URL}/api"
    
    POLL_INTERVAL = 3
    MAX_MESSAGE_LENGTH = 4000
    MAX_MEDIA_SIZE_MB = 20
    DEFAULT_ROOMS_LIMIT = 50

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
        "<code>msg room_id сообщение</code> — отправить сообщение\n"
        "<code>media room_id</code> — отправить медиа/файл\n"
        "<code>roomslist число</code> — список комнат (по умолч. 50)\n"
        "<code>searchroom Название</code> — найти комнату\n"
        "<code>stalkroom room_id</code> — следить за комнатой (WebSocket)\n"
        "<code>unstalk room_id</code> — остановить слежение\n"
        "<code>help</code> — справка\n"
        "<code>logout</code> — выйти из аккаунта\n\n"
        "💡 <i>Сообщения отправляются с припиской _viaBot</i>"
    )