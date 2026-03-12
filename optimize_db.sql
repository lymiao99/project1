-- 在 Supabase SQL Editor 執行以下語句以優化查詢
CREATE INDEX IF NOT EXISTS idx_maintenance_type ON maintenance (type);
CREATE INDEX IF NOT EXISTS idx_maintenance_udi ON maintenance (udi);
CREATE INDEX IF NOT EXISTS idx_maintenance_failure ON maintenance (machine_failure);
