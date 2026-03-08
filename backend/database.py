import sqlite3
import threading
from contextlib import contextmanager
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

print("database.py 已加载")

#数据库管理器
class DatabaseManager:

    #单例     
    _instance = None
    _lock = threading.Lock() #线程锁
    
    def __new__(cls):
        with cls._lock: #加锁 防止多线程冲突
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_db() #创建实例 数据库初始化
            return cls._instance
    
    #初始化数据库
    def _init_db(self):
        
        self.db_path = "smart_todo.db"  #路径
        print(f"数据库路径: {self.db_path}")
        self._create_tables() #初始化表
    
    #创建表
    def _create_tables(self):
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # 任务表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    is_completed BOOLEAN DEFAULT 0,
                    priority TEXT DEFAULT 'medium',
                    category TEXT DEFAULT 'personal',
                    due_date TIMESTAMP,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            #创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)')
            
            conn.commit()
            print("数据库表创建完成")
    
    #获取数据库连接
    @contextmanager
    def get_connection(self):
        
        conn = sqlite3.connect(self.db_path) #连接数据库
        conn.row_factory = sqlite3.Row 

        try:
            yield conn 
        except Exception as e:
            conn.rollback()
            print(f"数据库错误: {e}")
            raise
        finally:
            conn.close()
    
    #执行查询 
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        
        with self.get_connection() as conn: #获取数据库链接
            cursor = conn.cursor() #创建游标
            cursor.execute(query, params) #执行查询
            result = cursor.fetchall() #获取查询结果
            return [dict(row) for row in result] 
    
    #执行更新
    def execute_update(self, query: str, params: tuple = ()) -> int:
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params) #更新
            conn.commit() #提交事务
            return cursor.rowcount 
    
#数据访问对象
class BaseDAO:    
    
    def __init__(self, table_name: str): #初始化 绑定对应数据表
        self.db = DatabaseManager() 
        self.table_name = table_name

    
    #创建记录
    def create(self, data: Dict) -> int:
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        
        #在同一个连接中执行插入并获取ID
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(data.values()))
            conn.commit()
            #同一个连接中获取last_insert_rowid 
            cursor.execute("SELECT last_insert_rowid()")
            last_id = cursor.fetchone()[0]
        return last_id
    
    #根据ID获取记录
    def get_by_id(self, record_id: int) -> Optional[Dict]:
        
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"
        result = self.db.execute_query(query, (record_id,))
        return result[0] if result else None
    
    #更新记录
    def update(self, record_id: int, data: Dict) -> bool:
        
        if not data:
            return False
        
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
        
        params = tuple(data.values()) + (record_id,)
        affected = self.db.execute_update(query, params)
        return affected > 0
    
    #删除记录
    def delete(self, record_id: int) -> bool:
        
        query = f"DELETE FROM {self.table_name} WHERE id = ?"
        affected = self.db.execute_update(query, (record_id,))
        return affected > 0
    
    #获取所有记录
    def get_all(self, filters: Dict = None, order_by: str = None) -> List[Dict]:
        
        query = f"SELECT * FROM {self.table_name}"
        params = []
        
        if filters:
            conditions = []
            for key, value in filters.items():
                if value is not None:
                    conditions.append(f"{key} = ?")
                    params.append(value)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        return self.db.execute_query(query, tuple(params))

#测试数据库连接
if __name__ == "__main__":
    db = DatabaseManager()
    print("数据库管理器测试通过")