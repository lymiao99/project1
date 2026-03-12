import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

#CSV_PATH = os.path.join("models", "ai_2020.csv")
CSV_PATH = os.path.join("models", "test_data.csv")

# 你 Flask 端將要使用的特徵（建議就用 AI4I 的核心欄位）
CAT_COLS = ["Type", "Product ID"]
NUM_COLS = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]

# 目標：先做「是否故障」分類（0/1）
TARGET_COL = "Machine failure"

def main():
    df = pd.read_csv(CSV_PATH)

    # 基本檢查
    need_cols = CAT_COLS + NUM_COLS + [TARGET_COL]
    missing = [c for c in need_cols if c not in df.columns]
    if missing:
        raise ValueError(f"CSV 缺少欄位: {missing}\n目前欄位: {list(df.columns)}")

    X = df[CAT_COLS + NUM_COLS].copy()
    y = df[TARGET_COL].astype(int)

    # 前處理器：類別 one-hot；數值標準化
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_COLS),
            ("num", StandardScaler(), NUM_COLS),
        ],
        remainder="drop",
    )

    # 模型（簡單穩定，先能產出 pkl）
    model = LogisticRegression(max_iter=2000)

    # 這裡把 preprocessor 當成你 Flask 的 scaler.pkl
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    preprocessor.fit(X_train)
    X_train_t = preprocessor.transform(X_train)
    model.fit(X_train_t, y_train)

    os.makedirs("models", exist_ok=True)
    joblib.dump(preprocessor, "models/scaler.pkl")
    joblib.dump(model, "models/defect_severity_model.pkl")

    print("Exported models/scaler.pkl and models/defect_severity_model.pkl")

if __name__ == "__main__":
    main()
