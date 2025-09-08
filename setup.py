from pathlib import Path
from aiogram.types.message import Message





PHOTOS_PATH = Path(__file__).parent / "photos"



admin_ids = {301892352, 328168838, 763733398, 951008860, 5411845362, 753665396, 1378784301, 1825364517, 1224393478, 625056746, 1817275981, 1032264542, 944769569, 5690157353, 1575605738, 1342716925, 1691986075}
superadmin_ids = {763733398, 753665396}



async def is_superadmin(message: Message) -> bool:
    return message.from_user.id in superadmin_ids



async def is_admin(message: Message) -> bool:
    return message.from_user.id in admin_ids