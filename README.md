# 🔧 AI預測性維護系統 (AI Predictive Maintenance System)

一套基於機器學習的設備預測性維護 Web 應用程式，能夠即時監測感測器數據並預測機器故障風險，並提供完整的維護記錄管理與權限控制。

---

## 📋 功能特色

- **即時監測儀表板**：模擬感測器資料串流，即時顯示設備狀態。
- **異常偵測與處理**：自動識別異常值並記錄至資料庫，提供「異常記錄處理」頁面進行維護與追蹤。
- **分頁與進階篩選**：支援依設備類型、狀態及日期區間篩選異常紀錄，並具備完整的分頁功能。
- **故障預測**：使用機器學習模型（隨機森林 / XGBoost / 邏輯回歸）預測設備故障。
- **手動單次預測**：輸入感測器數值，立即取得預測結果。
- **進階儀表板**：Top 故障設備、預測故障分析、停機影響評估、趨勢比較。
- **使用者管理 (CRUD)**：管理員可維護使用者帳號、角色及基本資訊，具備完整的增刪改查功能。
- **多角色權限控制 (RBAC)**：基於角色（ADMIN / MANAGER / TEAM_LEADER）的存取權限管理。

---

## 🏗️ 專案結構

```
project1/
├── predictive.py           # Flask 主應用程式 (路由、API、預測邏輯、權限檢查)
├── train_models.py         # 模型訓練腳本 (隨機森林、XGBoost、邏輯回歸)
├── train_export_ai4i.py    # 使用 ai4i 資料集訓練並匯出模型
├── import_to_sql.py        # CSV 資料匯入 Supabase (PostgreSQL)
├── init_db.py              # 初始化資料庫結構與測試帳號
├── update_user_info_schema.py # 更新 user_info 資料表結構 (新增建立者/更新者欄位)
├── requirements.txt        # Python 套件依賴清單
├── .env                    # 環境變數 (資料庫連線資訊，勿提交至版控)
│
├── models/                 # 模型與資料檔案
│   ├── random_forest_model.pkl     # 隨機森林模型
│   ├── scaler.pkl                  # 資料前處理器
│   └── ai 2020.csv                 # 原始訓練資料集
│
├── templates/              # Jinja2 HTML 模板
│   ├── layout.html                 # 共用版型 (動態導覽列)
│   ├── login.html                  # 登入頁面
│   ├── user_management.html        # 使用者管理頁面 (限 ADMIN)
│   ├── maintenance_error.html      # 異常記錄處理頁面 (支援搜尋、分頁、編輯)
│   ├── realtime_monitoring.html    # 即時監測儀表板
│   ├── dashboard.html              # 進階分析儀表板
│   ├── training_results.html       # 訓練結果頁面
│   └── risk_assessment.html        # 風險評估頁面
│
└── static/                 # 靜態資源 (CSS)
    └── css/style.css
```

---

## ⚙️ 環境設定

### 1. 安裝套件
```bash
pip install -r requirements.txt
```

### 2. 設定環境變數
在專案根目錄建立 `.env` 檔案並填入資料庫連線資訊。

### 3. 初始化資料庫與更新結構
```bash
python init_db.py
python update_user_info_schema.py
```

---

## 🚀 帳號角色與權限

系統採取角色存取控制 (RBAC)，各角色權限定義如下：

| 角色 | 權限說明 | 可存取主要功能 |
|------|---------|---------------|
| **ADMIN** | 最高權限管理員 | 所有頁面、使用者管理、異常記錄編輯 |
| **MANAGER** | 決策主管 (僅供查詢) | 異常記錄查詢 (不可編輯)、數據儀表板、風險預算、訓練結果 |
| **TEAM_LEADER** | 技術組長 (第一線維護) | 即時監測、單次預測、異常記錄編輯 |

### 預設測試帳號
*   **管理員**: `admin001` / `admin123`
*   **主管**: `mgr001` / `mgr123`
*   **組長**: `tl001` / `tl123`

---

## 📈 異常記錄處理功能
*   **排序**：預設依「最後更新時間」從新到舊排序。
*   **分頁**：每頁 10 筆資料，支援快速切換。
*   **篩選**：可依「設備類型」、「處理狀態」及「日期範圍」進行交叉查詢。
*   **編輯**：組長與管理員可針對異常填寫建議行動並標記為「已處理」。

---

## 📦 主要套件
`flask`, `scikit-learn`, `xgboost`, `pandas`, `sqlalchemy`, `psycopg2-binary`, `python-dotenv`, `joblib`
