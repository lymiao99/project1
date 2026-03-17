# 資料庫實體關係圖 (ERD)

本專案使用 Supabase (PostgreSQL) 作為資料庫，主要包含三個資料表。以下是其結構與關係：

```mermaid
erDiagram
    user_info ||--o{ maintenance_error : "updates"
    maintenance ||--o{ maintenance_error : "logs"

    user_info {
        int id PK "SERIAL"
        string acct_no UK "唯一帳號"
        string pwds "密碼"
        string acct_name "姓名"
        string role "角色 (ADMIN, MANAGER, TEAM_LEADER)"
        timestamp created_at "建立時間"
        string created_by "建立者"
        timestamp last_updated_at "最後更新時間"
        string last_updated_by "最後更新者"
    }

    maintenance {
        int udi PK "唯一識別碼"
        string product_id "產品 ID"
        string type "設備類型 (L, M, H)"
        float air_temperature_k "環境溫度 (K)"
        float process_temperature_k "製程溫度 (K)"
        int rotational_speed_rpm "轉速 (rpm)"
        float torque_nm "扭矩 (Nm)"
        float tool_wear_min "刀具磨耗 (min)"
        int machine_failure "是否故障 (0/1)"
        int twf "刀具失效"
        int hdf "散熱失效"
        int pwf "功率失效"
        int osf "過載失效"
        int rnf "隨機失效"
    }

    maintenance_error {
        int udi FK "關聯至 maintenance.udi"
        string product_id "產品 ID"
        string type "設備類型"
        float air_temperature_k "溫度"
        float process_temperature_k "製程溫度"
        int rotational_speed_rpm "轉速"
        float torque_nm "扭矩"
        float tool_wear_min "磨耗"
        int machine_failure "故障預測結果"
        int twf "TWF"
        int hdf "HDF"
        int pwf "PWF"
        int osf "OSF"
        int rnf "RNF"
        string recommendation "維護建議"
        string last_update_by FK "最後處理者 (user_info.acct_no)"
        int process_flag "處理狀態 (0: 未處理, 1: 已處理)"
        timestamp last_update_date "最後更新日期"
        timestamp created_date "紀錄建立時間"
    }
```

### 關係說明：
1.  **[maintenance](file:///d:/homework/project1/predictive.py#396-407) 與 [maintenance_error](file:///d:/homework/project1/predictive.py#396-407)**:
    *   一對多關係。當系統偵測到 [maintenance](file:///d:/homework/project1/predictive.py#396-407) 表中的數據有異常或預測故障時，會將詳細資訊記錄到 [maintenance_error](file:///d:/homework/project1/predictive.py#396-407) 中。
    *   透過 `udi` 欄位進行關聯。
2.  **[user_info](file:///d:/homework/project1/init_db.py#19-62) 與 [maintenance_error](file:///d:/homework/project1/predictive.py#396-407)**:
    *   一對多關係。每個異常紀錄在處理時，會記錄是哪位使用者（`last_update_by`）進行了維護建議與狀態更新。
    *   透過 `user_info.acct_no` 進行關聯。
