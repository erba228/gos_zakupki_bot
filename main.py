import bcrypt as bcrypt
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
from settings import conn, curr
import os
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from keyboards import start_kb, change_profile_info_kb

HELP_COMMAND = """
/login - авторизоваться
/tenders - свежие тендеры
/compliants - жалобы
/change_name = изменение имени
/change_password = изменение пароля
/help - список команд
/start - начать работу с ботом
"""

load_dotenv()

bot = Bot(
    token=os.environ.get("TOKEN_API")
)

storage = MemoryStorage()

dp = Dispatcher(
    bot=bot,
    storage=storage,
)


class LoginStates(StatesGroup):
    Username = State()
    Password = State()

class FilterBy(StatesGroup):
    type = State()
    min_sum = State()
    max_sum = State()
    method = State()


@dp.message_handler(commands=['login'])
async def login_user(message: types.Message):
    await message.answer('Введите ваш логин:', reply_markup=start_kb)
    await LoginStates.Username.set()


@dp.message_handler(state=LoginStates.Username)
async def process_login_username(message: types.Message, state: FSMContext):
    username = message.text

    async with state.proxy() as data:
        data['username'] = username

    await message.answer('Введите ваш пароль:')
    await LoginStates.Password.set()


@dp.message_handler(state=LoginStates.Password)
async def process_login_password(message: types.Message, state: FSMContext):
    password = message.text

    async with state.proxy() as data:
        data['password'] = password

    try:
        with conn.cursor() as curr:
            curr.execute(
                '''
                SELECT password
                FROM tb_user
                WHERE username = %s
                ''',
                (data['username'],)
            )
            user_data = curr.fetchone()

        if user_data and password == user_data[0]:
            await message.answer('Вы успешно авторизованы!', reply_markup=change_profile_info_kb)
        else:
            await message.answer('Неверный логин или пароль.')
    except Exception as e:
        await message.answer(f'Произошла ошибка при авторизации: {e}')
    finally:
        await state.finish()



@dp.message_handler(commands=['change_name'])
async def change_name(message: types.Message, state: FSMContext):
    await message.reply('Введите ваше новое имя: ')
    await state.set_state("changename")


@dp.message_handler(state="changename")
async def change_user_name(message: types.Message, state: FSMContext):
    name = message.text

    curr.execute(
        '''
        UPDATE tb_user
        SET name = %s
        WHERE username = %s
        ''',
        (name, message.from_user.username)
    )
    conn.commit()

    await message.answer(f'Имя пользователя изменено на: {name}')

    await state.finish()


@dp.message_handler(commands=['change_password'])
async def change_psw(message: types.Message, state: FSMContext):
    await message.reply('Введите ваш новый пароль: ')
    await state.set_state("changepsw")


@dp.message_handler(state="changepsw")
async def change_user_password(message: types.Message, state: FSMContext):
    psw = message.text

    try:
        with conn.cursor() as curr:
            curr.execute(
                '''
                UPDATE tb_user
                SET password = %s
                WHERE username = %s
                ''',
                (psw, message.from_user.username)
            )
            conn.commit()

            await message.answer('Пароль успешно изменен')

    except Exception as e:
        await message.answer(f'Произошла ошибка при смене пароля: {e}')

    finally:
        await state.finish()


@dp.message_handler(
    commands=['help']
)
async def help_command(message: types.Message):
    await message.reply(
        text=HELP_COMMAND
    )

    await message.delete()


@dp.message_handler(commands=['tenders'])
async def send_latest_tenders(message: types.Message):
    try:
        with conn.cursor() as curr:
            curr.execute(
                '''
                SELECT number, name, type, name_buy, method_buy, planned_sum, date, deadline
                FROM tender
                ORDER BY date DESC
                LIMIT 10
                '''
            )
            tenders = curr.fetchall()
        
        advanced_search_button = KeyboardButton("Расширенный поиск")
        reply_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        reply_keyboard.add(advanced_search_button)
        await message.answer("Выберите действие:", reply_markup=reply_keyboard)

        for tender in tenders:
            tender_id = str(tender[0])[6:]

            text_message = (
                f"НОМЕР ОБЪЯВЛЕНИЯ: {tender[0]}\n"
                f"НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ: {tender[1]}\n"
                f"ВИД ЗАКУПОК: {tender[2]}\n"
                f"НАИМЕНОВАНИЕ ЗАКУПКИ: {tender[3]}\n"
                f"МЕТОД ЗАКУПОК: {tender[4]}\n"
                f"ПЛАНИРУЕМАЯ СУММА: {tender[5]}\n"
                f"ДАТА ПУБЛИКАЦИИ: {tender[6].strftime('%Y-%m-%d')}\n"
                f"СРОК ПОДАЧИ ПРЕДЛОЖЕНИЙ: {tender[7].strftime('%Y-%m-%d')}\n"
            )
            
            tender_url = f"https://zakupki.okmot.kg/popp/view/order/view.xhtml?id={tender_id}"
            
            inline_kb = InlineKeyboardMarkup().add(InlineKeyboardButton("Подробнее", url=tender_url))
                
            await message.answer(text_message, reply_markup=inline_kb)
                
    except Exception as e:
        await message.answer(f'Произошла ошибка при получении тендеров: {e}')

@dp.message_handler(commands=['news'])
async def send_latest_news(message: types.Message):
    try:
        with conn.cursor() as curr:
            curr.execute(
                '''
                SELECT name, header, local_date_time
                FROM news
                ORDER BY local_date_time DESC
                LIMIT 10
                '''
            )
            news_items = curr.fetchall()
        
        seen_news = set()

        for news_item in news_items:
            name = news_item[0]
            header = news_item[1]
            publication_date = news_item[2].strftime('%Y-%m-%d %H:%M:%S')
            
            news_identifier = hash((name, header))

            if news_identifier not in seen_news:
                text_message = (
                    f"ЗАГОЛОВОК: {name}\n"
                    f"СОДЕРЖАНИЕ:\n{header}\n"
                    f"ДАТА ПУБЛИКАЦИИ: {publication_date}"
                )
                
                await message.answer(text_message)
                seen_news.add(news_identifier)
                
    except Exception as e:
        await message.answer(f'Произошла ошибка при получении новостей: {e}')


@dp.message_handler(lambda message: message.text == "Расширенный поиск")
async def send_advanced_search_options(message: types.Message):
    inline_kb = InlineKeyboardMarkup(row_width=1)
    inline_kb.add(InlineKeyboardButton("Вид закупок", callback_data="filter_type"))
    inline_kb.add(InlineKeyboardButton("Стоимость", callback_data="filter_price"))
    inline_kb.add(InlineKeyboardButton("Метод закупки", callback_data="filter_method"))
    
    await message.answer("Выберите опцию для фильтрации:", reply_markup=inline_kb)

@dp.callback_query_handler(lambda c: c.data.startswith('filter_'), state="*")
async def process_filter(callback_query: types.CallbackQuery):
    if callback_query.data == "filter_type":
        await FilterBy.type.set()
        await callback_query.message.answer("Введите вид закупок (Товары, Работы, Услуги):")
    elif callback_query.data == "filter_price":
        await FilterBy.min_sum.set()
        await callback_query.message.answer("Введите минимальную сумму для фильтрации:")
    elif callback_query.data == "filter_method":
        await FilterBy.method.set()
        await callback_query.message.answer("Введите метод закупки (Простой и Неограниченный):")


@dp.message_handler(state=FilterBy.type)
async def filter_by_type(message: types.Message, state: FSMContext):
    purchase_type = message.text
    if purchase_type not in ["Товары", "Работы", "Услуги"]:
        await message.answer("Некорректное значение. Введите 'Товары', 'Работы' или 'Услуги'.")
        return
    
    else:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                SELECT number, name, type, name_buy, method_buy, planned_sum, date, deadline
                FROM tender
                WHERE type = %s
                ORDER BY date DESC
                LIMIT 10
                ''', (purchase_type,)
            )
            tenders = cursor.fetchall()
            if tenders:
                for tender in tenders:
                    tender_id = str(tender[0])[6:]

                    text_message = (
                        f"НОМЕР ОБЪЯВЛЕНИЯ: {tender[0]}\n"
                        f"НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ: {tender[1]}\n"
                        f"ВИД ЗАКУПОК: {tender[2]}\n"
                        f"НАИМЕНОВАНИЕ ЗАКУПКИ: {tender[3]}\n"
                        f"МЕТОД ЗАКУПОК: {tender[4]}\n"
                        f"ПЛАНИРУЕМАЯ СУММА: {tender[5]}\n"
                        f"ДАТА ПУБЛИКАЦИИ: {tender[6].strftime('%Y-%m-%d')}\n"
                        f"СРОК ПОДАЧИ ПРЕДЛОЖЕНИЙ: {tender[7].strftime('%Y-%m-%d')}\n"
                    )
                    
                    tender_url = f"https://zakupki.okmot.kg/popp/view/order/view.xhtml?id={tender_id}"
                    
                    inline_kb = InlineKeyboardMarkup()
                    inline_kb.add(InlineKeyboardButton("Подробнее", url=tender_url))
            
                    await message.answer(text_message, reply_markup=inline_kb)
            else:
                await message.answer("Тендеры по заданным критериям не найдены.")
        await state.finish()


@dp.message_handler(state=FilterBy.method)
async def filter_by_method(message: types.Message, state: FSMContext):
    buy_method = message.text
    if buy_method not in ["Простой", "Неограниченный"]:
        await message.answer("Некорректное значение. Введите 'Простой', 'Неограниченный'.")
        return
    
    else:
        with conn.cursor() as cursor:
            cursor.execute(
                '''
                SELECT number, name, type, name_buy, method_buy, planned_sum, date, deadline
                FROM tender
                WHERE method_buy = %s
                ORDER BY date DESC
                LIMIT 10
                ''', (buy_method,)
            )
            tenders = cursor.fetchall()
            if tenders:
                for tender in tenders:
                    tender_id = str(tender[0])[6:]

                    text_message = (
                        f"НОМЕР ОБЪЯВЛЕНИЯ: {tender[0]}\n"
                        f"НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ: {tender[1]}\n"
                        f"ВИД ЗАКУПОК: {tender[2]}\n"
                        f"НАИМЕНОВАНИЕ ЗАКУПКИ: {tender[3]}\n"
                        f"МЕТОД ЗАКУПОК: {tender[4]}\n"
                        f"ПЛАНИРУЕМАЯ СУММА: {tender[5]}\n"
                        f"ДАТА ПУБЛИКАЦИИ: {tender[6].strftime('%Y-%m-%d')}\n"
                        f"СРОК ПОДАЧИ ПРЕДЛОЖЕНИЙ: {tender[7].strftime('%Y-%m-%d')}\n"
                    )
                    
                    tender_url = f"https://zakupki.okmot.kg/popp/view/order/view.xhtml?id={tender_id}"
                    
                    inline_kb = InlineKeyboardMarkup()
                    inline_kb.add(InlineKeyboardButton("Подробнее", url=tender_url))
            
                    await message.answer(text_message, reply_markup=inline_kb)
            else:
                await message.answer("Тендеры по заданным критериям не найдены.")
        await state.finish()


@dp.message_handler(state=FilterBy.min_sum)
async def set_min_sum(message: types.Message, state: FSMContext):
    try:
        min_sum = float(message.text)
    except ValueError:
        await message.reply("Введите числовое значение для минимальной суммы.")
        return

    async with state.proxy() as data:
        data['min_sum'] = min_sum

    await FilterBy.next()
    await message.reply("Введите максимальную сумму для фильтрации:")


@dp.message_handler(state=FilterBy.max_sum)
async def set_max_sum(message: types.Message, state: FSMContext):
    try:
        max_sum = float(message.text)
    except ValueError:
        await message.reply("Введите числовое значение для максимальной суммы.")
        return

    async with state.proxy() as data:
        min_sum = data['min_sum']
        if min_sum >= max_sum:
            await message.reply("Минимальная сумма должна быть меньше максимальной.")
            return

        data['max_sum'] = max_sum

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT number, name, type, name_buy, method_buy, planned_sum, date, deadline
            FROM tender
            WHERE planned_sum BETWEEN %s AND %s
            ORDER BY date DESC
            LIMIT 10
            """, (min_sum, max_sum)
        )
        tenders = cursor.fetchall()
        if tenders:
            for tender in tenders:
                tender_id = str(tender[0])[6:]

                text_message = (
                    f"НОМЕР ОБЪЯВЛЕНИЯ: {tender[0]}\n"
                    f"НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ: {tender[1]}\n"
                    f"ВИД ЗАКУПОК: {tender[2]}\n"
                    f"НАИМЕНОВАНИЕ ЗАКУПКИ: {tender[3]}\n"
                    f"МЕТОД ЗАКУПОК: {tender[4]}\n"
                    f"ПЛАНИРУЕМАЯ СУММА: {tender[5]}\n"
                    f"ДАТА ПУБЛИКАЦИИ: {tender[6].strftime('%Y-%m-%d')}\n"
                    f"СРОК ПОДАЧИ ПРЕДЛОЖЕНИЙ: {tender[7].strftime('%Y-%m-%d')}\n"
                )
                
                tender_url = f"https://zakupki.okmot.kg/popp/view/order/view.xhtml?id={tender_id}"
                
                inline_kb = InlineKeyboardMarkup()
                inline_kb.add(InlineKeyboardButton("Подробнее", url=tender_url))

                await message.answer(text_message, reply_markup=inline_kb)
        else:
            await message.answer("Тендеры по заданным критериям не найдены.")
    await state.finish()

@dp.message_handler(commands=['compliants'])
async def send_latest_complaints(message: types.Message):
    try:
        with conn.cursor() as curr:
            curr.execute(
                '''
                SELECT number, name_provider, number_ad, buyer, complaint, complaint_status, complaint_type, local_date_time, solution
                FROM complaints;
                '''
            )
            complaints = curr.fetchall()
        
        for complaint in complaints:
            complaint_id = str(complaint[0])[6:]
            
            text_message = (
                f"№: {complaint[0]}\n"
                f"НАИМЕНОВАНИЕ ПОСТАВЩИКА: {complaint[1]}\n"
                f"НАИМЕНОВАНИЕ ОБЪЯВЛЕНИЯ: {complaint[2]}\n"
                f"НАИМЕНОВАНИЕ ЗАКУПАЮЩЕЙ ОРГАНИЗАЦИИ: {complaint[3]}\n"
                f"СУТЬ ЖАЛОБЫ: {complaint[4]}\n"
                f"СТАТУС: {complaint[5]}\n"
                f"ВИД ЖАЛОБЫ: {complaint[6]}\n"
                f"ДАТА ПУБЛИКАЦИИ ЖАЛОБЫ: {complaint[7]}\n"
            )
            
            compliant_url = f"http://zakupki.gov.kg/popp/view/services/complaints/detail.xhtml?id={complaint_id}"
            
            inline_kb1 = InlineKeyboardMarkup()
            inline_kb1.add(InlineKeyboardButton("Подробнее", url=compliant_url))
            
            await message.answer(text_message, reply_markup=inline_kb1)
                
    except Exception as e:
        await message.answer(f'Произошла ошибка при получении тендеров: {e}')

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    photo_path = "C:\\Users\\User\\Desktop\\gos_zakupki_bot\\transparency.jpg"
    photo = InputFile(photo_path)
    
    await message.answer_photo(
        photo=photo,
        caption="Добро пожаловать в наш телеграм бот 'simple_tender'\n\n \
            Этот бот создан для того, чтобы помочь малым и средним бизнесам узнавать больше информации о проведенных и предстоящих тендерах мы за ПРОЗРАЧНОСТЬ!",
        reply_markup=start_kb
    )
    await message.delete()


if __name__ == '__main__':
    executor.start_polling(
        dispatcher=dp,
        skip_updates=True
    )
