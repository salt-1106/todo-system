from datetime import datetime 
import hashlib
import secrets
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from database import DatabaseManager, BaseDAO
from models import UserCreate, TaskCreate, TaskUpdate
from auth import AuthService

print("services.py 已加载")

#用户服务
class UserService:  
    
    def __init__(self):
        self.user_dao = BaseDAO("users")
        print("UserService 初始化完成")
    
    def create_user(self, user_data: UserCreate) -> int:
        """创建用户"""
        print(f"创建用户: {user_data.username}")
        
        # 检查用户名是否已存在
        existing = self.user_dao.get_all({"username": user_data.username})
        if existing:
            raise ValueError("用户名已存在")
        
        # 检查邮箱是否已存在
        existing = self.user_dao.get_all({"email": user_data.email})
        if existing:
            raise ValueError("邮箱已存在")
        
        # 哈希密码
        password_hash = AuthService.hash_password(user_data.password)
        
        # 创建用户
        user_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": password_hash
        }
        
        user_id = self.user_dao.create(user_dict)
        print(f"用户创建成功，ID: {user_id}")
        return user_id
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """用户认证"""
        users = self.user_dao.get_all({"username": username})
        if not users:
            print(f"用户不存在: {username}")
            return None
        
        user = users[0]
        if not AuthService.verify_password(password, user["password_hash"]):
            print("密码验证失败")
            return None
        
        print(f"用户认证成功: {username}")
        return user
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """根据ID获取用户"""
        return self.user_dao.get_by_id(user_id)

"""任务服务"""
class TaskService:
    
    def __init__(self):
        self.task_dao = BaseDAO("tasks")
        print("TaskService 初始化完成")

    """创建任务（彻底修复datetime错误）"""
    def create_task(self, task_data: "TaskCreate", user_id: int) -> Dict:
        
        print(f"创建任务: {task_data.title}")
        
        # 处理 due_date（兼容空值）
        due_date = task_data.due_date
        if due_date and isinstance(due_date, str):
            try:
                # 现在datetime是直接导入的，能正常使用
                parsed_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                due_date = parsed_date.isoformat()
            except:
                due_date = None  # 格式错就设为空
        
        # 处理枚举值（容错）
        priority_val = task_data.priority.value if hasattr(task_data.priority, 'value') else task_data.priority
        category_val = task_data.category.value if hasattr(task_data.category, 'value') else task_data.category
        
        # 重点：这里用datetime.utcnow()就对了（因为已经from datetime import datetime）
        task_dict = {
            "title": task_data.title.strip(),
            "description": task_data.description.strip() if task_data.description else "",
            "priority": priority_val,
            "category": category_val,
            "due_date": due_date,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),  # 现在能正常访问了
            "updated_at": datetime.utcnow().isoformat(),
            "is_completed": 0
        }
        
        try:
            task_id = self.task_dao.create(task_dict)
            task = self.task_dao.get_by_id(task_id)
            print(f"任务创建成功，ID: {task_id}")
            return task
        except Exception as e:
            print(f"创建任务失败: {str(e)}")
            raise
    def get_user_tasks(self, user_id: int, 
                      category: Optional[str] = None,
                      completed: Optional[bool] = None,
                      priority: Optional[str] = None) -> List[Dict]:
        """获取用户任务"""
        filters = {"user_id": user_id}
        if category:
            filters["category"] = category
        if completed is not None:
            filters["is_completed"] = 1 if completed else 0
        if priority:
            filters["priority"] = priority
        
        tasks = self.task_dao.get_all(filters, order_by="created_at DESC")
        print(f"获取用户 {user_id} 的任务，数量: {len(tasks)}")
        return tasks
    """完成任务"""    
    def complete_task(self, task_id: int, user_id: int) -> bool:
        
        update_data = {
            "is_completed": 1,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # 验证任务所有权并更新
        query = "UPDATE tasks SET is_completed = ?, updated_at = ? WHERE id = ? AND user_id = ?"
        db = DatabaseManager()
        affected = db.execute_update(query, (1, datetime.utcnow().isoformat(), task_id, user_id))
        
        success = affected > 0
        if success:
            print(f"完成任务 ID: {task_id}")
        else:
            print(f"完成任务失败 ID: {task_id}")
        
        return success

   
    def delete_task(self, task_id: int, user_id: int) -> bool:
        """删除任务（验证任务归属）"""
        # 先检查任务是否存在且属于当前用户
        task = self.task_dao.get_by_id(task_id)
        if not task or task["user_id"] != user_id:
            print(f"删除任务失败：任务不存在或不属于用户 {user_id}")
            return False
        
        # 执行删除
        success = self.task_dao.delete(task_id)
        if success:
            print(f"删除任务成功 ID: {task_id}")
        else:
            print(f"删除任务失败 ID: {task_id}")
        
        return success
# 测试代码
if __name__ == "__main__":
    print("测试服务层...")
    user_service = UserService()
    task_service = TaskService()
    print("服务层测试通过")