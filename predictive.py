from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import joblib
import json
import pandas as pd
import numpy as np
import os
import time
from collections import deque
from sqlalchemy import create_engine, text
import urllib.parse
from dotenv import load_dotenv

#import os
#from fastapi import FastAPI, HTTPException, request
#from fastapi.staticfiles import StaticFiles
#from fastapi.responses import HTMLResponse, FileResponse
#from supabase import create_client, create_client
#from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# 登入追蹤 (fail_count, lock_until)
login_tracker = {}

@app.context_processor
def inject_user():
    """注入目前登入使用者資訊"""
    return dict(current_user=session.get('user_info'))

def login_required(f):
    """登入驗證裝飾器，限制未登入使用者存取"""
    pass

@app.route('/api/model-results')
def api_model_results():
    """Return model training results."""
    path = 'models/model_results.json'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({'error': 'Results not found'})

# 模型設定
CSV_PATH = 'models/ai 2020.csv'
MODEL_PATH = 'models/random_forest_model.pkl'
SCALER_PATH = 'models/scaler.pkl'
TABLE_NAME = 'maintenance'

# Supabase 資料庫設定（從 .env 讀取）
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# 編碼密碼 URL
encoded_pass = urllib.parse.quote_plus(DB_PASS)
DB_URL = f"postgresql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 建立資料庫引擎
engine = create_engine(DB_URL)

# 載入模型
try:
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        print("Model and scaler loaded successfully.")
    else:
        raise FileNotFoundError("Model files not found.")
except Exception as e:
    print(f"Warning: {e}. Using placeholders.")
    model = None
    scaler = None

# 感測資料歷史(每個帳號各自保存)
sensor_history = {}
# 最後讀取 UDI
last_seen_udi = {}

@app.route('/predict-manual')
def predict_manual():
    """手動預測頁面"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_acct = session.get('user')
    permissions = {
        'admin001': ['index', 'dashboard', 'training_results', 'risk_assessment', 'predict_manual'],
        'mgr001': ['dashboard', 'risk_assessment'],
        'tl001': ['index', 'training_results', 'predict_manual'],
    }
    allowed_pages = permissions.get(user_acct, [])
    if 'predict_manual' not in allowed_pages:
        return "無權限", 403
        
    return render_template('index.html', user_info=session.get('user_info'))

@app.route('/')
def index():
    """Realtime monitoring page."""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_acct = session.get('user')
    permissions = {
        'admin001': ['index', 'dashboard', 'training_results', 'risk_assessment', 'predict_manual'],
        'mgr001': ['dashboard', 'risk_assessment'],
        'tl001': ['index', 'training_results', 'predict_manual'],
    }
    
    allowed_pages = permissions.get(user_acct, [])
    if 'index' not in allowed_pages:
        if allowed_pages:
            return redirect(url_for(allowed_pages[0]))
        return "無權限", 403

    return render_template('realtime_monitoring.html', user_info=session.get('user_info'))

@app.route('/api/sensor-stream')
def sensor_stream():
    """即時感測資料串流 API"""
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    acct_no = session['user']
    last_udi = last_seen_udi.get(acct_no)
    
    try:
        if last_udi is None:
            # If no history, just pick the first row to start
            query = text(f"SELECT * FROM {TABLE_NAME} a where not exists (select 1 from public.maintenance_error b where a.udi=b.udi) ORDER BY udi ASC LIMIT 1")
            params = {}
        else:
            # Fetch the next row
            query = text(f"SELECT * FROM {TABLE_NAME} a WHERE udi > 10000 and udi > :last_udi and not exists (select 1 from public.maintenance_error b where a.udi=b.udi) ORDER BY udi ASC LIMIT 1")
            params = {"last_udi": last_udi}

        with engine.connect() as conn:
            row = conn.execute(query, params).fetchone()

            if row is None:
                # If we've reached the end, loop back to the first row
                row = conn.execute(
                    text(f"SELECT * FROM {TABLE_NAME} where not exists (select 1 from public.maintenance_error b where a.udi=b.udi) ORDER BY udi ASC LIMIT 1")
                ).fetchone()

        if not row:
            return jsonify({'success': False, 'error': 'No data in maintenance table'})
        
        # 轉成字典格式
        data = dict(row._mapping)
        last_seen_udi[acct_no] = int(data["udi"])
        
        # 建立歷史資料 (每帳號)
        if acct_no not in sensor_history:
            sensor_history[acct_no] = deque(maxlen=5)
        
        history = sensor_history[acct_no]
        history.append({
            'temp': float(data['air_temperature_k']),
            'speed': float(data['rotational_speed_rpm'])
        })
        
        # 均溫
        temp_avg = sum(h['temp'] for h in history) / len(history)
        # 轉速震盪 (標準差)
        if len(history) > 1:
            speeds = [h['speed'] for h in history]
            speed_std = float(np.std(speeds))
        else:
            speed_std = 0.0
            
        # 建立特徵
        features_df = pd.DataFrame([{
            'type': data['type'],
            'air_temperature_k': float(data['air_temperature_k']),
            'process_temperature_k': float(data['process_temperature_k']),
            'rotational_speed_rpm': float(data['rotational_speed_rpm']),
            'torque_nm': float(data['torque_nm']),
            'tool_wear_min': float(data['tool_wear_min']),
            'air_temp_avg': temp_avg,
            'rot_oscillation': speed_std
        }])
        
        # 模型預測
        prediction = 0
        confidence = 0
        if model and scaler:
            X_encoded = scaler.transform(features_df)
            prediction = int(model.predict(X_encoded)[0])
            probs = model.predict_proba(X_encoded)[0]
            confidence = round(float(np.max(probs)) * 100, 2)
            
            if prediction == 1:
                try:
                    with engine.begin() as insert_conn:
                        insert_query = text("""
                            INSERT INTO maintenance_error (
                                udi, product_id, type, air_temperature_k, process_temperature_k, 
                                rotational_speed_rpm, torque_nm, tool_wear_min, machine_failure, 
                                twf, hdf, pwf, osf, rnf, recommendation, last_update_by
                            ) VALUES (
                                :udi, :product_id, :type, :air_temperature_k, :process_temperature_k, 
                                :rotational_speed_rpm, :torque_nm, :tool_wear_min, :machine_failure, 
                                :twf, :hdf, :pwf, :osf, :rnf, :recommendation, :last_update_by
                            )
                        """)
                        insert_conn.execute(insert_query, {
                            "udi": data["udi"],
                            "product_id": data.get("product_id", ""),
                            "type": data["type"],
                            "air_temperature_k": data["air_temperature_k"],
                            "process_temperature_k": data["process_temperature_k"],
                            "rotational_speed_rpm": data["rotational_speed_rpm"],
                            "torque_nm": data["torque_nm"],
                            "tool_wear_min": data["tool_wear_min"],
                            "machine_failure": prediction,
                            "twf": data.get("twf", 0),
                            "hdf": data.get("hdf", 0),
                            "pwf": data.get("pwf", 0),
                            "osf": data.get("osf", 0),
                            "rnf": data.get("rnf", 0),
                            "recommendation": "建議立即安排設備停機檢查",
                            "last_update_by": acct_no
                        })
                except Exception as ex:
                    print("Error inserting into maintenance_error:", ex)
            
        return jsonify({
            'success': True,
            'data': {
                'udi': data['udi'],
                'type': data['type'],
                'air_temp': data['air_temperature_k'],
                'process_temp': data['process_temperature_k'],
                'rot_speed': data['rotational_speed_rpm'],
                'torque': data['torque_nm'],
                'tool_wear': data['tool_wear_min'],
                'air_temp_avg': round(temp_avg, 2),
                'rot_oscillation': round(speed_std, 2)
            },
            'prediction': prediction,
            'confidence': confidence,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication API."""
    if request.method == 'GET':
        return render_template('login.html')

    acct_no = request.form.get('acct_no')
    pwds = request.form.get('pwds')
    now = time.time()

    # 鎖定檢查
    tracker = login_tracker.get(acct_no, {'fail_count': 0, 'lock_until': 0})
    if tracker['lock_until'] > now:
        remaining = int(tracker['lock_until'] - now)
        return jsonify({'success': False, 'message': 'Account is temporarily locked', 'lock_time': remaining})

    try:
        # 查詢使用者帳號資料
        query = text("SELECT acct_no, pwds, acct_name, role FROM user_info WHERE acct_no = :acct_no")
        with engine.connect() as conn:
            result = conn.execute(query, {"acct_no": acct_no}).fetchone()

        if not result:
            return jsonify({'success': False, 'message': '帳號不存在'})

        db_acct, db_pwds, db_name, db_role = result
        if pwds == db_pwds:
            login_tracker[acct_no] = {'fail_count': 0, 'lock_until': 0}
            session['user'] = acct_no
            session['user_info'] = {
                'acct_no': db_acct,
                'acct_name': db_name or 'Unknown',
                'role': db_role or 'Unknown'
            }
            return jsonify({'success': True, 'redirect': url_for('index')})
        else:
            tracker['fail_count'] += 1
            lock_time = 0
            if tracker['fail_count'] >= 5:
                tracker['lock_until'] = now + 10
                tracker['fail_count'] = 0
                lock_time = 10
                msg = "Too many failed attempts. Locked for 10 seconds"
            else:
                msg = "密碼錯誤"
            login_tracker[acct_no] = tracker
            return jsonify({'success': False, 'message': msg, 'lock_time': lock_time})
    except Exception as e:
        return jsonify({'success': False, 'message': f'登入失敗: {str(e)}'})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/predict', methods=['POST'])
def predict_route():
    """API：手動輸入資料進行預測"""
    try:
        # 從表單取得資料
        current_temp = float(request.form.get('air_temp', 0))
        data = {
            'type': request.form.get('type', 'M'),
            'air_temperature_k': current_temp,
            'process_temperature_k': float(request.form.get('process_temp', 0)),
            'rotational_speed_rpm': float(request.form.get('rot_speed', 0)),
            'torque_nm': float(request.form.get('torque', 0)),
            'tool_wear_min': float(request.form.get('tool_wear', 0)),
            'air_temp_avg': current_temp,
            'rot_oscillation': 0.0
        }

        if model and scaler:
            # 轉成 DataFrame 供模型輸入
            X = pd.DataFrame([data])
            # 前處理編碼 (ColumnTransformer)
            X_encoded = scaler.transform(X)
            
            # 預測 (0: 正常, 1: 故障)
            prediction = int(model.predict(X_encoded)[0])
            # 預測機率 (若模型支援 LogisticRegression)
            if hasattr(model, "predict_proba"):
                prob = model.predict_proba(X_encoded)[0]
                confidence = float(prob[prediction])
            else:
                confidence = 1.0
        else:
            # Mock 預測
            prediction = 0
            confidence = 0.95

        # 回傳結果
        risk_level = "高風險" if prediction == 1 else "正常"
        recommendation = "建議立即安排設備停機檢查" if prediction == 1 else "目前狀態穩定，無需特別處置"

        return jsonify({
            'success': True,
            'prediction': prediction,
            'confidence': round(confidence * 100, 2),
            'risk_level': risk_level,
            'recommendation': recommendation
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/dashboard')
def dashboard():
    """儀表板 (主管)"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    role = session.get('user_info', {}).get('role')
    if role not in ['ADMIN', 'MANAGER']:
        return "Forbidden", 403
        
    return render_template('dashboard.html')

@app.route('/training-results')
def training_results():
    """訓練結果"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    role = session.get('user_info', {}).get('role')
    # 使用者要求: TEAM LEADER 看不到, MANAGER 看得到
    if role not in ['ADMIN', 'MANAGER']:
        return "Forbidden", 403
        
    return render_template('training_results.html')

@app.route('/risk-assessment')
def risk_assessment():
    """風險評估 (主管)"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    role = session.get('user_info', {}).get('role')
    if role not in ['ADMIN', 'MANAGER']:
        return "Forbidden", 403
        
    return render_template('risk_assessment.html')

@app.route('/maintenance-error')
def maintenance_error():
    """設備記錄異常處理 (組長)"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    role = session.get('user_info', {}).get('role')
    if role not in ['ADMIN', 'MANAGER', 'TEAM_LEADER']:
        return "Forbidden", 403
        
    return render_template('maintenance_error.html')

@app.route('/user-management')
def user_management():
    """使用者管理 (管理員)"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_acct = session.get('user')
    # 目前先開放給 admin001
    if user_acct != 'admin001':
        return "Forbidden", 403
        
    return render_template('user_management.html')

@app.route('/api/users')
def api_users():
    """取得使用者列表"""
    if 'user' not in session or session.get('user') != 'admin001':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        query = "SELECT id, acct_no, acct_name, role, created_at, created_by, last_updated_at, last_updated_by FROM user_info ORDER BY id ASC"
        with engine.connect() as conn:
            result = conn.execute(text(query)).fetchall()
            data = []
            for row in result:
                item = dict(row._mapping)
                if item['created_at']:
                    item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if item['last_updated_at']:
                    item['last_updated_at'] = item['last_updated_at'].strftime('%Y-%m-%d %H:%M:%S')
                data.append(item)
            return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/users/add', methods=['POST'])
def api_add_user():
    """新增使用者"""
    if 'user' not in session or session.get('user') != 'admin001':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.json
    acct_no = data.get('acct_no')
    acct_name = data.get('acct_name')
    pwds = data.get('pwds')
    role = data.get('role')
    
    if not acct_no or not pwds:
        return jsonify({'success': False, 'error': '帳號與密碼為必填'})
        
    try:
        query = text("""
            INSERT INTO user_info (acct_no, acct_name, pwds, role, created_by, last_updated_by)
            VALUES (:acct_no, :acct_name, :pwds, :role, :created_by, :last_updated_by)
        """)
        with engine.begin() as conn:
            conn.execute(query, {
                'acct_no': acct_no,
                'acct_name': acct_name,
                'pwds': pwds,
                'role': role,
                'created_by': session['user'],
                'last_updated_by': session['user']
            })
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/users/update', methods=['POST'])
def api_update_user():
    """更新使用者"""
    if 'user' not in session or session.get('user') != 'admin001':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.json
    uid = data.get('id')
    acct_no = data.get('acct_no')
    acct_name = data.get('acct_name')
    pwds = data.get('pwds')
    role = data.get('role')
    
    if not uid:
        return jsonify({'success': False, 'error': '缺失使用者 ID'})
        
    try:
        # 密碼只有在有提供時才更新
        if pwds:
            query = text("""
                UPDATE user_info 
                SET acct_no = :acct_no, 
                    acct_name = :acct_name, 
                    pwds = :pwds, 
                    role = :role, 
                    last_updated_by = :last_updated_by,
                    last_updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """)
        else:
            query = text("""
                UPDATE user_info 
                SET acct_no = :acct_no, 
                    acct_name = :acct_name, 
                    role = :role, 
                    last_updated_by = :last_updated_by,
                    last_updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """)
            
        params = {
            'acct_no': acct_no,
            'acct_name': acct_name,
            'role': role,
            'last_updated_by': session['user'],
            'id': uid
        }
        if pwds:
            params['pwds'] = pwds
            
        with engine.begin() as conn:
            conn.execute(query, params)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/users/delete', methods=['POST'])
def api_delete_user():
    """刪除使用者"""
    if 'user' not in session or session.get('user') != 'admin001':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.json
    uid = data.get('id')
    
    if not uid:
        return jsonify({'success': False, 'error': '缺失使用者 ID'})
        
    try:
        query = text("DELETE FROM user_info WHERE id = :id")
        with engine.begin() as conn:
            conn.execute(query, {'id': uid})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/maintenance-error')
def api_maintenance_error():
    """取得異常紀錄列表 (支援分頁、篩選、排序)"""
    try:
        # 取得分頁與篩選參數
        try:
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 10))
        except (ValueError, TypeError):
            page = 1
            limit = 10
            
        offset = (page - 1) * limit
        
        equip_type = request.args.get('type')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # 構建查詢語法
        where_clauses = []
        params = {}
        
        if equip_type:
            where_clauses.append("type = :type")
            params['type'] = equip_type
        if status:
            where_clauses.append("process_flag = :status")
            params['status'] = int(status)
        if start_date:
            where_clauses.append("last_update_date >= :start_date")
            params['start_date'] = f"{start_date} 00:00:00"
        if end_date:
            where_clauses.append("last_update_date <= :end_date")
            params['end_date'] = f"{end_date} 23:59:59"
            
        where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # 取得總筆數
        count_query = text(f"SELECT COUNT(*) FROM maintenance_error {where_str}")
        
        # 取得分頁資料 (強制依照 last_update_date DESC 排序)
        data_query = text(f"""
            SELECT * FROM maintenance_error 
            {where_str} 
            ORDER BY last_update_date DESC 
            LIMIT :limit OFFSET :offset
        """)
        params['limit'] = limit
        params['offset'] = offset

        with engine.connect() as conn:
            total_count = conn.execute(count_query, {k:v for k,v in params.items() if k not in ['limit', 'offset']}).scalar()
            result = conn.execute(data_query, params).fetchall()
            data = [dict(row._mapping) for row in result]
            
            # 處理時間格式
            for row in data:
                if 'created_date' in row and row['created_date']:
                    row['created_date'] = row['created_date'].strftime('%Y-%m-%d %H:%M:%S')
                if 'last_update_date' in row and row['last_update_date']:
                    row['last_update_date'] = row['last_update_date'].strftime('%Y-%m-%d %H:%M:%S')

            return jsonify({
                'success': True, 
                'data': data, 
                'total': total_count,
                'page': page,
                'limit': limit,
                'pages': (total_count + limit - 1) // limit
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/maintenance-error/update', methods=['POST'])
def update_maintenance_error():
    """更新異常紀錄建議事項與狀態"""
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})

    role = session.get('user_info', {}).get('role')
    # 使用者要求: MANAGER 不能編輯
    if role == 'MANAGER':
        return jsonify({'success': False, 'error': '權限不足：經理帳號僅供查詢，不可編輯內容'})

    data = request.json
    udi = data.get('udi')
    recommendation = data.get('recommendation')
    
    if not udi:
        return jsonify({'success': False, 'error': 'Missing UDI'})

    user_acct = session.get('user')

    try:
        query = text("""
            UPDATE maintenance_error 
            SET recommendation = :recommendation, 
                process_flag = 1,
                last_update_by = :last_update_by,
                last_update_date = CURRENT_TIMESTAMP
            WHERE udi = :udi
        """)
        
        with engine.begin() as conn:
            conn.execute(query, {
                'recommendation': recommendation,
                'last_update_by': user_acct,
                'udi': udi
            })
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard-advanced')
def api_dashboard_advanced():
    """Advanced dashboard API."""
    try:
        # 區塊 1. 設備類型故障比例 (H/M/L)
        type_fail_query = f"""
            SELECT type, SUM(machine_failure) as failures
            FROM {TABLE_NAME}
            WHERE machine_failure = 1
            GROUP BY type
        """
        type_fail_df = pd.read_sql(type_fail_query, engine)
        type_failure_ratios = [
            {'type': r['type'], 'count': int(r['failures'])}
            for _, r in type_fail_df.iterrows()
        ]

        # 區塊 2. 異常設備 () 清單
        stats_query = f"""
            SELECT 
                AVG(rotational_speed_rpm) as mean_speed,
                STDDEV(rotational_speed_rpm) as std_speed,
                AVG(torque_nm) as mean_torque,
                STDDEV(torque_nm) as std_torque
            FROM {TABLE_NAME}
        """
        stats_row = pd.read_sql(stats_query, engine).iloc[0]
        mean_speed = float(stats_row['mean_speed'] or 0)
        std_speed = float(stats_row['std_speed'] or 1)
        mean_torque = float(stats_row['mean_torque'] or 0)
        std_torque = float(stats_row['std_torque'] or 1)

        anomaly_query = f"""
            SELECT udi, type, rotational_speed_rpm, torque_nm, tool_wear_min
            FROM {TABLE_NAME}
            WHERE rotational_speed_rpm > {mean_speed + 2 * std_speed}
               OR rotational_speed_rpm < {mean_speed - 2 * std_speed}
               OR torque_nm > {mean_torque + 2 * std_torque}
               OR torque_nm < {mean_torque - 2 * std_torque}
            ORDER BY udi
            LIMIT 30
        """
        # 區塊 2. 異常設備列表 & 原因比例
        anomaly_df = pd.read_sql(anomaly_query, engine)
        anomaly_devices = []
        reason_counts = {}
        
        for _, r in anomaly_df.iterrows():
            reasons = []
            spd = float(r['rotational_speed_rpm'])
            trq = float(r['torque_nm'])
            if spd > mean_speed + 2 * std_speed or spd < mean_speed - 2 * std_speed:
                reason = '轉速異常'
                reasons.append(reason)
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            if trq > mean_torque + 2 * std_torque or trq < mean_torque - 2 * std_torque:
                reason = '扭矩異常'
                reasons.append(reason)
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
                
            anomaly_devices.append({
                'udi': int(r['udi']),
                'type': r['type'],
                'speed': round(spd, 1),
                'torque': round(trq, 1),
                'tool_wear': round(float(r['tool_wear_min']), 1),
                'reason': ' / '.join(reasons)
            })
            
        anomaly_reason_stats = [
            {'reason': k, 'count': v} for k, v in reason_counts.items()
        ]

        # 區塊 3. 預測性故障 (高磨耗 設備)
        predict_normal = 0
        predict_failure = 0
        if model and scaler:
            avg_wear_query = f"SELECT AVG(tool_wear_min) as avg_wear FROM {TABLE_NAME}"
            avg_wear = float(pd.read_sql(avg_wear_query, engine).iloc[0, 0] or 0)
            threshold = avg_wear * 1.5

            high_wear_query = f"""
                SELECT type, air_temperature_k, process_temperature_k,
                       rotational_speed_rpm, torque_nm, tool_wear_min
                FROM {TABLE_NAME}
                WHERE tool_wear_min > {threshold}
                LIMIT 200
            """
            hw_df = pd.read_sql(high_wear_query, engine)
            if len(hw_df) > 0:
                hw_df['air_temp_avg'] = hw_df['air_temperature_k']
                hw_df['rot_oscillation'] = 0.0
                feature_cols = ['type', 'air_temperature_k', 'process_temperature_k',
                                'rotational_speed_rpm', 'torque_nm', 'tool_wear_min',
                                'air_temp_avg', 'rot_oscillation']
                X = scaler.transform(hw_df[feature_cols])
                preds = model.predict(X)
                predict_failure = int(np.sum(preds == 1))
                predict_normal = int(np.sum(preds == 0))

        # 區塊 4. 成本 (依設備類型 統計)
        impact_query = f"""
            SELECT type,
                   SUM(machine_failure) as failures,
                   COUNT(0) as total
            FROM {TABLE_NAME}
            GROUP BY type
        """
        impact_df = pd.read_sql(impact_query, engine)
        downtime_impact = []
        cost_per_failure = {'L': 8000, 'M': 12000, 'H': 18000}
        for _, r in impact_df.iterrows():
            t = r['type']
            fails = int(r['failures'] if r['failures'] else 0)
            downtime_impact.append({
                'type': t,
                'failures': fails,
                'total': int(r['total']),
                'est_cost': fails * cost_per_failure.get(t, 10000)
            })

        # 區塊 5. 趨勢 (前後半段) 比較
        total_query = f"SELECT COUNT(0) FROM {TABLE_NAME}"
        total_count = int(pd.read_sql(total_query, engine).iloc[0, 0])
        half = total_count // 2
        bucket_size = max(half // 5, 1)

        trend_query = f"""
            SELECT udi, machine_failure FROM {TABLE_NAME} ORDER BY udi
        """
        trend_df = pd.read_sql(trend_query, engine)
        first_half = trend_df.iloc[:half]
        second_half = trend_df.iloc[half:]

        def calc_bucket_rates(df, buckets=5):
            size = max(len(df) // buckets, 1)
            rates = []
            for i in range(buckets):
                chunk = df.iloc[i * size: (i + 1) * size]
                if len(chunk) > 0:
                    rate = round(chunk['machine_failure'].mean() * 100, 2)
                    rates.append(rate)
            return rates

        trend_comparison = {
            'labels': [f'區段{i+1}' for i in range(5)],
            'first_half': calc_bucket_rates(first_half),
            'second_half': calc_bucket_rates(second_half)
        }

        return jsonify({
            'type_failure_ratios': type_failure_ratios,
            'anomaly_devices': anomaly_devices,
            'anomaly_reason_stats': anomaly_reason_stats,
            'predictive_failures': {
                'predicted_fail': predict_failure,
                'predicted_normal': predict_normal
            },
            'downtime_impact': downtime_impact,
            'trend_comparison': trend_comparison
        })
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'})

@app.route('/api/stats')
def api_stats():
    """API：從 Supabase 撈取統計資料(以 SQL 聚合)"""
    try:
        # 1. 基本聚合統計(SQL 計算)
        agg_query = f"""
            SELECT 
                COUNT(0) as total_records,
                SUM(machine_failure) as failure_count,
                AVG(air_temperature_k) as avg_air_temp,
                AVG(torque_nm) as avg_torque,
                AVG(tool_wear_min) as avg_tool_wear,
                STDDEV(rotational_speed_rpm) as std_speed,
                AVG(rotational_speed_rpm) as mean_speed
            FROM {TABLE_NAME}
        """
        agg_df = pd.read_sql(agg_query, engine)
        row = agg_df.iloc[0]
        
        total_records = int(row['total_records'])
        failure_count = int(row['failure_count'] if row['failure_count'] else 0)
        failure_rate = round((failure_count / total_records) * 100, 2) if total_records > 0 else 0
        
        # 2. 類型故障統計(SQL 分組)
        type_query = f"SELECT type, SUM(machine_failure) as failures FROM {TABLE_NAME} GROUP BY type"
        type_df = pd.read_sql(type_query, engine)
        type_stats = dict(zip(type_df['type'], type_df['failures']))

        # 3. 趨勢圖 (最近20 筆)
        trend_query = f"SELECT rotational_speed_rpm FROM {TABLE_NAME} ORDER BY udi DESC LIMIT 20"
        trend_df = pd.read_sql(trend_query, engine)
        trend_data = trend_df['rotational_speed_rpm'].iloc[::-1].tolist() # 反轉成時間序

        # 4. 異常值 (SQL 算)
        mean_s = row['mean_speed'] if row['mean_speed'] else 0
        std_s = row['std_speed'] if row['std_speed'] else 0
        anomaly_query = f"""
            SELECT COUNT(0) as anomaly_count FROM {TABLE_NAME} 
            WHERE rotational_speed_rpm > {mean_s + 2 * std_s} 
            OR rotational_speed_rpm < {mean_s - 2 * std_s}
        """
        anomalies = int(pd.read_sql(anomaly_query, engine).iloc[0, 0])

        stats = {
            'total_records': total_records,
            'failure_count': failure_count,
            'failure_rate': failure_rate,
            'type_stats': type_stats,
            'avg_air_temp': round(row['avg_air_temp'] if row['avg_air_temp'] else 0, 2),
            'avg_torque': round(row['avg_torque'] if row['avg_torque'] else 0, 2),
            'trend_data': trend_data,
            'anomalies': anomalies,
            'avg_tool_wear': round(row['avg_tool_wear'] if row['avg_tool_wear'] else 0, 2)
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)