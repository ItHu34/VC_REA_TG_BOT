import aiosqlite
from aiogram import Bot, types, Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from setup import is_admin



feedback_router = Router()



class FeedbackStates(StatesGroup):
    full_name_feedbacks = State()
    group_name_feedbacks = State()
    event_name_feedbacks = State()
    feedback_text_feedbacks = State()





@feedback_router.message(Command("admin_get_info_feedbacks"))
async def cmd_get_info_feedbacks(message: types.Message):
    if not await is_admin(message):
        await message.answer("Вы не админ")
    else:
        async with aiosqlite.connect("data.db") as db:
            async with db.execute("SELECT full_name_feedbacks, group_name_feedbacks, event_name_feedbacks, feedback_text_feedbacks, tg_id_feedbacks FROM feedbacks") as cursor:
                feedbacks_admin = await cursor.fetchall()
        if not feedbacks_admin:
            await message.answer("Данные отсутствуют")
            return
        formatted_feedbacks = []
        for row in feedbacks_admin:
            formatted_row = "; ".join(map(str, row))
            formatted_feedbacks.append(formatted_row)
        result = "\n\n".join(formatted_feedbacks)
        await message.answer(result)



@feedback_router.message(Command("feedback"))
async def cmd_feedback(message: Message, state: FSMContext):
    await message.answer(
        "Приступим к написанию отзыва.\n\nДля начала давай познакомимся?\n\n"
        "Напиши свое ФИО, чтобы в случае чего мы могли с тобой связаться!"
    )
    await state.set_state(FeedbackStates.full_name_feedbacks)


@feedback_router.message(FeedbackStates.full_name_feedbacks)
async def process_full_name_feedbacks(message: Message, state: FSMContext):
    full_name_feedbacks = message.text.strip()
    await state.update_data(full_name_feedbacks=full_name_feedbacks)
    await state.set_state(FeedbackStates.group_name_feedbacks)
    await message.answer(
        f"Супер. Рад познакомиться, {full_name_feedbacks}!\n\nТеперь, если ты студент Университета, пришли номер своей группы.\n\n"
        f"Например: 15.14Д-ЖУР01/25б\nЕсли не являешься студентом: '—'"
    )


@feedback_router.message(FeedbackStates.group_name_feedbacks)
async def process_group_name_feedbacks(message: Message, state: FSMContext):
    group_name_feedbacks = message.text.strip()
    await state.update_data(group_name_feedbacks=group_name_feedbacks)
    await state.set_state(FeedbackStates.event_name_feedbacks)
    await message.answer(
        f"Хорошо, теперь я знаю что ты из группы: {group_name_feedbacks}, "
        f"Напиши название мероприятия и дату, например:\n\n"
        f"'VIII Профессорский форум «Наука и образование», 18.11.2025'"
    )


@feedback_router.message(FeedbackStates.event_name_feedbacks)
async def process_event_name_feedbacks(message: Message, state: FSMContext):
    event_name_feedbacks = message.text.strip()
    await state.update_data(event_name_feedbacks=event_name_feedbacks)
    await state.set_state(FeedbackStates.feedback_text_feedbacks)
    data = await state.get_data()
    full_name_feedbacks = data.get("full_name_feedbacks")
    group_name_feedbacks = data.get("group_name_feedbacks")
    await message.answer(
        f"Теперь я знаю, что {full_name_feedbacks} из группы {group_name_feedbacks} побывал на мероприятии: {event_name_feedbacks}. "
        f"Что ты можешь о нем рассказать?"
    )
    await message.answer(
        f'Формат составления отзыва:\n\n'
        f'1) Заголовок\n1 предложение раскрывающее смысл публикации\n\n'
        f'2) Лид\n1-4 предложения кратко описывающих заголовок\n\n'
        f'3) Основной текст\n\n'
        f'4) Комментарий (по желанию)\n\n'
        f'5) Итог\n1-4 предложения подводящих итог\n\n'
        f'6) Хештеги (по желанию)'
    )


@feedback_router.message(FeedbackStates.feedback_text_feedbacks)
async def process_feedback(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    full_name_feedbacks = data["full_name_feedbacks"]
    group_name_feedbacks = data["group_name_feedbacks"]
    event_name_feedbacks = data["event_name_feedbacks"]
    feedback_text_feedbacks = message.text.strip()
    tg_id_feedbacks = f"@{message.from_user.username}" if message.from_user.username else str(message.from_user.id)
    await insert_feedback(full_name_feedbacks, group_name_feedbacks, event_name_feedbacks, feedback_text_feedbacks, tg_id_feedbacks)
    whole_feedback = (
        f"Отзыв сохранен, спасибо!\n\n"
        f"Итоговый отзыв:\n"
        f"Твои ФИО: {full_name_feedbacks}\n"
        f"Твоя группа: {group_name_feedbacks}\n"
        f"Твое мероприятие: {event_name_feedbacks}\n"
        f"Твой отзыв: {feedback_text_feedbacks}"
    )
    await message.answer(whole_feedback)
    await bot.send_message(-4822221970, whole_feedback)
    await state.clear()


async def insert_feedback(full_name_feedbacks, group_name_feedbacks, event_name_feedbacks, feedback_text_feedbacks, tg_id_feedbacks):
    async with aiosqlite.connect("data.db") as db:
        await db.execute("""
            INSERT INTO feedbacks (full_name_feedbacks, group_name_feedbacks, event_name_feedbacks, feedback_text_feedbacks, tg_id_feedbacks)
            VALUES (?, ?, ?, ?, ?)
        """, (full_name_feedbacks, group_name_feedbacks, event_name_feedbacks, feedback_text_feedbacks, tg_id_feedbacks))
        await db.commit()