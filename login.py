from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse
import os
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用於 session

# --- 沿用 predictive.py 的資料庫連線設定 (從 .env 讀取) ---
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

encoded_pass = urllib.parse.quote_plus(DB_PASS)
DB_URL = f"postgresql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

# --- 鎖定機制全域變數 (簡單範例，生產環境建議使用 Redis 或資料庫) ---
# 格式: { 'acct_no': { 'fail_count': 0, 'lock_until': 0 } }
login_tracker = {}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    acct_no = request.form.get('acct_no')
    pwds = request.form.get('pwds')
    now = time.time()

    # 1. 檢查鎖定狀態
    tracker = login_tracker.get(acct_no, {'fail_count': 0, 'lock_until': 0})
    if tracker['lock_until'] > now:
        remaining = int(tracker['lock_until'] - now)
        return jsonify({
            'success': False, 
            'message': f'帳號已鎖定，請稍後再試', 
            'lock_time': remaining
        })

    try:
        # 2. 查詢帳號
        query = text("SELECT acct_no, pwds FROM user_info WHERE acct_no = :acct_no")
        with engine.connect() as conn:
            result = conn.execute(query, {"acct_no": acct_no}).fetchone()

        if not result:
            return jsonify({'success': False, 'message': '無此帳號'})

        db_acct, db_pwds = result

        # 3. 比對密碼
        if pwds == db_pwds:
            # 登入成功，重置計數並轉導
            login_tracker[acct_no] = {'fail_count': 0, 'lock_until': 0}
            session['user'] = acct_no
            return jsonify({'success': True, 'redirect': '/'})
        else:
            # 密碼錯誤，累加次數
            tracker['fail_count'] += 1
            lock_time = 0
            
            if tracker['fail_count'] >= 5:
                tracker['lock_until'] = now + 10  # 鎖定 10 秒
                tracker['fail_count'] = 0       # 鎖定後重置或不重置依需求，這裡先重置
                lock_time = 10
                msg = "密碼錯誤過多，鎖定 10 秒"
            else:
                msg = f"密碼錯誤 (剩餘 {5 - tracker['fail_count']} 次機會)"
            
            login_tracker[acct_no] = tracker
            return jsonify({'success': False, 'message': msg, 'lock_time': lock_time})

    except Exception as e:
        return jsonify({'success': False, 'message': f'資料庫錯誤: {str(e)}'})

# 跳轉至 predictive.py 的功能，這裡暫時將 predictive.py 的路由整合進來或改寫
# 註：為了讓系統完整運作，通常會將 login 路由加進 predictive.py
# 或是在此獨立執行但導向預測頁面。

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
