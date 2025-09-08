import aiosqlite
import re
from aiogram import Bot, types, Router
from datetime import datetime
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from collections import defaultdict
from setup import is_admin



interview_router = Router()



class InterviewStates(StatesGroup):
    full_name_interviews = State()
    user_time_slot = State()


class AdminAddSlotStates(StatesGroup):
    day_interviews = State()
    time_interviews = State()
    tg_id_recruiter_interviews = State()


class AdminDeleteSlotStates(StatesGroup):
    id_interviews = State()
    confirm = State()





@interview_router.message(Command("admin_add_slot"))
async def cmd_admin_add_slot(message: Message, state: FSMContext):
    if not await is_admin(message):
        await message.answer("Вы не админ")
        return
    await message.answer("Введите дату проведения интервью (например: 08.09.2025 - понедельник):")
    await state.set_state(AdminAddSlotStates.day_interviews)


@interview_router.message(AdminAddSlotStates.day_interviews)
async def process_admin_add_day(message: Message, state: FSMContext):
    await state.update_data(day_interviews=message.text.strip())
    await message.answer("Теперь введите время проведения интервью (например: 12:30-12:50):")
    await state.set_state(AdminAddSlotStates.time_interviews)


@interview_router.message(AdminAddSlotStates.time_interviews)
async def process_admin_add_time(message: Message, state: FSMContext):
    await state.update_data(time_interviews=message.text.strip())
    await message.answer("Введите tg_id тим-лидера (например: @nickname):")
    await state.set_state(AdminAddSlotStates.tg_id_recruiter_interviews)


@interview_router.message(AdminAddSlotStates.tg_id_recruiter_interviews)
async def process_admin_add_recruiter(message: Message, state: FSMContext, bot: Bot):
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



@interview_router.message(Command("admin_delete_slot"))
async def cmd_admin_delete_slot(message: Message, state: FSMContext):
    if not await is_admin(message):
        await message.answer("Вы не админ")
        return
    if not await is_admin(message):
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
    for id_interviews, day, time, tg_vol, tg_recruiter, full_name in rows:
        if day not in grouped:
            grouped[day] = []
        grouped[day].append((id_interviews, time, tg_vol, tg_recruiter, full_name))
    formatted_days = []
    for day, slots in grouped.items():
        lines = []
        for id_interviews, time, tg_vol, tg_recruiter, full_name in slots:
            recruiter_txt = tg_recruiter if tg_recruiter else "—"
            volunteer_txt = f"{full_name}, {tg_vol}" if full_name and tg_vol else "—"
            lines.append(
                f"ID {id_interviews}: {time} "
                f"(Тим-лидер: {recruiter_txt}; Волонтер: {volunteer_txt})"
            )
        formatted_days.append(f"{day}:\n" + "\n".join(lines))
    formatted = "\n\n".join(formatted_days)
    await message.answer(formatted)
    await message.answer("Введите ID временного слота, который хотите удалить:")
    await state.set_state(AdminDeleteSlotStates.id_interviews)



@interview_router.message(AdminDeleteSlotStates.id_interviews)
async def process_delete_id_interviews(message: Message, state: FSMContext):
    id_interviews = message.text.strip()
    async with aiosqlite.connect("data.db") as db:
        async with db.execute(
            "SELECT id_interviews, day_interviews, time_interviews, tg_id_recruiter_interviews "
            "FROM interviews WHERE id_interviews = ?", (id_interviews,)
        ) as cursor:
            slot = await cursor.fetchone()
    if not slot:
        await message.answer("Слот с таким ID не найден. Попробуйте снова.")
        await state.clear()
        return
    id_interviews, day, time, recruiter = slot
    await state.update_data(id_interviews=id_interviews, day=day, time=time, recruiter=recruiter)
    await message.answer(
        f"Вы собираетесь удалить слот:\n\n"
        f"ID: {id_interviews}\nДата: {day}\nВремя: {time}\nТим-лидер: {recruiter}\n\n"
        f"Чтобы подтвердить удаление, напишите: Подтверждаю\n"
        f"Любой другой ответ отменит действие."
    )
    await state.set_state(AdminDeleteSlotStates.confirm)



@interview_router.message(AdminDeleteSlotStates.confirm)
async def process_delete_confirm(message: Message, state: FSMContext, bot: Bot):
    confirm_text = message.text.strip()
    data = await state.get_data()
    id_interviews = data.get("id_interviews")
    day = data.get("day")
    time = data.get("time")
    recruiter = data.get("recruiter")
    if confirm_text.lower() == "подтверждаю":
        async with aiosqlite.connect("data.db") as db:
            await db.execute("DELETE FROM interviews WHERE id_interviews = ?", (id_interviews,))
            await db.commit()
        whole_delete_slot = (f"Слот ID: {id_interviews}\nДата: {day}\nВремя: {time}\nТим-лидер: {recruiter}\n\n Успешно удалён.")
        await message.answer(whole_delete_slot)
        await bot.send_message(-4822221970, whole_delete_slot)
    else:
        whole_notdelete_slot = (f"Удаление слота ID: {id_interviews}\nДата: {day}\nВремя: {time}\nТим-лидер: {recruiter}\n\n отменено.")
        await message.answer(whole_notdelete_slot)
        await bot.send_message(-4822221970, whole_notdelete_slot)
    await state.clear()



@interview_router.message(Command("admin_get_info_interviews"))
async def cmd_admin_get_info_interviews(message: types.Message):
    if not await is_admin(message):
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
    for id_interviews, day, time, tg_vol, tg_recruiter, full_name in rows:
        if day not in grouped:
            grouped[day] = []
        grouped[day].append((id_interviews, time, tg_vol, tg_recruiter, full_name))
    formatted_days = []
    for day, slots in grouped.items():
        lines = []
        for id_interviews, time, tg_vol, tg_recruiter, full_name in slots:
            recruiter_txt = tg_recruiter if tg_recruiter else "—"
            volunteer_txt = f"{full_name}, {tg_vol}" if full_name and tg_vol else "—"
            lines.append(
                f"ID {id_interviews}: {time} "
                f"(Тим-лидер: {recruiter_txt}; Волонтер: {volunteer_txt})"
            )
        formatted_days.append(f"{day}:\n" + "\n".join(lines))
    formatted = "\n\n".join(formatted_days)
    await message.answer(formatted)



@interview_router.message(Command("interviews"))
async def interviews_command(message: Message, state: FSMContext):
    await message.answer("Приступим к регистрации на интервью. Для начала напиши свои ФИО:")
    await state.set_state(InterviewStates.full_name_interviews)



@interview_router.message(InterviewStates.full_name_interviews)
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
            id_interviews, day, time = row[0], str(row[1] or ""), str(row[2] or "")
        elif len(row) == 2:
            id_interviews = None
            day, time = str(row[0] or ""), str(row[1] or "")
        else:
            id_interviews = row[0] if len(row) > 0 else None
            day = str(row[1]) if len(row) > 1 else ""
            time = str(row[2]) if len(row) > 2 else ""
        normalized.append((id_interviews, day.strip(), time.strip()))
    extracted = []
    time_pattern = re.compile(r'\(?\s*(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})\s*\)?')
    trailing_time_pattern = re.compile(r'\s*-\s*\(?\s*\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}\s*\)?\s*$')
    for id_interviews, day, time in normalized:
        if (not time or time == "") and day:
            m = time_pattern.search(day)
            if m:
                time = m.group(1)
                day = trailing_time_pattern.sub("", day).strip()
        time = time.strip().strip("() ")
        day = day.strip()
        extracted.append((id_interviews, day, time))
    grouped = defaultdict(list)
    for id_interviews, day, time in extracted:
        grouped[day].append((id_interviews, time))
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
        for id_interviews, t in items_sorted:
            id_part = f"({id_interviews}) " if id_interviews is not None else ""
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



@interview_router.message(InterviewStates.user_time_slot)
async def process_user_time(message: Message, state: FSMContext, bot: Bot):
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