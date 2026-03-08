from pydantic import BaseModel, Field, validator
from typing import Optional
from enum import Enum
import re

print("models.py 已加载")

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskCategory(str, Enum):
    WORK = "work"
    PERSONAL = "personal"
    SHOPPING = "shopping"
    HEALTH = "health"
    LEARNING = "learning"

# 用户相关模型
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=6)
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        # 简单的邮箱格式验证（避免使用 EmailStr）
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', v):
            raise ValueError('邮箱格式不正确')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        return v

# 任务相关模型
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    category: TaskCategory = TaskCategory.PERSONAL
    due_date: Optional[str] = None  # 改为字符串，避免 datetime 解析问题

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_completed: Optional[bool] = None
    priority: Optional[Priority] = None
    category: Optional[TaskCategory] = None
    due_date: Optional[str] = None