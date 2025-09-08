from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import aiosqlite
from aiogram.filters import Command
from setup import is_superadmin


rating_router = Router()



class AddVolunteer(StatesGroup):
    waiting_full_name = State()

class AddHours(StatesGroup):
    waiting_id = State()
    waiting_hours = State()

class DeleteVolunteer(StatesGroup):
    waiting_id = State()
    waiting_confirm = State()

class DeleteHours(StatesGroup):
    waiting_id = State()
    waiting_hours = State()





async def format_table(with_id=True):
    async with aiosqlite.connect("data.db") as db:
        cursor = await db.execute("SELECT * FROM rating ORDER BY hours_worked DESC")
        rows = await cursor.fetchall()
    if not rows:
        return "Таблица пуста"
    result = []
    for row in rows:
        if with_id:
            result.append(f"ID: {row[0]} | {row[1]}, Часы: {row[2]}")
        else:
            result.append(f"{row[1]} | Часы: {row[2]}")
    return "\n".join(result)

def split_text_into_chunks(text: str, limit: int = 4096):
    if not text:
        return
    lines = text.splitlines(keepends=True)
    chunk = ""
    for line in lines:
        # если добавление строки превысит лимит — отдаём текущий кусок
        if len(chunk) + len(line) > limit:
            if chunk:
                yield chunk
            # если сама строка длиннее лимита — режем её по символам
            if len(line) > limit:
                for i in range(0, len(line), limit):
                    yield line[i:i+limit]
                chunk = ""
            else:
                chunk = line
        else:
            chunk += line
    if chunk:
        yield chunk

async def send_long_message(message: Message, text: str, limit: int = 4096):
    for part in split_text_into_chunks(text, limit):
        await message.answer(part)




@rating_router.message(Command("superadmin_add_volunteer"))
async def cmd_add_volunteer(message: Message, state: FSMContext):
    if not await is_superadmin(message):
        return await message.answer("Вы не суперадмин")
    await state.set_state(AddVolunteer.waiting_full_name)
    await message.answer("Введите ФИО волонтёра:")


@rating_router.message(AddVolunteer.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    async with aiosqlite.connect("data.db") as db:
        await db.execute("INSERT INTO rating (full_name) VALUES (?)", (full_name,))
        await db.commit()
    await state.clear()
    await message.answer("Волонтёр успешно добавлен!")



@rating_router.message(Command("superadmin_add_hours"))
async def cmd_add_hours(message: Message, state: FSMContext):
    if not await is_superadmin(message):
        return await message.answer("Вы не суперадмин")
    table = await format_table()
    await state.set_state(AddHours.waiting_id)
    header = "Текущий рейтинг:\n"
    await send_long_message(message, header + table)
    await message.answer("Введите ID волонтёра:")


@rating_router.message(AddHours.waiting_id)
async def process_add_hours_id(message: Message, state: FSMContext):
    await state.update_data(volunteer_id=message.text)
    await state.set_state(AddHours.waiting_hours)
    await message.answer("Введите количество часов:")


@rating_router.message(AddHours.waiting_hours)
async def process_add_hours(message: Message, state: FSMContext):
    data = await state.get_data()
    volunteer_id = int(data["volunteer_id"])
    hours = int(message.text)
    async with aiosqlite.connect("data.db") as db:
        cursor = await db.execute("SELECT * FROM rating WHERE id = ?", (volunteer_id,))
        row = await cursor.fetchone()
        if not row:
            return await message.answer("Волонтёр не найден")
        new_hours = row[2] + hours
        await db.execute("UPDATE rating SET hours_worked = ? WHERE id = ?", (new_hours, volunteer_id))
        await db.commit()
    await state.clear()
    await message.answer(f"Обновлено: {row[1]}, Часы: {new_hours}")



@rating_router.message(Command("superadmin_delete_volunteer"))
async def cmd_delete_volunteer(message: Message, state: FSMContext):
    if not await is_superadmin(message):
        return await message.answer("Вы не суперадмин")
    table = await format_table()
    await state.set_state(DeleteVolunteer.waiting_id)
    header = "Текущий рейтинг:\n"
    await send_long_message(message, header + table)
    await message.answer("Введите ID волонтёра для удаления:")


@rating_router.message(DeleteVolunteer.waiting_id)
async def process_delete_id(message: Message, state: FSMContext):
    await state.update_data(volunteer_id=message.text)
    await state.set_state(DeleteVolunteer.waiting_confirm)
    await message.answer("Подтвердите удаление, напишите 'Да' или 'Нет'")


@rating_router.message(DeleteVolunteer.waiting_confirm)
async def process_delete_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    volunteer_id = int(data["volunteer_id"])
    if message.text.lower() != "да":
        await state.clear()
        return await message.answer("Удаление отменено")
    async with aiosqlite.connect("data.db") as db:
        cursor = await db.execute("SELECT * FROM rating WHERE id = ?", (volunteer_id,))
        row = await cursor.fetchone()
        if not row:
            return await message.answer("Волонтёр не найден")
        await db.execute("DELETE FROM rating WHERE id = ?", (volunteer_id,))
        await db.commit()
    await state.clear()
    await message.answer(f"Успешно удалено: {row[1]}, Часы: {row[2]}")



@rating_router.message(Command("superadmin_delete_hours"))
async def cmd_delete_hours(message: Message, state: FSMContext):
    if not await is_superadmin(message):
        return await message.answer("Вы не суперадмин")
    table = await format_table()
    await state.set_state(DeleteHours.waiting_id)
    header = "Текущий рейтинг:\n"
    await send_long_message(message, header + table)


@rating_router.message(DeleteHours.waiting_id)
async def process_delete_hours_id(message: Message, state: FSMContext):
    await state.update_data(volunteer_id=message.text)
    await state.set_state(DeleteHours.waiting_hours)
    await message.answer("Введите количество часов для вычитания:")


@rating_router.message(DeleteHours.waiting_hours)
async def process_delete_hours(message: Message, state: FSMContext):
    data = await state.get_data()
    volunteer_id = int(data["volunteer_id"])
    hours = int(message.text)
    async with aiosqlite.connect("data.db") as db:
        cursor = await db.execute("SELECT * FROM rating WHERE id = ?", (volunteer_id,))
        row = await cursor.fetchone()
        if not row:
            return await message.answer("Волонтёр не найден")
        new_hours = max(0, row[2] - hours)
        await db.execute("UPDATE rating SET hours_worked = ? WHERE id = ?", (new_hours, volunteer_id))
        await db.commit()
    await state.clear()
    await message.answer(f"Обновлено: {row[1]}, Часы: {new_hours}")



@rating_router.message(Command("superadmin_get_info_rating"))
async def cmd_get_info(message: Message):
    if not await is_superadmin(message):
        return await message.answer("Вы не суперадмин")
    table = await format_table()
    header = "Текущий рейтинг:\n"
    await send_long_message(message, header + table)


@rating_router.message(Command("rating"))
async def cmd_rating(message: Message):
    table = await format_table(with_id=False)
    header = "Рейтинг волонтёров:\n"
    await send_long_message(message, header + table)