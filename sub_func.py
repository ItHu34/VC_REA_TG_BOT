from aiogram import types, Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command



sub_func_router = Router()





@sub_func_router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        " Привет, друг! Я — бот Волонтерского центра РЭУ. Помогаю делать добро легче и популярнее\n\n"
        "Какой у тебя вопрос?\n\n"
        "Для отправки фотографий с мероприятия, напиши: /images\n"
        "Для отправки отзыва о мероприятии, напиши: /feedback\n"
        "Для записи на интервью на Волонтера Плехановки, напиши: /interviews\n"
        "Для просмотра рейтинга Волонтеров Плехановки, напиши, /rating"
    )



@sub_func_router.message(Command("test"))
async def any_message(message: Message):
    await message.answer("Hello, <b>world</b>!", parse_mode=ParseMode.HTML)
    await message.answer("Сообщение с <u>HTML-разметкой</u>")
    await message.answer("Сообщение без <s>какой-либо разметки</s>", parse_mode=None)



@sub_func_router.message(Command("dice"))
async def cmd_dice(message: types.Message):
    await message.answer_dice(emoji="🎲")



@sub_func_router.message(Command("info"))
async def cmd_info(message: types.Message, started_at: str):
    await message.answer(f"Бот запущен {started_at}")



@sub_func_router.message(Command("chat_id"))
async def cmd_chat_id(message: Message):
    chat_id = message.chat.id
    await message.answer(f"Chat ID: `{chat_id}`", parse_mode="Markdown")