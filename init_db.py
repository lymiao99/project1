from sqlalchemy import create_engine, text
import urllib.parse
import os
from dotenv import load_dotenv

load_dotenv()

# Supabase 連線資訊 (從 .env 讀取)
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

encoded_pass = urllib.parse.quote_plus(DB_PASS)
DB_URL = f"postgresql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

def init_user_info():
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS user_info (
        id SERIAL PRIMARY KEY,
        acct_no TEXT UNIQUE NOT NULL,
        pwds TEXT NOT NULL,
        acct_name TEXT,
        role TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_by TEXT,
        last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        last_updated_by TEXT
    );
    """
    
    # 先嘗試增加欄位（如果表已存在）
    alter_table_sql_1 = "ALTER TABLE user_info ADD COLUMN IF NOT EXISTS acct_name TEXT;"
    alter_table_sql_2 = "ALTER TABLE user_info ADD COLUMN IF NOT EXISTS role TEXT;"

    insert_data_sql = """
    INSERT INTO user_info (acct_no, pwds, acct_name, role) 
    VALUES 
        ('admin001', 'admin123', '最高管理員', 'ADMIN'),
        ('mgr001', 'mgr123', '經理人', 'MANAGER'),
        ('tl001', 'tl123', '組長', 'TEAM_LEADER'),
        ('MGR002', 'admin123', '管理者', '系統管理員')
    ON CONFLICT (acct_no) DO UPDATE SET 
        acct_name = EXCLUDED.acct_name, 
        role = EXCLUDED.role;
    """
    
    try:
        with engine.connect() as conn:
            print("正在確保 user_info 資料表結構正確...")
            conn.execute(text(create_table_sql))
            conn.execute(text(alter_table_sql_1))
            conn.execute(text(alter_table_sql_2))
            print("正在更新測試帳號資訊...")
            conn.execute(text(insert_data_sql))
            conn.commit()
            print("成功！資料表已更新，測試帳號 MGR002 已具備姓名與角色。")
    except Exception as e:
        print(f"初始化失敗: {e}")

if __name__ == "__main__":
    init_user_info()
