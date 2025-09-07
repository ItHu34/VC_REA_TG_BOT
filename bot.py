import asyncio
import logging
import aiosqlite
import re
from aiogram import Bot, Dispatcher, types, F
from datetime import datetime
from conf_reader import config
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from pathlib import Path
from collections import defaultdict





def safe_handler(func):
    import functools
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            try:
                from aiogram import types as _types
                msg = None
                for a in args:
                    if isinstance(a, _types.Message):
                        msg = a
                        break
                    if isinstance(a, _types.CallbackQuery):
                        msg = a.message
                        break
                if msg is None:
                    for v in kwargs.values():
                        if isinstance(v, _types.Message):
                            msg = v
                            break
                        if isinstance(v, _types.CallbackQuery):
                            msg = v.message
                            break
                if msg is not None:
                    await msg.answer(f"Произошла непредвиденная ошибка: {e}")
            except Exception:
                pass
            import logging as _logging
            _logging.exception("Unhandled exception in handler")
    return wrapper


logging.basicConfig(level=logging.INFO)


bot = Bot(
    token=config.bot_token.get_secret_value(),
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)


dp = Dispatcher()
dp["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")


admin_ids = {301892352, 328168838, 763733398, 951008860, 5411845362, 753665396, 1378784301, 1825364517, 1224393478, 625056746, 1817275981, 1032264542, 944769569, 5690157353, 1575605738, 1342716925, 1691986075}


async def init_db():
    async with aiosqlite.connect("data.db") as connection:
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id_feedbacks INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name_feedbacks TEXT,
                group_name_feedbacks TEXT,
                event_name_feedbacks TEXT,
                feedback_text_feedbacks TEXT,
                tg_id_feedbacks TEXT
            )
        """)
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS interviews (
                id_interviews INTEGER PRIMARY KEY AUTOINCREMENT,
                day_interviews TEXT,
                time_interviews TEXT,
                tg_id_volunteer_interviews TEXT,
                tg_id_recruiter_interviews TEXT,
                full_name_interviews TEXT,
                is_busy_interviews INTEGER
            )
        """)
        await connection.commit()


class FeedbackStates(StatesGroup):
    full_name_feedbacks = State()
    group_name_feedbacks = State()
    event_name_feedbacks = State()
    feedback_text_feedbacks = State()


class InterviewStates(StatesGroup):
    full_name_interviews = State()
    user_time_slot = State()


class AdminAddSlotStates(StatesGroup):
    day_interviews = State()
    time_interviews = State()
    tg_id_recruiter_interviews = State()


class AdminDeleteSlotStates(StatesGroup):
    slot_id = State()
    confirm = State()





@safe_handler
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        " Привет, друг! Я — бот Волонтерского центра РЭУ. Помогаю делать добро легче и популярнее\n\n"
        "Какой у тебя вопрос?\n\n"
        "Для отправки фотографий с мероприятия напиши: /images\n"
        "Для отправки отзыва о мероприятии напиши: /feedback\n"
        "Для записи на интервью на Волонтера Плехановки напиши: /interviews"
    )



@safe_handler
@dp.message(Command("admin_add_slot"))
async def cmd_admin_add_slot(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        await message.answer("Вы не админ")
        return

    await message.answer("Введите дату проведения интервью (например: 08.09.2025 - понедельник):")
    await state.set_state(AdminAddSlotStates.day_interviews)

@safe_handler
@dp.message(AdminAddSlotStates.day_interviews)
async def process_admin_add_day(message: Message, state: FSMContext):
    await state.update_data(day_interviews=message.text.strip())
    await message.answer("Теперь введите время проведения интервью (например: 12:30-12:50):")
    await state.set_state(AdminAddSlotStates.time_interviews)

@safe_handler
@dp.message(AdminAddSlotStates.time_interviews)
async def process_admin_add_time(message: Message, state: FSMContext):
    await state.update_data(time_interviews=message.text.strip())
    await message.answer("Введите tg_id тим-лидера (например: @nickname):")
    await state.set_state(AdminAddSlotStates.tg_id_recruiter_interviews)

@safe_handler
@dp.message(AdminAddSlotStates.tg_id_recruiter_interviews)
async def process_admin_add_recruiter(message: Message, state: FSMContext):
    tg_id_recruiter = message.text.strip()

    data = await state.get_data()
    day_interviews = data.get("day_interviews")
    time_interviews = data.get("time_interviews")

    if not day_interviews or not time_interviews:
        await message.answer("Ошибка: данные неполные. Повторите команду /admin_add_slot заново.")
        await state.clear()
        return

    async with aiosqlite.connect("data.db") as db:
        await db.execute(
            """
            INSERT INTO interviews 
            (day_interviews, time_interviews, tg_id_recruiter_interviews, is_busy_interviews) 
            VALUES (?, ?, ?, '0')
            """,
            (day_interviews, time_interviews, tg_id_recruiter)
        )
        await db.commit()

    whole_new_slot = (
        f"Слот успешно добавлен!\n\n"
        f"Дата: {day_interviews}\n"
        f"Время: {time_interviews}\n"
        f"Тим-лидер: {tg_id_recruiter}"
    )

    await message.answer(whole_new_slot)
    await bot.send_message(-4822221970, whole_new_slot)
    await state.set_state(AdminDeleteSlotStates.confirm)
    await state.clear()



@safe_handler
@dp.message(Command("admin_delete_slot"))
async def cmd_admin_delete_slot(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        await message.answer("Вы не админ")
        return

    await message.answer("Введите ID временного слота, который хотите удалить:")
    await state.set_state(AdminDeleteSlotStates.slot_id)

@safe_handler
@dp.message(AdminDeleteSlotStates.slot_id)
async def process_delete_slot_id(message: Message, state: FSMContext):
    slot_id = message.text.strip()

    async with aiosqlite.connect("data.db") as db:
        async with db.execute(
            "SELECT id_interviews, day_interviews, time_interviews, tg_id_recruiter_interviews "
            "FROM interviews WHERE id_interviews = ?", (slot_id,)
        ) as cursor:
            slot = await cursor.fetchone()

    if not slot:
        await message.answer("Слот с таким ID не найден. Попробуйте снова.")
        await state.clear()
        return

    id_interviews, day, time, recruiter = slot
    await state.update_data(slot_id=id_interviews)

    await message.answer(
        f"Вы собираетесь удалить слот:\n\n"
        f"ID: {id_interviews}\nДата: {day}\nВремя: {time}\nТим-лидер: {recruiter}\n\n"
        f"Чтобы подтвердить удаление, напишите: Подтверждаю\n"
        f"Любой другой ответ отменит действие."
    )
    await state.set_state(AdminDeleteSlotStates.confirm)

@safe_handler
@dp.message(AdminDeleteSlotStates.confirm)
async def process_delete_confirm(message: Message, state: FSMContext):
    confirm_text = message.text.strip()
    data = await state.get_data()
    slot_id = data.get("slot_id")

    if confirm_text.lower() == "подтверждаю":
        async with aiosqlite.connect("data.db") as db:
            await db.execute("DELETE FROM interviews WHERE id_interviews = ?", (slot_id,))
            await db.commit()

        data = await state.get_data()
        id_interviews = data.get("id_interviews")
        day = data.get("day_interviews")
        time = data.get("time_interviews")
        recruiter = data.get("tg_id_recruiter_interviews")
        whole_delete_slot = (f"Слот ID: {id_interviews}\nДата: {day}\nВремя: {time}\nТим-лидер: {recruiter}\n\n Успешно удалён.")
        await message.answer(whole_delete_slot)
        await bot.send_message(-4822221970, whole_delete_slot)
    else:
        data = await state.get_data()
        id_interviews = data.get("id_interviews")
        day = data.get("day_interviews")
        time = data.get("time_interviews")
        recruiter = data.get("tg_id_recruiter_interviews")
        whole_notdelete_slot = (f"Удаление слота ID: {id_interviews}\nДата: {day}\nВремя: {time}\nТим-лидер: {recruiter}\n\n отменено.")
        await message.answer(whole_notdelete_slot)
        await bot.send_message(-4822221970, whole_notdelete_slot)

    await state.clear()



@safe_handler
@dp.message(Command("admin_get_info_interviews"))
async def cmd_get_info_interviews(message: types.Message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        await message.answer("Вы не админ")
        return

    async with aiosqlite.connect("data.db") as db:
        async with db.execute(
            """
            SELECT id_interviews, day_interviews, time_interviews, 
                   tg_id_volunteer_interviews, tg_id_recruiter_interviews, 
                   full_name_interviews
            FROM interviews
            """
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await message.answer("Данные отсутствуют")
        return

    grouped = {}
    for slot_id, day, time, tg_vol, tg_recruiter, full_name in rows:
        if day not in grouped:
            grouped[day] = []
        grouped[day].append((slot_id, time, tg_vol, tg_recruiter, full_name))

    formatted_days = []
    for day, slots in grouped.items():
        lines = []
        for slot_id, time, tg_vol, tg_recruiter, full_name in slots:
            recruiter_txt = tg_recruiter if tg_recruiter else "—"
            volunteer_txt = f"{full_name}, {tg_vol}" if full_name and tg_vol else "—"
            lines.append(
                f"ID {slot_id}: {time} "
                f"(Тим-лидер: {recruiter_txt}; Волонтер: {volunteer_txt})"
            )
        formatted_days.append(f"{day}:\n" + "\n".join(lines))

    formatted = "\n\n".join(formatted_days)
    await message.answer(formatted)



@safe_handler
@dp.message(Command("admin_get_info_feedbacks"))
async def cmd_get_info_feedbacks(message: types.Message):
    user_id = message.from_user.id
    if user_id not in admin_ids:
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



PHOTOS_PATH = Path(__file__).parent / "photos"
PHOTOS_PATH.mkdir(parents=True, exist_ok=True)

user_photo_info = {}

def _sanitize(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'[^\w\-@]', '_', s, flags=re.UNICODE)
    return s

@safe_handler
@dp.message(Command("images"))
async def cmd_images(message: Message):
    user_id = message.from_user.id
    user_photo_info[user_id] = {"step": "date"}
    await message.reply(
        "Чтобы загрузить «Фото-отчет» о мероприятии необходимо:\n\n"
        "1) Введи дату мероприятия (например: 2025-09-06).\n"
        "2) Введи название мероприятия.\n"
        "3) Затем прикрепи фотографии (отправляй их по одной).\n\n"
        "По возможности: фотографии должны быть отправлены как файлы, без сжатия!"
    )

@safe_handler
@dp.message(lambda m: m.from_user.id in user_photo_info and user_photo_info[m.from_user.id]["step"] == "date")
async def get_date(message: Message):
    user_id = message.from_user.id
    user_photo_info[user_id]["date_photo"] = message.text.strip()
    user_photo_info[user_id]["step"] = "event"
    await message.answer(" Дата сохранена.\n\nТеперь введи *название мероприятия*.")

@safe_handler
@dp.message(lambda m: m.from_user.id in user_photo_info and user_photo_info[m.from_user.id]["step"] == "event")
async def get_event_name(message: Message):
    user_id = message.from_user.id
    user_photo_info[user_id]["event_name_photo"] = message.text.strip()
    user_photo_info[user_id]["step"] = "photos"
    user_photo_info[user_id]["counter"] = 0
    await message.answer(" Название сохранено.\n\nТеперь можешь отправлять фотографии (по одной, как файл или фото).")

@safe_handler
@dp.message(F.photo | F.document)
async def download_files(message: Message, bot: Bot):
    user_id = message.from_user.id
    info = user_photo_info.get(user_id)

    if not info or info.get("step") != "photos":
        await message.answer(" Сначала используй команду /images и укажи дату и название мероприятия.")
        return

    username = message.from_user.username
    tg_id_photo = f"@{username}" if username else str(user_id)

    date_photo = _sanitize(info["date_photo"])
    event_name_photo = _sanitize(info["event_name_photo"])
    tg_id_safe = _sanitize(tg_id_photo)

    counter = info.get("counter", 0) + 1
    info["counter"] = counter

    if message.document:
        file_id = message.document.file_id
        orig_name = message.document.file_name or ""
        ext = Path(orig_name).suffix.lower() if Path(orig_name).suffix else ".jpeg"
    else:
        file_id = message.photo[-1].file_id
        ext = ".jpeg"

    filename = f"{date_photo}_{event_name_photo}_{tg_id_safe}_{counter}{ext}"
    file_path = PHOTOS_PATH / filename

    try:
        await bot.download(file_id, destination=file_path)
    except Exception as e:
        await message.answer(f"Ошибка при сохранении файла: {e}")
        return

    whole_message_file = f" Файл сохранён как:\n{filename}"
    await message.answer(whole_message_file)
    await bot.send_message(-4822221970, whole_message_file)

@safe_handler
@dp.message(Command("done"))
async def cmd_done(message: Message):
    user_id = message.from_user.id
    user_photo_info.pop(user_id, None)
    await message.answer(" Данные о текущем фото-отчёте удалены. При необходимости запусти /images заново.")



@safe_handler
@dp.message(Command("interviews"))
async def interviews_command(message: Message, state: FSMContext):
    await message.answer("Приступим к регистрации на интервью. Для начала напиши свои ФИО:")
    await state.set_state(InterviewStates.full_name_interviews)

@safe_handler
@dp.message(InterviewStates.full_name_interviews)
async def process_interview_full_name_feedbacks(message: Message, state: FSMContext):
    full_name_interviews = message.text.strip()
    await state.update_data(full_name_interviews=full_name_interviews)

    async with aiosqlite.connect("data.db") as db:
        async with db.execute(
            "SELECT id_interviews, day_interviews, time_interviews FROM interviews WHERE is_busy_interviews = '0'"
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await message.answer("К сожалению, свободных слотов нет.")
        await state.clear()
        return

    normalized = []
    for row in rows:
        if len(row) >= 3:
            slot_id, day, time = row[0], str(row[1] or ""), str(row[2] or "")
        elif len(row) == 2:
            slot_id = None
            day, time = str(row[0] or ""), str(row[1] or "")
        else:
            slot_id = row[0] if len(row) > 0 else None
            day = str(row[1]) if len(row) > 1 else ""
            time = str(row[2]) if len(row) > 2 else ""
        normalized.append((slot_id, day.strip(), time.strip()))

    extracted = []
    time_pattern = re.compile(r'\(?\s*(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})\s*\)?')
    trailing_time_pattern = re.compile(r'\s*-\s*\(?\s*\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}\s*\)?\s*$')
    for slot_id, day, time in normalized:
        if (not time or time == "") and day:
            m = time_pattern.search(day)
            if m:
                time = m.group(1)
                day = trailing_time_pattern.sub("", day).strip()
        time = time.strip().strip("() ")
        day = day.strip()
        extracted.append((slot_id, day, time))

    grouped = defaultdict(list)
    for slot_id, day, time in extracted:
        grouped[day].append((slot_id, time))

    def parse_day_key(day_str):
        m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})', day_str)
        if m:
            d, mo, y = m.groups()
            y = int(y)
            if y < 100:
                y += 2000
            try:
                return datetime(year=y, month=int(mo), day=int(d))
            except Exception:
                pass
        return datetime.max

    def parse_time_key(time_str):
        m = re.match(r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})', time_str)
        if m:
            sh, sm, eh, em = map(int, m.groups())
            return sh * 60 + sm
        return 10**9

    sorted_days = sorted(grouped.items(), key=lambda kv: parse_day_key(kv[0]))
    formatted_slots = []
    for day, items in sorted_days:
        items_sorted = sorted(items, key=lambda it: parse_time_key(it[1] or ""))
        lines = []
        for slot_id, t in items_sorted:
            id_part = f"({slot_id}) " if slot_id is not None else ""
            t_display = t if t else "не указано время"
            lines.append(f"— {id_part}{t_display}")
        day_display = day if day else "Не указана дата"
        formatted_slots.append(f"{day_display}:\n" + "\n".join(lines))

    itime_slots = "\n\n".join(formatted_slots)

    await message.answer(
        f"Привет, {full_name_interviews}! Вот свободные слоты для записи на интервью:\n\n"
        f"{itime_slots}\n\n"
        f"Пришли номер напротив временного слота, который тебя устраивает\n\n"
        f"Если ни один временной слот не подходит, жди обновления каждую субботу"
    )
    await state.set_state(InterviewStates.user_time_slot)

@safe_handler
@dp.message(InterviewStates.user_time_slot)
async def process_user_time(message: Message, state: FSMContext):
    user_time_slot = message.text.strip()
    await state.update_data(user_time_slot=user_time_slot)

    tg_id_volunteer_interviews = f"@{message.from_user.username}" if message.from_user.username else str(message.from_user.id)
    await state.update_data(tg_id_volunteer_interviews=tg_id_volunteer_interviews)

    data = await state.get_data()
    full_name_interviews = data["full_name_interviews"]

    async with aiosqlite.connect("data.db") as db:
        async with db.execute(
                "SELECT day_interviews, time_interviews, is_busy_interviews ""FROM interviews WHERE id_interviews = ?", (user_time_slot,),
        ) as cursor:
            slot = await cursor.fetchone()

        if not slot:
            await message.answer("Такого слота нет. Попробуй снова.")
            return

        day_interviews, time_interviews, is_busy = slot

        if is_busy == "1":
            await message.answer("Этот слот уже занят. Попробуй выбрать другой.")
            return

        await db.execute(
            "UPDATE interviews "
            "SET is_busy_interviews = '1', full_name_interviews = ?, tg_id_volunteer_interviews = ? "
            "WHERE id_interviews = ?",
            (full_name_interviews, tg_id_volunteer_interviews, user_time_slot),
        )
        await db.commit()

    whole_interview = (
        f"{tg_id_volunteer_interviews} записан на интервью, спасибо!\n\n"
        f"Итоговая запись:\n\n"
        f"Твои ФИО: {full_name_interviews}\n"
        f"Твое время: {day_interviews} — {time_interviews}\n\n"
        f"Обратите внимание: за 12 часов до начала собеседования изменить временной слот или записаться на новый не получится, если возникли вопросы, пиши - @Herrison_Kon\n"
        f" Место встречи неизменно: Добро.Центр (6к, 2 этаж, стеклянное пространство у ауд. 265)"
    )
    await message.answer(whole_interview)
    await bot.send_message(-4822221970, whole_interview)
    await state.clear()



@safe_handler
@dp.message(Command("feedback"))
async def feedback_command(message: Message, state: FSMContext):
    await message.answer(
        "Приступим к написанию отзыва.\n\nДля начала давай познакомимся?\n\n"
        "Напиши свое ФИО, чтобы в случае чего мы могли с тобой связаться!"
    )
    await state.set_state(FeedbackStates.full_name_feedbacks)

@safe_handler
@dp.message(FeedbackStates.full_name_feedbacks)
async def process_full_name_feedbacks(message: Message, state: FSMContext):
    full_name_feedbacks = message.text.strip()
    await state.update_data(full_name_feedbacks=full_name_feedbacks)
    await state.set_state(FeedbackStates.group_name_feedbacks)
    await message.answer(
        f"Супер. Рад познакомиться, {full_name_feedbacks}!\n\nТеперь, если ты студент Университета, пришли номер своей группы.\n\n"
        f"Например: 15.14Д-ЖУР01/25б\nЕсли не являешься студентом: '—'"
    )

@safe_handler
@dp.message(FeedbackStates.group_name_feedbacks)
async def process_group_name_feedbacks(message: Message, state: FSMContext):
    group_name_feedbacks = message.text.strip()
    await state.update_data(group_name_feedbacks=group_name_feedbacks)
    await state.set_state(FeedbackStates.event_name_feedbacks)
    await message.answer(
        f"Хорошо, теперь я знаю что ты из группы: {group_name_feedbacks}, "
        f"Напиши название мероприятия и дату, например:\n\n"
        f"'VIII Профессорский форум «Наука и образование», 18.11.2025'"
    )

@safe_handler
@dp.message(FeedbackStates.event_name_feedbacks)
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

@safe_handler
@dp.message(FeedbackStates.feedback_text_feedbacks)
async def process_feedback(message: Message, state: FSMContext):
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





@safe_handler
@dp.message(Command("test"))
async def any_message(message: Message):
    await message.answer("Hello, <b>world</b>!", parse_mode=ParseMode.HTML)
    await message.answer("Сообщение с <u>HTML-разметкой</u>")
    await message.answer("Сообщение без <s>какой-либо разметки</s>", parse_mode=None)



@safe_handler
@dp.message(Command("dice"))
async def cmd_dice(message: types.Message):
    await message.answer_dice(emoji="🎲")



@safe_handler
@dp.message(Command("info"))
async def cmd_info(message: types.Message, started_at: str):
    await message.answer(f"Бот запущен {started_at}")



@safe_handler
@dp.message(Command("chat_id"))
async def cmd_chat_id(message: Message):
    chat_id = message.chat.id
    await message.answer(f"Chat ID: `{chat_id}`", parse_mode="Markdown")





async def main():
    PHOTOS_PATH.mkdir(parents=True, exist_ok=True)
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())