import pandas as pd
import numpy as np
import joblib
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score
try:
    from xgboost import XGBClassifier
except ImportError:
    print("XGBoost not found. Please install it with 'pip install xgboost'.")
    XGBClassifier = None

from sqlalchemy import create_engine
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

# 數據庫連線設定 (從 .env 讀取)
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
TABLE_NAME = 'maintenance'

encoded_pass = urllib.parse.quote_plus(DB_PASS)
DB_URL = f"postgresql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 模型儲存設定
MODEL_DIR = 'models'
RESULT_JSON = os.path.join(MODEL_DIR, 'model_results.json')

def train():
    print(f"Connecting to Supabase and fetching data from '{TABLE_NAME}'...")
    engine = create_engine(DB_URL)
    
    try:
        # 1. 讀取數據庫數據
        query = f"SELECT * FROM {TABLE_NAME}"
        df = pd.read_sql(query, engine)
        print(f"Data fetched successfully: {len(df)} records.")
    except Exception as e:
        print(f"Error fetching data from database: {e}")
        return
    finally:
        engine.dispose()
    
    # 2. 特徵工程 (Feature Engineering) - 捕捉趨勢
    print("Performing feature engineering (Trend Analysis)...")
    # 按照 UDI 或原始順序排序（這裡假設數據本身是按時間序列儲存的）
    df = df.sort_values('udi').reset_index(drop=True)
    
    print("First 5 rows before feature engineering:")
    print(df[['air_temperature_k', 'rotational_speed_rpm']].head())
    
    # 計算移動平均溫度 (5筆窗口)
    df['air_temp_avg'] = df['air_temperature_k'].rolling(window=5).mean()
    # 計算旋轉轉速震盪率 (5筆窗口標準差)
    df['rot_oscillation'] = df['rotational_speed_rpm'].rolling(window=5).std()
    
    # 特徵與目標設定 (納入特徵工程產生的欄位)
    features = ['type', 'air_temperature_k', 'process_temperature_k', 
                'rotational_speed_rpm', 'torque_nm', 'tool_wear_min',
                'air_temp_avg', 'rot_oscillation']
    target = 'machine_failure'
    
    # 我們只針對特徵工程產生的欄位進行 dropna，避免受其他無關欄位（如 created_date）影響
    df = df.dropna(subset=features).reset_index(drop=True)
    print(f"Data ready for training: {len(df)} rows")
    
    X = df[features]
    y = df[target]

    # 3. 預處理
    numeric_features = ['air_temperature_k', 'process_temperature_k', 
                        'rotational_speed_rpm', 'torque_nm', 'tool_wear_min',
                        'air_temp_avg', 'rot_oscillation']
    categorical_features = ['type']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_features),
            ('cat', OneHotEncoder(), categorical_features)
        ])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 適配轉換器
    X_train_processed = preprocessor.fit_transform(X_train)
    X_test_processed = preprocessor.transform(X_test)
    
    # 儲存轉換器
    joblib.dump(preprocessor, os.path.join(MODEL_DIR, 'scaler.pkl'))

    # 4. 模型訓練與評估
    models = {
        'logistic_regression': LogisticRegression(random_state=42, max_iter=1000),
        'random_forest': RandomForestClassifier(n_estimators=100, random_state=42)
    }
    
    if XGBClassifier:
        models['xgboost'] = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)

    results = {}

    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(X_train_processed, y_train)
        y_pred = model.predict(X_test_processed)
        
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        
        # 儲存模型
        model_filename = os.path.join(MODEL_DIR, f'{name}_model.pkl')
        joblib.dump(model, model_filename)
        
        results[name] = {
            'accuracy': round(acc * 100, 2),
            'precision': round(prec * 100, 2),
            'recall': round(rec * 100, 2),
            'algorithm': name.replace('_', ' ').title(),
            'summary': get_summary(name)
        }
        print(f"{name} trained. Accuracy: {acc:.4f}")

    # 5. 儲存結果 JSON
    with open(RESULT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"All models trained and results saved to {RESULT_JSON}")

def get_summary(name):
    summaries = {
        'logistic_regression': "傳統的統計模型，具有極佳的解釋性，適合分析單一參數對故障的影響權重。",
        'random_forest': "由多棵決策樹構成的集成模型，擅長處理非線性特徵互動（如溫度與轉速的複合影響）。",
        'xgboost': "基於梯度提升的先進算法，目前結構化數據預測效能最強的模型，能捕捉極微小的數據異常。"
    }
    return summaries.get(name, "")

if __name__ == "__main__":
    train()
