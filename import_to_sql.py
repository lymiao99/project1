import pandas as pd
from sqlalchemy import create_engine
import urllib.parse
import os
from dotenv import load_dotenv

load_dotenv()

# 路徑與連線設定
#CSV_PATH = 'models/ai 2020.csv'
CSV_PATH = 'models/test_data.csv'
TABLE_NAME = 'maintenance'

# Supabase 連線資訊 (從 .env 讀取)
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# 對密碼進行 URL 編碼以處理特殊字元
encoded_pass = urllib.parse.quote_plus(DB_PASS)
DB_URL = f"postgresql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def import_csv_to_sqlite():
    if not os.path.exists(CSV_PATH):
        print(f"錯誤：找不到檔案 {CSV_PATH}")
        return

    print(f"正在讀取 {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)

    # 清理欄位名稱以便於 SQL 操作
    # 範例: "Rotational speed [rpm]" -> "rotational_speed_rpm"
    df.columns = [
        col.lower()
        .replace(' ', '_')
        .replace('[', '')
        .replace(']', '')
        .replace('-', '_')
        for col in df.columns
    ]

    print(f"正在連接至 Supabase (PostgreSQL)...")
    engine = create_engine(DB_URL)
    
    try:
        # 將資料寫入 Supabase
        print(f"正在將資料寫入資料表 '{TABLE_NAME}'...")
        df.to_sql(TABLE_NAME, engine, if_exists='append', index=False)
        print(f"成功！已將 {len(df)} 筆資料 append 至資料表 '{TABLE_NAME}'。")
        
        # 顯示前幾筆資料確認
        query = f"SELECT * FROM {TABLE_NAME} LIMIT 5"
        check_df = pd.read_sql(query, engine)
        print("\n資料預覽：")
        print(check_df)
        
    except Exception as e:
        print(f"匯入過程中發生錯誤: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    import_csv_to_sqlite()
