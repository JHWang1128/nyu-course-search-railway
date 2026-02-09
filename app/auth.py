
import os
import secrets
from datetime import datetime, timedelta, timezone
import resend
from jose import jwt
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, AppConfig, VerificationToken

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "").split(",")

def get_resend_api_key(db: Session):
    # Check env var first
    key = os.getenv("RESEND_API_KEY")
    if key:
        return key
    # Check DB config
    config = db.query(AppConfig).filter(AppConfig.key == "RESEND_API_KEY").first()
    if config:
        return config.value
    return None

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def send_otp(email: str, db: Session):
    if not email.endswith("@nyu.edu") and email not in ADMIN_EMAILS:
        # Check against admin list just in case
        return {"error": "Only @nyu.edu emails are allowed."}

    # Generate OTP
    otp = secrets.token_hex(3)
    # Expires in 15 mins - use naive UTC for consistency with DB storage
    expires = datetime.utcnow() + timedelta(minutes=15)
    
    # Store in DB (upsert)
    token_entry = db.query(VerificationToken).filter(VerificationToken.email == email).first()
    if token_entry:
        token_entry.token = otp
        token_entry.expires_at = expires
    else:
        token_entry = VerificationToken(email=email, token=otp, expires_at=expires)
        db.add(token_entry)
            
    db.commit()

    api_key = get_resend_api_key(db)
    
    # Dev mode if no key
    if not api_key:
        print(f"DEV MODE: OTP for {email} is {otp}")
        return {"message": f"DEV MODE: OTP sent (check console)."}

    resend.api_key = api_key
    try:
        r = resend.Emails.send({
            "from": "NYU Course Search <onboarding@resend.dev>",
            "to": email,
            "subject": "Your Login OTP",
            "html": f"<p>Your login code is: <strong>{otp}</strong></p><p>It expires in 15 minutes.</p>"
        })
        print(f"Resend response: {r}")
        return {"message": "OTP sent. Please check your email."}
    except Exception as e:
        print(f"Resend Error: {e}")
        return {"error": "Failed to send email. Please try again later."}

def verify_otp(email: str, otp: str, db: Session):
    token_entry = db.query(VerificationToken).filter(VerificationToken.email == email).first()
    
    if token_entry and token_entry.token == otp:
        # Use naive UTC for comparison (consistent with storage)
        now = datetime.utcnow()
        
        expires_at = token_entry.expires_at
        # Strip timezone if present for consistent comparison
        if expires_at.tzinfo:
            expires_at = expires_at.replace(tzinfo=None)
            
        if expires_at > now:
            # Valid
            db.delete(token_entry)
            db.commit()
            
            # Get/Create User
            user = db.query(User).filter(User.email == email).first()
            if not user:
                is_admin = (email in ADMIN_EMAILS)
                user = User(email=email, is_verified=True, is_admin=is_admin)
                db.add(user)
                db.commit()
                db.refresh(user)
            
            # Return token
            access_token = create_access_token(data={"sub": user.email, "admin": user.is_admin})
            return access_token
    
    return None
