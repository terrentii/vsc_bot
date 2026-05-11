from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    main_menu = State()
    waiting_login = State()
    waiting_media = State()