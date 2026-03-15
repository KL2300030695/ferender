from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None
    users = None
    sessions = None

db_ctx = Database()

async def connect_to_mongo():
    db_ctx.client = AsyncIOMotorClient(settings.MONGO_URI)
    db_ctx.db = db_ctx.client[settings.DB_NAME]
    db_ctx.users = db_ctx.db["users"]
    db_ctx.sessions = db_ctx.db["sessions"]

async def close_mongo_connection():
    if db_ctx.client is not None:
        db_ctx.client.close()
