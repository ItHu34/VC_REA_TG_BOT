import asyncio
from aiogram import Dispatcher
from aiogram.enums import ParseMode
from datetime import datetime
import logging
from aiogram import Bot
from conf_reader import config
from aiogram.client.default import DefaultBotProperties
import aiosqlite

from routers import all_routers
from setup import PHOTOS_PATH



dp = Dispatcher()
dp["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")



bot = Bot(
    token=config.bot_token.get_secret_value(),
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)



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
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS rating (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                hours_worked FLOAT DEFAULT 0
            )
        """)
        await connection.commit()



logging.basicConfig(level=logging.INFO)



bot = Bot(
    token=config.bot_token.get_secret_value(),
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)





for r in all_routers:
    dp.include_router(r)





async def main():
    PHOTOS_PATH.mkdir(parents=True, exist_ok=True)
    await init_db()
    await dp.start_polling(bot)





if __name__ == "__main__":
    asyncio.run(main())