# 模型訓練詳細資訊

根據專案中的程式碼（如 `tran_and_export.py` 與 `train_export_ai4i.py`），目前訓練的模型資訊如下：

### 1. 模型類型
*   **演算法**: **邏輯回歸 (Logistic Regression)**
*   **套件**: 使用 `scikit-learn` (`sklearn.linear_model.LogisticRegression`)

### 2. 訓練目標 (Target)
*   **欄位名稱**: `Machine failure` (機器故障)
*   **用途**: 二元分類（0: 正常, 1: 故障），用於預測設備是否可能發生故障。

### 3. 使用的特徵 (Features)
模型使用了以下數值與類別特徵：
*   `type` (Type): 設備類型（M, L, H）
*   `air_temp` (Air temperature [K]): 空氣溫度
*   `process_temp` (Process temperature [K]): 加工溫度
*   `rot_speed` (Rotational speed [rpm]): 轉速
*   `torque` (Torque [Nm]): 扭矩
*   `tool_wear` (Tool wear [min]): 工具磨損時間

### 4. 輸出檔案
訓練完成後會產生以下兩個 `.pkl` 檔案，供 `predictive.py` 載入使用：
*   `models/defect_severity_model.pkl`: 訓練好的邏輯回歸模型本體。
*   `models/scaler.pkl`: 資料前處理器（包含 OneHotEncoder 與特徵轉換邏輯）。

### 5. 資料來源
*   **CSV 檔案**: `models/ai 2020.csv` (預測性維護資料集)
