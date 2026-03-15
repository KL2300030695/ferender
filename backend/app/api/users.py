from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from app.models.session import SessionData
from app.api.dependencies import require_user
from app.core.database import db_ctx

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
async def read_users_me(current_user: dict = Depends(require_user)):
    return {"email": current_user["email"], "first_name": current_user["first_name"], "id": current_user["id"]}

@router.post("/me/sessions")
async def save_session(session: SessionData, current_user: dict = Depends(require_user)):
    session_dict = session.model_dump()
    session_dict["user_id"] = current_user["id"]
    session_dict["created_at"] = datetime.now(timezone.utc)
    await db_ctx.sessions.insert_one(session_dict)
    return {"status": "success"}

@router.get("/me/sessions")
async def get_sessions(current_user: dict = Depends(require_user)):
    sessions = []
    cursor = db_ctx.sessions.find({"user_id": current_user["id"]}).sort("created_at", -1)
    async for s in cursor:
        s["id"] = str(s["_id"])
        del s["_id"]
        sessions.append(s)
    return sessions
