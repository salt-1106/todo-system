import logging
import traceback

# 配置日志，强制输出详细错误
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# backend/main.py - 完整的后端接口实现
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
import uvicorn
from datetime import timedelta

# 导入已实现的模块
from auth import AuthService
from models import UserCreate, TaskCreate
from services import UserService, TaskService
from database import DatabaseManager



# 初始化 FastAPI
app = FastAPI(title="SmartTodo API")

# 解决跨域问题（前端调用后端必须加）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源，生产环境指定前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
user_service = UserService()
task_service = TaskService()
db = DatabaseManager()


# 依赖项：验证 Token 获取当前用户
def get_current_user(token: str = Query(...)) -> Dict:
    """验证 Token 并返回当前用户"""
    payload = AuthService.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的 Token")
    user_id = payload.get("sub")
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


# 认证接口（登录/注册）
@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    """用户注册接口"""
    try:
        user_id = user_service.create_user(user_data)
        return JSONResponse(
            status_code=201,
            content={"message": "注册成功", "user_id": user_id}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")

@app.post("/api/auth/login")
async def login(username: str = Query(...), password: str = Query(...)):
    """用户登录接口"""
    # 验证用户
    user = user_service.authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 生成 Token（有效期1小时）
    access_token = AuthService.create_access_token(
        data={"sub": user["id"]},
        expires_delta=timedelta(hours=1)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }
    }


@app.post("/api/tasks")
async def create_task(
    task_data: TaskCreate,
    token: str = Query(...),
):
    """创建任务"""
    # 验证 Token
    try:
        user = get_current_user(token)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token验证失败")
    
    try:
        # 兼容前端字符串传参（容错处理）
        from models import Priority, TaskCategory
        
        # 优先级容错
        try:
            priority = Priority(task_data.priority.lower())
        except (ValueError, AttributeError):
            priority = Priority.MEDIUM  # 默认中优先级
        
        # 分类容错
        try:
            category = TaskCategory(task_data.category.lower())
        except (ValueError, AttributeError):
            category = TaskCategory.PERSONAL  # 默认个人分类
        
        # 重新构造TaskCreate对象（确保枚举类型正确）
        valid_task_data = TaskCreate(
            title=task_data.title.strip(),
            description=task_data.description.strip() if task_data.description else "",
            priority=priority,
            category=category,
            due_date=task_data.due_date
        )
        
        task = task_service.create_task(valid_task_data, user["id"])
        return JSONResponse(status_code=201, content=task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")
    except Exception as e:
        # 打印详细错误日志（方便调试）
        import traceback
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        logger.error(f"创建任务失败: {str(e)}", exc_info=True)
        print(f"创建任务异常: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


        

@app.get("/api/tasks")
async def get_tasks(
    token: str = Query(...),
    category: Optional[str] = None,
    # 新增：优先级筛选参数
    # priority: Optional[str] = None,
):
    """获取用户任务（支持分类过滤）"""
    user = get_current_user(token)
    tasks = task_service.get_user_tasks(
        user_id=user["id"],
        category=category,
        # priority=priority
    )
    return tasks

@app.put("/api/tasks/{task_id}/complete")
async def complete_task(
    task_id: int,
    token: str = Query(...),
):
    """标记任务为完成"""
    user = get_current_user(token)
    success = task_service.complete_task(task_id, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail="任务完成失败（可能任务不存在或不属于当前用户）")
    return {"message": "任务已完成"}

# 在 complete_task 接口后添加以下代码
@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: int,
    token: str = Query(...),
):
    """删除指定任务"""
    # 验证 Token 获取当前用户
    try:
        user = get_current_user(token)
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=401, detail="Token验证失败")
    
    # 执行删除
    success = task_service.delete_task(task_id, user["id"])
    if not success:
        raise HTTPException(status_code=400, detail="删除失败（任务不存在或不属于当前用户）")
    
    return {"message": "任务已成功删除"}
# ------------------------------
# 启动服务
# ------------------------------
if __name__ == "__main__":
    print("SmartTodo 后端服务启动中...")
    print("访问地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

