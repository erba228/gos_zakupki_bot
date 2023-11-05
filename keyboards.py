from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Клавиатура для команд /start и /help
start_kb = ReplyKeyboardMarkup(resize_keyboard=True)
start_kb.add(KeyboardButton('/login'))
start_kb.add(KeyboardButton('/help'))

# Клавиатура для команд /change_name и /change_password
change_profile_info_kb = ReplyKeyboardMarkup(resize_keyboard=True)
change_profile_info_kb.add(KeyboardButton('/tenders'))
change_profile_info_kb.add(KeyboardButton('/news'))
change_profile_info_kb.add(KeyboardButton('/compliants'))
change_profile_info_kb.add(KeyboardButton('/change_name'))
change_profile_info_kb.add(KeyboardButton('/change_password'))

