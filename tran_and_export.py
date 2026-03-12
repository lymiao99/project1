import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
from sklearn.linear_model import LogisticRegression

# ====== 你要改的地方 START ======
CSV_PATH = "models/ai 2020.csv"

# Kaggle 資料集的「目標欄位」(y) 名稱
TARGET_COL = "Machine failure" 

# Kaggle 欄位 -> 你的 Flask 期望欄位 的對應
# 這裡我們挑選這份資料集最有用的幾個數值特徵
COLUMN_MAP = {
    "Type": "type",
    "Air temperature [K]": "air_temp",
    "Process temperature [K]": "process_temp",
    "Rotational speed [rpm]": "rot_speed",
    "Torque [Nm]": "torque",
    "Tool wear [min]": "tool_wear",
}
# ====== 你要改的地方 END ======

FEATURE_COLS = list(COLUMN_MAP.values())

def main():
    df = pd.read_csv(CSV_PATH)

    # 1) 重新命名欄位，對齊 Flask 端傳入的 key
    #    (如果 Kaggle 欄位名稱不同，請在 COLUMN_MAP 左邊填 Kaggle 原名、右邊填目標名)
    rename_dict = {k: v for k, v in COLUMN_MAP.items() if k in df.columns and k != v}
    if rename_dict:
        df = df.rename(columns=rename_dict)

    # 2) 檢查需要的欄位是否存在
    missing = [c for c in FEATURE_COLS + [TARGET_COL] if c not in df.columns]
    if missing:
        raise ValueError(
            f"資料缺少欄位：{missing}\n"
            f"目前欄位：{list(df.columns)}\n"
            f"請修正 TARGET_COL 或 COLUMN_MAP。"
        )

    # 3) 取出 X, y
    X = df[FEATURE_COLS].copy()
    y = df[TARGET_COL].copy()

    # 4) 基本清理
    num_cols = ["air_temp", "process_temp", "rot_speed", "torque", "tool_wear"]
    cat_cols = ["type"]
    
    # 確保數值欄位正確轉換為數值，類別欄位轉換為字串
    for col in num_cols:
        if col in X.columns:
            X[col] = pd.to_numeric(X[col], errors='coerce')
    
    for col in cat_cols:
        if col in X.columns:
            X[col] = X[col].astype(str)

    # 5) 建立「轉換器」(我們把它存成 scaler.pkl)
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
            ("num", "passthrough", num_cols)
        ],
        remainder="drop",
    )

    # 6) 模型（示範用 LogisticRegression，多類別也可）
    clf = LogisticRegression(max_iter=2000)

    # 7) 用 Pipeline 串起來訓練
    #    注意：我們會拆開存檔（preprocessor -> scaler.pkl, model -> defect_severity_model.pkl）
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    # 先 fit 轉換器
    preprocessor.fit(X_train)
    X_train_enc = preprocessor.transform(X_train)
    X_test_enc = preprocessor.transform(X_test)

    # 再 fit 模型
    clf.fit(X_train_enc, y_train)

    # 8) 評估（可選）
    y_pred = clf.predict(X_test_enc)
    print(classification_report(y_test, y_pred))

    # 9) 輸出 .pkl
    os.makedirs("models", exist_ok=True)
    joblib.dump(preprocessor, "models/scaler.pkl")
    joblib.dump(clf, "models/defect_severity_model.pkl")

    print("Success: models/scaler.pkl and models/defect_severity_model.pkl exported.")

if __name__ == "__main__":
    main()
