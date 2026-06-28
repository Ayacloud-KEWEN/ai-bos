import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt

# 生产环境中，SECRET_KEY 必须放在 .env 文件中
SECRET_KEY = "aya_cloud_bos_super_secret_key_change_me_in_production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # Token 7天有效

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt 原生库需要处理 bytes 类型，因此需要 encode
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    # 生成盐值并加密
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    # 转换回字符串以便后续存入数据库
    return hashed_password.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    
    # 适配 Python 3.12+ 的时间标准，使用 timezone.utc
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt