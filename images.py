import re
from aiogram import Bot, F, Router
from aiogram.types import Message
from aiogram.filters import Command
from pathlib import Path
from setup import PHOTOS_PATH



image_router = Router()
user_photo_info = {}



def _sanitize(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'[^\w\-@]', '_', s, flags=re.UNICODE)
    return s





@image_router.message(Command("images"))
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


@image_router.message(lambda m: m.from_user.id in user_photo_info and user_photo_info[m.from_user.id]["step"] == "date")
async def process_get_date(message: Message):
    user_id = message.from_user.id
    user_photo_info[user_id]["date_photo"] = message.text.strip()
    user_photo_info[user_id]["step"] = "event"
    await message.answer(" Дата сохранена.\n\nТеперь введи *название мероприятия*.")


@image_router.message(lambda m: m.from_user.id in user_photo_info and user_photo_info[m.from_user.id]["step"] == "event")
async def procees_get_event_name(message: Message):
    user_id = message.from_user.id
    user_photo_info[user_id]["event_name_photo"] = message.text.strip()
    user_photo_info[user_id]["step"] = "photos"
    user_photo_info[user_id]["counter"] = 0
    await message.answer(" Название сохранено.\n\nТеперь можешь отправлять фотографии (по одной, как файл или фото).")


@image_router.message(F.photo | F.document)
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



@image_router.message(Command("done"))
async def cmd_done(message: Message):
    user_id = message.from_user.id
    user_photo_info.pop(user_id, None)
    await message.answer(" Данные о текущем фото-отчёте удалены. При необходимости запусти /images заново.")