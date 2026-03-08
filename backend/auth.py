import hashlib
import secrets
from typing import Optional, Dict
from datetime import datetime, timedelta
import jwt

print("auth.py 已加载")

class AuthService:
    
    #认证服务
    SECRET_KEY = "development-secret-key-change-in-production"
    ALGORITHM = "HS256"

    #明文密码转哈希密码
    @staticmethod
    def hash_password(password: str) -> str:
       
        salt = secrets.token_hex(16)  #secrets库生成随机值，避免两用户密码相同生产相同哈希值
        #哈希明文密码
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'), #转字节
            salt.encode('utf-8'),  
            100000    #迭代次数
        ).hex()
        return f"{salt}${password_hash}" #链接
    
    #验证密码
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        
        try:
            if not hashed_password or '$' not in hashed_password:
                return False
            salt, stored_hash = hashed_password.split('$')  #加密密码拆分
            #重新哈希明文密码
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            ).hex()
            return password_hash == stored_hash #对比新哈希密码与存储哈希密码一致性
        except Exception:
            return False
    
    #生成访问令牌（用户id、过期时间；密钥加密），返回给前端
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        
        to_encode = data.copy() #复制传入的数据
        if expires_delta:  #设置令牌过期时间
            expire = datetime.utcnow() + expires_delta  
        else:
            expire = datetime.utcnow() + timedelta(minutes=15) #设置令牌过期时间
        to_encode.update({"exp": expire}) #过期时间存入令牌
        encoded_jwt = jwt.encode(to_encode, AuthService.SECRET_KEY, algorithm=AuthService.ALGORITHM) #头部 负载
        return encoded_jwt #返回加密后的令牌字符串
    
    #验证后端接收到的前端返回的令牌
    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        
        try:
            payload = jwt.decode(token, AuthService.SECRET_KEY, algorithms=[AuthService.ALGORITHM]) #
            return payload
        except jwt.PyJWTError:
            return None