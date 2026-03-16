from sqlalchemy import create_engine, text
import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

encoded_pass = urllib.parse.quote_plus(DB_PASS)
DB_URL = f"postgresql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

def update_schema():
    queries = [
        "ALTER TABLE user_info ADD COLUMN IF NOT EXISTS created_by TEXT;",
        "ALTER TABLE user_info ADD COLUMN IF NOT EXISTS last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE user_info ADD COLUMN IF NOT EXISTS last_updated_by TEXT;"
    ]
    
    try:
        with engine.connect() as conn:
            for query in queries:
                print(f"Executing: {query}")
                conn.execute(text(query))
            conn.commit()
            print("Schema updated successfully.")
    except Exception as e:
        print(f"Error updating schema: {e}")

if __name__ == "__main__":
    update_schema()
