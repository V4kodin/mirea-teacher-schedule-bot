import aiogram
import requests
import config
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup, \
    KeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery
from handlers import teacher_parser

bot = aiogram.Bot(token=config.TOKEN)
storage = MemoryStorage()
dp = aiogram.Dispatcher(bot, storage=storage)


# ToDo: resize_keyboard=True markup

class StatesGroup(StatesGroup):
    name_S = State()
    teacher_S = State()
    day_S = State()


@dp.message_handler(commands=['start'], state='*')
async def start_message(message: aiogram.types.Message):
    # Отправка сообщения: Введите фамилию преподавателя
    # TODO: delete Karpow board
    buttonK = KeyboardButton('Карпов')
    karb = ReplyKeyboardMarkup(resize_keyboard=True).add(buttonK)
    await message.answer(text='Введите фамилию преподавателя', reply_markup=karb)


@dp.message_handler(lambda message: message.text not in "/start", state='*')
async def get_name(message: aiogram.types.Message, state: FSMContext) -> None:
    await StatesGroup.name_S.set()  # set name state
    print(f"User: {message.from_user.id} set name: {message.text}")
    # Поиск преподавателей

    teacher = message.text
    # Запись в контекст пользователя
    async with state.proxy() as data:
        data['teacher'] = teacher
        try:
            url = f"https://schedule.mirea.ninja/api/schedule/teacher/{teacher}"
            response = requests.get(url)
            teacher_schedule = response.json() if response.status_code == 200 else None
        except Exception as e:
            print("Api exception:" + e)
            await message.reply(text='Api упало')  # TODO: не вызывается
        # Запись teacher_schedule в контекст пользователя
        data['teacher_schedule'] = teacher_schedule
    if teacher_schedule is None:
        # Ответ на сообщение сообщения: Преподаватель не найден
        await message.reply(text='Преподаватель не найден')
        return
    array_of_teachers = teacher_parser.list_of_teachers(teacher_schedule)
    #  Запись в контекст пользователя
    async with state.proxy() as data:
        data["array_of_teachers"] = array_of_teachers

    # Создание inline клавиатуры с неопределенным количеством кнопок
    markup = InlineKeyboardMarkup()
    for i in range(len(array_of_teachers)):
        markup.add(InlineKeyboardButton(text=array_of_teachers[i], callback_data=f"teacher_button{i}"))
    async with state.proxy() as data:
        data['name'] = message.text

    # Отправка сообщения: Выберите преподавателя
    await message.reply(text='Выберете нужного преподавателя', reply_markup=markup)


@dp.callback_query_handler(
    lambda c: c.data.startswith('teacher_button'), state=StatesGroup.name_S)
async def select_teacher(callback_query: aiogram.types.CallbackQuery, state: FSMContext) -> None:
    # Remove inline keyboard
    await callback_query.message.edit_reply_markup(reply_markup=None)

    # Interpretation of the callback data
    async with state.proxy() as data:
        array_of_teachers = data["array_of_teachers"]
        # фильтрация расписания по имени преподавателя
        teacher_schedule = data["teacher_schedule"]
        teacher_schedule_copy = {"schedules": []}
        for i in range(len(array_of_teachers)):
            if i == int(callback_query.data[14:]):
                Full_teacher_name = array_of_teachers[i]
                for j in range(len(teacher_schedule["schedules"])):
                    if Full_teacher_name in teacher_schedule["schedules"][j]['lesson']['teachers']:
                        teacher_schedule_copy["schedules"].append(teacher_schedule["schedules"][j])
                data["teacher_schedule"] = teacher_schedule_copy
                break
    print(
        f"User: {callback_query.from_user.id} selected teacher: {Full_teacher_name}, count of buttons: {len(array_of_teachers)}")
    await callback_query.message.edit_text(text=f"Вы выбрали {Full_teacher_name}")
    # markup of day selection
    markup = InlineKeyboardMarkup(row_width=4)  # resize_keyboard=True,
    item1 = InlineKeyboardButton("Понедельник", callback_data='Понедельник')
    item2 = InlineKeyboardButton("Вторник", callback_data='Вторник')
    item3 = InlineKeyboardButton("Среда", callback_data='Среда')
    item4 = InlineKeyboardButton("Четверг", callback_data='Четверг')
    item5 = InlineKeyboardButton("Пятница", callback_data='Пятница')
    item6 = InlineKeyboardButton("Суббота", callback_data='Суббота')
    item7 = InlineKeyboardButton("Назад", callback_data='Назад')
    markup.add(item1, item2, item3, item4, item5, item6, item7)

    await StatesGroup.next()  # to teacher state
    # отправка сообщения пользователю
    await callback_query.message.answer('Выберите день недели', reply_markup=markup)


@dp.callback_query_handler(
    lambda c: c.data in ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Назад'],
    state=StatesGroup.teacher_S, )
async def get_day(callback_query: aiogram.types.CallbackQuery, state: FSMContext) -> None:
    print(f"user {callback_query.from_user.id} selected day {callback_query.data}")
    # remove reply markup
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.edit_text(text=f"Вы выбрали {callback_query.data}")
    day = callback_query.data
    # Запись в контекст пользователя
    async with state.proxy() as data:
        data['day'] = day

    if day in ['Понедельник']:
        day = '1'
    elif day in ['Вторник']:
        day = '2'
    elif day in ['Среда']:
        day = '3'
    elif day in ['Четверг']:
        day = '4'
    elif day in ['Пятница']:
        day = '5'
    elif day in ['Суббота']:
        day = '6'
    elif day == 'Назад':
        await callback_query.message.answer('Введите фамилию преподавателя')
        await state.finish()
        return
    else:
        await callback_query.message.answer('Some problems with day')
    await state.update_data(day=day)
    await StatesGroup.next()  # to day state

    markup = InlineKeyboardMarkup(row_width=4)
    item1 = InlineKeyboardButton("1", callback_data='1')
    item2 = InlineKeyboardButton("2", callback_data='2')
    item3 = InlineKeyboardButton("3", callback_data='3')
    item4 = InlineKeyboardButton("4", callback_data='4')
    item5 = InlineKeyboardButton("5", callback_data='5')
    item6 = InlineKeyboardButton("6", callback_data='6')
    item7 = InlineKeyboardButton("7", callback_data='7')
    item8 = InlineKeyboardButton("8", callback_data='8')
    item9 = InlineKeyboardButton("9", callback_data='9')
    item10 = InlineKeyboardButton("10", callback_data='10')
    item11 = InlineKeyboardButton("11", callback_data='11')
    item12 = InlineKeyboardButton("12", callback_data='12')
    item13 = InlineKeyboardButton("13", callback_data='13')
    item14 = InlineKeyboardButton("14", callback_data='14')
    item15 = InlineKeyboardButton("15", callback_data='15')
    item16 = InlineKeyboardButton("16", callback_data='16')
    item17 = InlineKeyboardButton("17", callback_data='17')
    item18 = InlineKeyboardButton("Отмена", callback_data='Отмена')
    markup.add(item1, item2, item3, item4, item5, item6, item7, item8, item9, item10, item11, item12, item13, item14,
               item15, item16, item17, item18)
    await callback_query.message.reply('Выберите неделю', reply_markup=markup)


@dp.callback_query_handler(
    lambda c: c.data in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17',
                         'Отмена'],
    state=StatesGroup.day_S)
async def get_week(callback_query: aiogram.types.CallbackQuery, state: FSMContext) -> None:
    print(f"user {callback_query.from_user.id} selected week {callback_query.data}")
    # remove reply markup
    await callback_query.message.edit_reply_markup(reply_markup=None)
    # достаем данные из контекста
    async with state.proxy() as data:
        day = data['day']
    # cancel button processing
    if callback_query.data == 'Отмена':
        await callback_query.message.answer('Вы выбрали отмену')
        await StatesGroup.name.set()
        print(f"dat is {day}")
        callback_query.data = day
        return
    else:
        await callback_query.message.edit_text(text=f"Вы выбрали {callback_query.data} неделю")

    weeknum = callback_query.data
    # Запись в контекст пользователя
    async with state.proxy() as data:
        data['weeknum'] = weeknum
    # if weeknum == 'отмена' or weeknum == 'Отмена':
    #    pass    #ToDo: Не работает
    #    return bot.send_message(message.chat.id, 'Введите фамилию преподавателя',
    #                            reply_markup=aiogram.types.ReplyKeyboardRemove())
    # if weeknum.isdigit() == False:
    #    bot.reply_to(message, 'Номер недели должен быть числом')
    #    return bot.send_message(message.chat.id, 'Введите фамилию преподавателя')
    # вытаскиваем данные из контекста пользователя
    async with state.proxy() as data:
        teacher_schedule = data['teacher_schedule']
    if teacher_schedule:
        text = ""
        weekdays = {
            1: "Понедельник",
            2: "Вторник",
            3: "Среда",
            4: "Четверг",
            5: "Пятница",
            6: "Суббота",
        }
        teacher_schedule = teacher_schedule["schedules"]
        teacher_schedule = sorted(teacher_schedule, key=lambda x: x["weekday"])
        teacher_schedule = sorted(teacher_schedule, key=lambda x: x["group"])
        teacher_schedule = list(filter(lambda x: x["weekday"] == int(day), teacher_schedule))
        teacher_schedule = list(filter(lambda x: int(weeknum) in x["lesson"]["weeks"], teacher_schedule))
        teacher_schedule = sorted(teacher_schedule, key=lambda x: x["lesson"]["time_start"])
        teacher_schedule = sorted(teacher_schedule, key=lambda x: x["lesson"]["time_end"])
        remove_index = []
        for i in range(len(teacher_schedule)):
            for j in range(i + 1, len(teacher_schedule)):
                if (
                        teacher_schedule[i]["weekday"] == teacher_schedule[j]["weekday"]
                        and teacher_schedule[i]["lesson"]["name"]
                        == teacher_schedule[j]["lesson"]["name"]
                        and teacher_schedule[i]["lesson"]["weeks"]
                        == teacher_schedule[j]["lesson"]["weeks"]
                        and teacher_schedule[i]["lesson"]["time_start"]
                        == teacher_schedule[j]["lesson"]["time_start"]
                ):
                    teacher_schedule[i]["group"] += ", " + teacher_schedule[j]["group"]
                    remove_index.append(j)
        remove_index = set(remove_index)
        for i in sorted(remove_index, reverse=True):
            del teacher_schedule[i]
        if not teacher_schedule:
            await callback_query.message.answer("В этот день у преподавателя нет пар")
            await state.finish()
            return
        i = 0
        while i < len(teacher_schedule) - 1:
            if (
                    teacher_schedule[i]["weekday"] == teacher_schedule[i + 1]["weekday"]
                    and teacher_schedule[i]["group"] == teacher_schedule[i + 1]["group"]
                    and teacher_schedule[i]["lesson"]["time_start"]
                    == teacher_schedule[i + 1]["lesson"]["time_start"]
            ):
                teacher_schedule[i]["lesson"]["weeks"] += teacher_schedule[i + 1]["lesson"][
                    "weeks"
                ]
                teacher_schedule[i]["lesson"]["weeks"] = sorted(
                    teacher_schedule[i]["lesson"]["weeks"]
                )
                teacher_schedule.pop(i + 1)
            else:
                i += 1
        for schedule in teacher_schedule:
            if schedule["lesson"]["weeks"] == list(range(1, 18)):
                weeks = "все"
            elif schedule["lesson"]["weeks"] == list(range(2, 18, 2)):
                weeks = "по чётным"
            elif schedule["lesson"]["weeks"] == list(range(1, 18, 2)):
                weeks = "по нечётным"
            else:
                weeks = ", ".join(str(week) for week in schedule["lesson"]["weeks"])
            room = ", ".join(schedule["lesson"]["rooms"])
            teachers = ", ".join(schedule["lesson"]["teachers"])
            weekday = weekdays[schedule["weekday"]]
            text += f'📝 Пара № {schedule["lesson_number"] + 1} в ⏰ {schedule["lesson"]["time_start"]}–{schedule["lesson"]["time_end"]}\n'
            text += f'📝 {schedule["lesson"]["name"]}\n'
            text += f'👥 Группы: {schedule["group"]}\n'
            text += f'📚 Тип: {schedule["lesson"]["types"]}\n'
            text += f"👨🏻‍🏫 Преподаватели: {teachers}\n"
            text += f"🏫 Аудитории: {room}\n"
            text += f"📅 Недели: {weeks}\n"
            text += f"📆 День недели: {weekday}\n\n"
        text_len = len(text)
        for i in range(0, text_len, 4096):
            await bot.send_message(callback_query.message.chat.id, text[i: i + 4096])
    else:
        await callback_query.message.answer(callback_query.message.chat.id,
                                            'Ошибка на стороне api, преподаватель не найден')

    await state.finish()