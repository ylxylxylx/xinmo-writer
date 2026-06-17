"""生成空数据库（仅含表结构，无数据）"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from novel.models import init_db, DB_PATH

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"已删除旧库: {DB_PATH}")
    
    init_db()
    size = os.path.getsize(DB_PATH)
    print(f"已创建空库: {DB_PATH} ({size} bytes)")
