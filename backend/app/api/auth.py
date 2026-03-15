from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from app.models.user import UserRegister, UserLogin, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.database import db_ctx

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
async def register(user: UserRegister):
    existing_user = await db_ctx.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_password = get_password_hash(user.password)
    new_user = {
        "email": user.email,
        "password_hash": hashed_password,
        "first_name": user.first_name,
        "created_at": datetime.now(timezone.utc)
    }
    await db_ctx.users.insert_one(new_user)
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    db_user = await db_ctx.users.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
