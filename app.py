# -*- coding: utf-8 -*-
"""
称骨算命网站 - Flask 后端
运行：pip install flask zhdate && python app.py
访问：http://127.0.0.1:5000
"""
import os
import sqlite3
import datetime
from functools import wraps
from flask import Flask, request, session, jsonify, render_template, g
from werkzeug.security import generate_password_hash, check_password_hash
import chenggu_core as core

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chenggu_secret_key_change_in_production')
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chenggu.db')


# ===================== 数据库 =====================

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT DEFAULT '',
            birth_year INTEGER,
            birth_month INTEGER,
            birth_day INTEGER,
            birth_hour INTEGER,
            gender TEXT,
            standard_total REAL,
            palace_total REAL,
            song TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    db.commit()
    db.close()


# ===================== 登录装饰器 =====================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '未登录'}), 401
        return f(*args, **kwargs)
    return decorated


def current_user():
    if 'user_id' in session:
        db = get_db()
        row = db.execute('SELECT id, username FROM users WHERE id=?', (session['user_id'],)).fetchone()
        if row:
            return {'id': row['id'], 'username': row['username']}
    return None


# ===================== 页面路由 =====================

@app.route('/')
def index():
    user = current_user()
    if not user:
        return render_template('login.html')
    return render_template('index.html', username=user['username'])


# ===================== 认证 API =====================

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if len(username) < 2:
        return jsonify({'error': '用户名至少2个字符'}), 400
    if len(password) < 6:
        return jsonify({'error': '密码至少6位'}), 400
    db = get_db()
    if db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
        return jsonify({'error': '用户名已存在'}), 400
    db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
               (username, generate_password_hash(password)))
    db.commit()
    return jsonify({'ok': True, 'message': '注册成功，请登录'})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    db = get_db()
    row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    if not row or not check_password_hash(row['password_hash'], password):
        return jsonify({'error': '用户名或密码错误'}), 401
    session['user_id'] = row['id']
    session['username'] = row['username']
    return jsonify({'ok': True, 'username': row['username']})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/user', methods=['GET'])
def get_user():
    user = current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    return jsonify(user)


# ===================== 称骨计算 API =====================

@app.route('/api/calc', methods=['POST'])
@login_required
def calc():
    data = request.get_json()
    try:
        y = int(data['year']); m = int(data['month']); d = int(data['day'])
        h = int(data.get('hour', 12)); gender = data.get('gender', '男')
        name = (data.get('name') or '').strip()
        if not 1900 <= y <= 2100 or not 1 <= m <= 12 or not 1 <= d <= 31 or not 0 <= h <= 23:
            return jsonify({'error': '日期范围不正确'}), 400
    except (ValueError, KeyError):
        return jsonify({'error': '请填写有效的数字'}), 400

    try:
        s = core.standard_bone_weight(y, m, d, h)
        p = core.palace_bone_weight(y, m, d, h)
    except Exception as e:
        return jsonify({'error': f'计算出错：{e}'}), 500

    song = (core.MALE_SONGS if gender == '男' else core.FEMALE_SONGS).get(s['total'], '（暂无）')

    # 保存历史
    db = get_db()
    db.execute('''INSERT INTO history (user_id,name,birth_year,birth_month,birth_day,birth_hour,gender,standard_total,palace_total,song)
                  VALUES (?,?,?,?,?,?,?,?,?,?)''',
               (session['user_id'], name, y, m, d, h, gender, s['total'], p['total'], song))
    db.commit()

    return jsonify({
        'name': name, 'gender': gender,
        'solar': f'{y}年{m}月{d}日 {h:02d}时',
        'lunar': f"{s['gz']}年 {s['lunar_month']}月{s['lunar_day']}日 {s['shichen']}",
        'standard': {
            'gz': s['gz'], 'y': s['y'], 'm': s['m'], 'd': s['d'], 't': s['t'],
            'total': s['total'], 'total_text': core.weight_text(s['total']),
            'y_text': core.weight_text(s['y']), 'm_text': core.weight_text(s['m']),
            'd_text': core.weight_text(s['d']), 't_text': core.weight_text(s['t']),
        },
        'palace': {
            'year_p': p['year_p'], 'month_p': p['month_p'], 'day_p': p['day_p'], 'hour_p': p['hour_p'],
            'y': p['y'], 'm': p['m'], 'd': p['d'], 't': p['t'],
            'total': p['total'], 'total_text': core.palace_text(p['total']),
            'y_text': core.palace_text(p['y']), 'm_text': core.palace_text(p['m']),
            'd_text': core.palace_text(p['d']), 't_text': core.palace_text(p['t']),
        },
        'song': song,
    })


# ===================== 历史记录 API =====================

@app.route('/api/history', methods=['GET'])
@login_required
def history_list():
    db = get_db()
    rows = db.execute('''SELECT * FROM history WHERE user_id=? ORDER BY id DESC LIMIT 50''',
                      (session['user_id'],)).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/history/<int:hid>', methods=['DELETE'])
@login_required
def history_delete(hid):
    db = get_db()
    db.execute('DELETE FROM history WHERE id=? AND user_id=?', (hid, session['user_id']))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/history', methods=['DELETE'])
@login_required
def history_clear():
    db = get_db()
    db.execute('DELETE FROM history WHERE user_id=?', (session['user_id'],))
    db.commit()
    return jsonify({'ok': True})


# ===================== 多人对比 API =====================

@app.route('/api/compare', methods=['POST'])
@login_required
def compare():
    data = request.get_json()
    people = data.get('people', [])
    if len(people) < 2:
        return jsonify({'error': '至少填写2人'}), 400
    results = []
    for pp in people:
        try:
            y = int(pp['year']); m = int(pp['month']); d = int(pp['day'])
            h = int(pp.get('hour', 12)); gender = pp.get('gender', '男')
            name = (pp.get('name') or '').strip() or '未命名'
            s = core.standard_bone_weight(y, m, d, h)
            p = core.palace_bone_weight(y, m, d, h)
            song = (core.MALE_SONGS if gender == '男' else core.FEMALE_SONGS).get(s['total'], '（暂无）')
            results.append({
                'name': name, 'gender': gender,
                'birth': f'{y}-{m:02d}-{d:02d} {h:02d}时',
                'lunar': f"{s['gz']}年{s['lunar_month']}月{s['lunar_day']}日{s['shichen']}",
                'standard_total': s['total'], 'standard_text': core.weight_text(s['total']),
                'palace_total': p['total'], 'palace_text': core.palace_text(p['total']),
                'pillars': [p['year_p'], p['month_p'], p['day_p'], p['hour_p']],
                'song': song,
            })
        except Exception as e:
            return jsonify({'error': f'{name}计算出错：{e}'}), 400
    results.sort(key=lambda x: x['standard_total'], reverse=True)
    return jsonify({'people': results})


# ===================== 取名推荐 API =====================

@app.route('/api/name', methods=['POST'])
@login_required
def name_recommend():
    data = request.get_json()
    try:
        surname = (data.get('surname') or '').strip()
        if not surname:
            return jsonify({'error': '请填写姓氏'}), 400
        y = int(data['year']); m = int(data['month']); d = int(data['day'])
        h = int(data.get('hour', 12)); gender = data.get('gender', '男')
    except (ValueError, KeyError):
        return jsonify({'error': '请填写有效的数字'}), 400
    try:
        p = core.palace_bone_weight(y, m, d, h)
        pillars = [p['year_p'], p['month_p'], p['day_p'], p['hour_p']]
        count, day_master, xi, reason, names = core.recommend_names(surname, gender, pillars)
    except Exception as e:
        return jsonify({'error': f'计算出错：{e}'}), 500
    return jsonify({
        'surname': surname, 'gender': gender,
        'pillars': pillars,
        'wuxing': count, 'day_master': day_master,
        'day_master_wuxing': core.TIANGAN_WUXING[day_master],
        'xi': xi, 'reason': reason, 'names': names,
    })


# ===================== 合婚 API =====================

@app.route('/api/marriage', methods=['POST'])
@login_required
def marriage():
    data = request.get_json()
    try:
        p1_data = data['p1']; p2_data = data['p2']
        p1 = core.palace_bone_weight(int(p1_data['year']), int(p1_data['month']),
                                     int(p1_data['day']), int(p1_data.get('hour', 12)))
        p2 = core.palace_bone_weight(int(p2_data['year']), int(p2_data['month']),
                                     int(p2_data['day']), int(p2_data.get('hour', 12)))
        name1 = (p1_data.get('name') or '').strip() or '甲方'
        name2 = (p2_data.get('name') or '').strip() or '乙方'
    except (ValueError, KeyError):
        return jsonify({'error': '请填写两人的有效出生日期'}), 400
    try:
        result = core.marriage_match(p1, p2)
    except Exception as e:
        return jsonify({'error': f'合婚分析出错：{e}'}), 500
    result['name1'] = name1
    result['name2'] = name2
    return jsonify(result)


# ===================== 深度报告 API =====================

@app.route('/api/deep', methods=['POST'])
@login_required
def deep():
    data = request.get_json()
    try:
        y = int(data['year']); m = int(data['month']); d = int(data['day'])
        h = int(data.get('hour', 12)); gender = data.get('gender', '男')
        name = (data.get('name') or '').strip() or '命主'
    except (ValueError, KeyError):
        return jsonify({'error': '请填写有效的数字'}), 400
    try:
        report = core.deep_report(name, gender, y, m, d, h)
    except Exception as e:
        return jsonify({'error': f'生成报告出错：{e}'}), 500
    report['standard_text'] = core.weight_text(report['standard_total'])
    report['palace_text'] = core.palace_text(report['palace_total'])
    return jsonify(report)


# ===================== 六十甲子 API =====================

@app.route('/api/jiazi', methods=['GET'])
def jiazi():
    return jsonify([{'num': n, 'ganzhi': gz, 'shengxiao': sx, 'nayin': ny}
                    for n, gz, sx, ny in core.build_jiazi()])


# ===================== 启动 =====================

if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("  称骨算命网站已启动")
    print("  访问地址：http://127.0.0.1:5000")
    print("  首次使用请先注册账号")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
