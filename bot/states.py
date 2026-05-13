from aiogram.fsm.state import State, StatesGroup

class BotStates(StatesGroup):
    auth_choice = State()           # новое — выбор Войти/Аноним
    main_menu = State()
    waiting_login = State()
    waiting_msg_room = State()
    waiting_msg_text = State()
    waiting_media_room = State()
    waiting_media = State()
    waiting_stalk_room = State()
    stalking = State()
    waiting_search = State()