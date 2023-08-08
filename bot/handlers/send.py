from telegram import Update
from telegram.ext import CallbackContext

import bot.formats.decode as decode
import bot.formats.formatting as formatting
import bot.handlers.construct as construct
import bot.handlers.fetch as fetch

GETNAME, GETDAY, GETWEEK, TEACHER_CLARIFY, BACK, GETROOM, ROOM_CLARIFY = range(7)


async def send_week_selector(
        update: Update,
        context: CallbackContext,
        firsttime=False):
    """
    Отправка селектора недели. По умолчанию изменяет предыдущее сообщение, но при firsttime=True отправляет в виде
    нового сообщения @param update: Update class of API @param context: CallbackContext of API @param firsttime:
    Впервые ли производится общение с пользователем @return: Статус следующего шага - GETWEEK
    """
    if context.user_data["state"] == "get_room":
        room = context.user_data["room"]

        if firsttime:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Выбрана аудитория: {room}\n" +
                     f"Выберите неделю:",
                reply_markup=construct.construct_weeks_markup()
            )

        else:
            await update.callback_query.edit_message_text(
                text=f"Выбрана аудитория: {room}\n" +
                     f"Выберите неделю:",
                reply_markup=construct.construct_weeks_markup()
            )

        return GETWEEK

    teacher = ", ".join(decode.decode_teachers([context.user_data["teacher"]]))

    if firsttime:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Выбран преподаватель: {teacher}\n" +
                 f"Выберите неделю:",
            reply_markup=construct.construct_weeks_markup()
        )

    else:
        await update.callback_query.edit_message_text(
            text=f"Выбран преподаватель: {teacher}\n" +
                 f"Выберите неделю:",
            reply_markup=construct.construct_weeks_markup()
        )

    return GETWEEK


async def resend_name_input(update: Update, context: CallbackContext):
    """
    Просит ввести имя преподавателя заново
    @param update: Update class of API
    @param context: CallbackContext of API
    @return: Статус следующего шага - GETNAME
    """
    await update.callback_query.answer(text="Введите новую фамилию", show_alert=True)


async def send_teacher_clarity(
        update: Update,
        context: CallbackContext,
        firsttime=False):
    """
    Отправляет список обнаруженных преподавателей. В случае если общение с пользователем не впервые - редактирует
    сообщение, иначе отправляет новое. @param update: Update class of API @param context: CallbackContext of API
    @param firsttime: Впервые ли производится общение с пользователем @return: Статус следующего шага - TEACHER_CLARIFY
    """
    available_teachers = context.user_data["available_teachers"]
    few_teachers_markup = construct.construct_teacher_markup(available_teachers)

    if firsttime:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Выберите преподвателя",
            reply_markup=few_teachers_markup
        )

    else:
        await update.callback_query.edit_message_text(
            text="Выберите преподвателя",
            reply_markup=few_teachers_markup
        )

    return TEACHER_CLARIFY


async def send_day_selector(update: Update, context: CallbackContext):
    """
    Отправляет селектор дня недели с указанием дней, когда преподаватель не имеет пар.
    @param update: Update class of API
    @param context: CallbackContext of API
    @return: Статус следующего шага - GETDAY
    """
    if context.user_data["state"] == "get_room":
        state = context.user_data["state"]
        room = context.user_data["room"]
        week = context.user_data["week"]
        schedule = context.user_data["schedule"]

        if schedule:
            room_workdays = construct.construct_teacher_workdays(week, schedule, room)

            await update.callback_query.edit_message_text(
                text=f"Выбрана аудитория: {room} \n" +
                     f"Выбрана неделя: {week} \n" +
                     f"Выберите день:",
                reply_markup=room_workdays
            )

            return GETDAY

        else:
            await update.callback_query.answer(
                text="Ошибка\n\nВ данной аудитории нет пар\nПожалуйста выберите другую аудиторию.", show_alert=True)

            return GETWEEK

    teacher = ", ".join(decode.decode_teachers([context.user_data["teacher"]]))
    week = context.user_data["week"]
    schedule = context.user_data["schedule"]
    teacher_workdays = construct.construct_teacher_workdays(week, schedule, False)

    await update.callback_query.edit_message_text(
        text=f"Выбран преподаватель: {teacher} \n" +
             f"Выбрана неделя: {week} \n" +
             f"Выберите день:",
        reply_markup=teacher_workdays
    )

    return GETDAY


async def send_result(update: Update, context: CallbackContext):
    """
    Выводит результат пользователю.
    В user_data["week"] и user_data["day"] должны быть заполнены перед вызовом!
    Если user_data["week"]=-1 - выводится вся неделя
    """
    if context.user_data["state"] == "get_room":
        room = context.user_data["room"]
        week = context.user_data["week"]
        weekday = context.user_data["day"]
        schedule_data = context.user_data["schedule"]

        parsed_schedule = formatting.parse(
            schedule_data,
            weekday,
            week,
            False,
            context,
            room)

    else:

        week = context.user_data["week"]
        weekday = context.user_data["day"]
        schedule_data = context.user_data["schedule"]
        teacher_surname = context.user_data["teacher"]

        parsed_schedule = formatting.parse(
            schedule_data,
            weekday,
            week,
            teacher_surname,
            context,
            False)

    parsed_schedule = formatting.remove_duplicates_merge_groups_with_same_lesson(
        parsed_schedule, context)

    parsed_schedule = formatting.merge_weeks_numbers(parsed_schedule)

    if len(parsed_schedule) == 0:
        await update.callback_query.answer(
            text="В этот день пар нет.", show_alert=True)
        return GETWEEK

    blocks_of_text = formatting.format_outputs(parsed_schedule, context)

    return await telegram_delivery_optimisation(blocks_of_text, update, context)


async def telegram_delivery_optimisation(
        blocks: list,
        update: Update,
        context: CallbackContext):
    week = context.user_data["week"]

    if context.user_data["state"] == "get_room":
        room = context.user_data["room"]
        room_id = context.user_data["room_id"]
        context.user_data["schedule"] = fetch.fetch_room_schedule_by_id(room_id)
        schedule = context.user_data["schedule"]
        teacher_workdays = construct.construct_teacher_workdays(week, schedule, room)
    else:

        context.user_data["schedule"] = fetch.fetch_schedule_by_name(
            context.user_data["teacher"])
        schedule = context.user_data["schedule"]
        teacher_workdays = construct.construct_teacher_workdays(week, schedule, False)

    chunk = ""
    first = True
    for block in blocks:

        if len(chunk) + len(block) <= 4096:
            chunk += block

        else:
            if first:
                if update.callback_query.inline_message_id:
                    await update.callback_query.answer(
                        text="Слишком длинное расписание, пожалуйста, воспользуйтесь личными сообщениями бота или "
                             "выберите конкретный день недели", show_alert=True)
                    break

                await update.callback_query.edit_message_text(chunk)
                first = False

            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=chunk)

            chunk = block

    if chunk:
        if first:
            await update.callback_query.edit_message_text(
                chunk, reply_markup=teacher_workdays)

        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=chunk,
                reply_markup=teacher_workdays)

    return GETDAY


async def send_room_clarity(update, context, firsttime=False):
    available_rooms = context.user_data["available_rooms"]
    few_rooms_markup = construct.construct_rooms_markup(available_rooms)

    if firsttime:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Выберите аудиторию",
            reply_markup=few_rooms_markup
        )

    else:
        await update.callback_query.edit_message_text(
            text="Выберите аудиторию",
            reply_markup=few_rooms_markup
        )

    return ROOM_CLARIFY
