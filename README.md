# VC_REA_TG_BOT
## Общее описание

Телеграм-бот для **Волонтёрского центра РЭУ**, помогающий:
•	собирать фото-отчёты о мероприятиях;
•	принимать отзывы в удобном формате;
•	записывать волонтёров на интервью по свободным слотам;
•	предоставлять админ-инструменты для управления слотами и выгрузки данных.

Бот использует FSM для диалоговых сценариев, _SQLite_ (через _aiosqlite_) для хранения, а также простую систему прав администраторов по списку _admin_ids_.

## Быстрый старт

Клонирование и окружение
```
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U aiogram aiosqlite pydantic python-dotenv
```

Конфигурация
Создайте conf_reader.py (если его нет) со считыванием токена из переменных окружения/.env:

```
# conf_reader.py (пример)
from pydantic import BaseSettings, SecretStr

class Settings(BaseSettings):
    bot_token: SecretStr

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

config = Settings()
```

.env:
```
BOT_TOKEN=123456:ABC-DEF...
```

Запуск
```
python bot.py
```

При первом запуске создастся база data.db и каталог photos.
