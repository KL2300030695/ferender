from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from app.core.config import settings
from app.core.database import db_ctx

def extract_token(request: Request):
    return request.headers.get("Authorization", "").replace("Bearer ", "")

async def get_current_user(token: str = Depends(extract_token)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None: return None
    except JWTError:
        return None
    
    if db_ctx.users is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
        
    user = await db_ctx.users.find_one({"email": email})
    if user is None: return None
    user["id"] = str(user["_id"])
    return user

async def require_user(current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return current_user
