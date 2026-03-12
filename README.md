# 🔧 預測性維護系統 (Predictive Maintenance System)

一套基於機器學習的設備預測性維護 Web 應用程式，能夠即時監測感測器數據並預測機器故障風險。

---

## 📋 功能特色

- **即時監測儀表板**：模擬感測器資料串流，即時顯示設備狀態
- **異常偵測**：自動識別轉速、扭矩等感測器異常值
- **故障預測**：使用機器學習模型（隨機森林 / XGBoost / 邏輯回歸）預測設備故障
- **手動單次預測**：輸入感測器數值，立即取得預測結果
- **進階儀表板**：Top 故障設備、預測故障分析、停機影響評估、趨勢比較
- **風險評估報表**：視覺化呈現各設備類型的風險分級
- **訓練結果查看**：比較三種模型的評估指標
- **帳號權限管理**：多角色存取控制（管理員 / 主管 / 技術員）

---

## 🏗️ 專案結構

```
project1/
├── predictive.py           # Flask 主應用程式 (路由、API、預測邏輯)
├── train_models.py         # 模型訓練腳本 (隨機森林、XGBoost、邏輯回歸)
├── train_export_ai4i.py    # 使用 ai4i 資料集訓練並匯出模型
├── tran_and_export.py      # 資料轉換與模型匯出腳本
├── import_to_sql.py        # CSV 資料匯入 Supabase (PostgreSQL)
├── init_db.py              # 初始化資料庫結構與使用者帳號
├── trainning.py            # Kaggle 資料集下載腳本
├── test_trainning.py       # 模型載入測試腳本
├── requirements.txt        # Python 套件依賴清單
├── optimize_db.sql         # 資料庫索引最佳化 SQL
├── .env                    # 環境變數 (資料庫連線資訊，勿提交至版控)
├── .gitignore              # Git 忽略規則
├── ngrok.exe               # ngrok 網路穿透工具
│
├── models/                 # 模型與資料檔案
│   ├── random_forest_model.pkl     # 隨機森林模型
│   ├── xgboost_model.pkl           # XGBoost 模型
│   ├── logistic_regression_model.pkl # 邏輯回歸模型
│   ├── defect_severity_model.pkl   # 預設載入模型
│   ├── scaler.pkl                  # 資料前處理器 (OneHotEncoder + 特徵轉換)
│   ├── model_results.json          # 三種模型評估結果
│   ├── ai 2020.csv                 # 原始訓練資料集
│   ├── test_data.csv               # 模擬測試資料
│   └── gen_data.py                 # 模擬感測器資料生成腳本
│
├── templates/              # Jinja2 HTML 模板
│   ├── layout.html                 # 共用版型
│   ├── login.html                  # 登入頁面
│   ├── realtime_monitoring.html    # 即時監測儀表板
│   ├── dashboard.html              # 進階分析儀表板
│   ├── index.html                  # 手動預測頁面
│   ├── training_results.html       # 訓練結果頁面
│   └── risk_assessment.html        # 風險評估頁面
│
├── static/                 # 靜態資源 (CSS、JS、圖片)
│   └── css/
│       └── style.css
│
└── src/                    # 其他原始碼
```

---

## ⚙️ 環境設定

### 1. 安裝套件

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

在專案根目錄建立 `.env` 檔案：

```env
DB_USER=your_db_user
DB_PASS=your_db_password
DB_HOST=your_supabase_host
DB_PORT=5432
DB_NAME=postgres
```

### 3. 初始化資料庫

```bash
python init_db.py
```

### 4. 匯入感測器資料

```bash
# 使用現有 CSV 資料
python import_to_sql.py

# 或先產生模擬資料再匯入
python models/gen_data.py
python import_to_sql.py
```

---

## 🤖 模型訓練

### 訓練三種模型（推薦）

```bash
python train_models.py
```

訓練完成後會輸出 `model_results.json`，供「訓練結果」頁面使用。

### 使用 ai4i 資料集訓練

```bash
python train_export_ai4i.py
```

### 模型說明

| 模型 | 演算法 | 輸出檔案 |
|------|--------|---------|
| 隨機森林 | Random Forest | `models/random_forest_model.pkl` |
| XGBoost | XGBoost | `models/xgboost_model.pkl` |
| 邏輯回歸 | Logistic Regression | `models/logistic_regression_model.pkl` |

**輸入特徵**：`type`、`air_temperature_k`、`process_temperature_k`、`rotational_speed_rpm`、`torque_nm`、`tool_wear_min`  
**預測目標**：`machine_failure`（0: 正常，1: 故障）

---

## 🚀 啟動應用程式

```bash
python predictive.py
```

瀏覽器開啟：[http://localhost:5000](http://localhost:5000)

### 測試帳號

| 帳號 | 角色 | 可存取頁面 |
|------|------|-----------|
| `admin001` | 管理員 | 全部頁面 |
| `mgr001` | 主管 | 儀表板、風險評估 |
| `tl001` | 技術員 | 即時監測、訓練結果、手動預測 |

---

## 🌐 外網存取（ngrok）

若需對外公開測試，可使用 ngrok：

```bash
.\ngrok.exe http 5000
```

---

## 📦 主要依賴套件

| 套件 | 用途 |
|------|------|
| `flask` | Web 框架 |
| `scikit-learn` | 機器學習模型 |
| `xgboost` | XGBoost 模型 |
| `pandas` / `numpy` | 資料處理 |
| `sqlalchemy` | ORM 資料庫操作 |
| `psycopg2-binary` | PostgreSQL 驅動 |
| `python-dotenv` | 環境變數管理 |
| `joblib` | 模型序列化 |

---

## ⚠️ 注意事項

- `.env` 檔案含有資料庫機密資訊，已加入 `.gitignore`，**請勿提交至版控**
- 模型訓練前請確認 `models/ai 2020.csv` 資料集存在
- Supabase 免費方案有連線數量限制，請注意並發連線數
