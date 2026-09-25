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
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            is_vip INTEGER DEFAULT 0,
            vip_expire_at TEXT,
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
        CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    # 兼容旧表：添加字段（如果不存在）
    for col, typ in [('is_admin', 'INTEGER DEFAULT 0'), ('is_active', 'INTEGER DEFAULT 1'),
                     ('is_vip', 'INTEGER DEFAULT 0'), ('vip_expire_at', 'TEXT')]:
        try:
            db.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass
    # 初始化默认站点配置
    defaults = {
        'admin_wechat': '',
        'admin_qq': '',
        'admin_phone': '',
        'admin_note': '请联系管理员开通VIP',
        'vip_monthly': '9.9',
        'vip_quarterly': '24.9',
        'vip_yearly': '79',
    }
    for k, v in defaults.items():
        db.execute("INSERT OR IGNORE INTO site_settings (key, value) VALUES (?, ?)", (k, v))
    db.commit()
    db.close()


def get_setting(key, default=''):
    """读取站点配置。"""
    try:
        db = get_db()
        row = db.execute('SELECT value FROM site_settings WHERE key=?', (key,)).fetchone()
        return row['value'] if row else default
    except Exception:
        return default


def get_all_settings():
    """读取全部站点配置。"""
    try:
        db = get_db()
        rows = db.execute('SELECT key, value FROM site_settings').fetchall()
        return {r['key']: r['value'] for r in rows}
    except Exception:
        return {}


# 模块加载时自动建表（WSGI 模式下也能生效，修复注册报错）
init_db()


# ===================== 登录装饰器 =====================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '未登录'}), 401
        return f(*args, **kwargs)
    return decorated


def is_vip(user):
    """检查用户是否为有效VIP（未过期）。"""
    if not user:
        return False
    if user.get('is_admin'):
        return True  # 管理员默认享有VIP权限
    if not user.get('is_vip'):
        return False
    expire = user.get('vip_expire_at')
    if not expire:
        return True  # 永久VIP
    return expire > datetime.datetime.now().strftime('%Y-%m-%d')


def current_user():
    if 'user_id' in session:
        db = get_db()
        row = db.execute('SELECT id, username, is_admin, is_active, is_vip, vip_expire_at FROM users WHERE id=?', (session['user_id'],)).fetchone()
        if row and row['is_active']:
            user = {'id': row['id'], 'username': row['username'], 'is_admin': bool(row['is_admin']),
                    'is_vip': bool(row['is_vip']), 'vip_expire_at': row['vip_expire_at']}
            user['vip_valid'] = is_vip(user)
            return user
    return None


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({'error': '未登录'}), 401
        if not user.get('is_admin'):
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated


# ===================== 页面路由 =====================

@app.route('/')
def index():
    user = current_user()
    if not user:
        return render_template('login.html')
    return render_template('index.html', username=user['username'],
                           is_admin=user.get('is_admin', False),
                           is_vip=user.get('vip_valid', False))


@app.route('/admin')
def admin_page():
    user = current_user()
    if not user or not user.get('is_admin'):
        return render_template('login.html')
    return render_template('admin.html', username=user['username'])


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
    # 第一个注册的用户自动成为管理员
    is_admin = 1 if db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0 else 0
    db.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
               (username, generate_password_hash(password), is_admin))
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
    if not row['is_active']:
        return jsonify({'error': '账号已被禁用，请联系管理员'}), 403
    session['user_id'] = row['id']
    session['username'] = row['username']
    user = {'id': row['id'], 'username': row['username'], 'is_admin': bool(row['is_admin']),
            'is_vip': bool(row['is_vip']), 'vip_expire_at': row['vip_expire_at']}
    return jsonify({'ok': True, 'username': row['username'], 'is_admin': bool(row['is_admin']),
                    'is_vip': is_vip(user)})


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
    user = current_user()
    vip = is_vip(user)
    # 非VIP最多对比2人
    if not vip and len(people) > 2:
        return jsonify({'error': '普通用户最多对比2人，开通VIP可对比4人', 'need_vip': True}), 403
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
        count, day_master, xi, reason, single_names, double_names = core.recommend_names(surname, gender, pillars)
    except Exception as e:
        return jsonify({'error': f'计算出错：{e}'}), 500
    user = current_user()
    vip = is_vip(user)
    result = {
        'surname': surname, 'gender': gender,
        'pillars': pillars,
        'wuxing': count, 'day_master': day_master,
        'day_master_wuxing': core.TIANGAN_WUXING[day_master],
        'xi': xi, 'reason': reason,
        'is_vip': vip,
        'single_names': single_names,  # 单字名（免费）
    }
    if vip:
        # VIP：双字名 + 三才五格 + 寓意详解
        result['double_names'] = double_names
        # 为每个双字名生成详细分析（取前6个展示详情，其余只列名字）
        details = []
        for name in double_names[:6]:
            given = name[len(surname):]
            details.append(core.name_detail(surname, given))
        result['name_details'] = details
        result['locked'] = False
    else:
        result['double_names'] = []
        result['name_details'] = []
        result['locked'] = True
    return result


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
    user = current_user()
    result['is_vip'] = is_vip(user)
    # 非VIP只返回评分和等级，详细分析锁定
    if not is_vip(user):
        result['locked'] = True
        result['shengxiao'] = result['shengxiao'][:20] + '…（开通VIP查看完整分析）'
        result['wuxing'] = '开通VIP查看五行互补分析'
        result['rizhu'] = '开通VIP查看日柱关系分析'
        result['guzhong'] = '开通VIP查看骨重匹配分析'
        result['advice'] = '开通VIP查看综合建议'
    else:
        result['locked'] = False
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
    user = current_user()
    report['is_vip'] = is_vip(user)
    # 非VIP只返回性格和五行部分，其余锁定
    if not is_vip(user):
        report['locked'] = True
        report['career'] = '开通VIP查看事业财运分析'
        report['marriage'] = '开通VIP查看婚姻感情分析'
        report['health'] = '开通VIP查看健康注意事项'
        report['dayun'] = [('开通VIP', '查看大运走势')]
        report['song'] = report['song'][:40] + '…（开通VIP查看完整称骨歌）'
    else:
        report['locked'] = False
    return jsonify(report)


# ===================== 六十甲子 API =====================

@app.route('/api/jiazi', methods=['GET'])
def jiazi():
    return jsonify([{'num': n, 'ganzhi': gz, 'shengxiao': sx, 'nayin': ny}
                    for n, gz, sx, ny in core.build_jiazi()])


# ===================== 站点配置 API =====================

@app.route('/api/settings', methods=['GET'])
def settings():
    """公开的站点配置（VIP价格、管理员联系方式）。"""
    return jsonify(get_all_settings())


@app.route('/api/admin/settings', methods=['POST'])
@admin_required
def update_settings():
    """管理员修改站点配置。"""
    data = request.get_json() or {}
    db = get_db()
    for k, v in data.items():
        db.execute("INSERT OR REPLACE INTO site_settings (key, value) VALUES (?, ?)", (k, str(v)))
    db.commit()
    return jsonify({'ok': True})


# ===================== 管理员 API =====================

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    db = get_db()
    total_users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    active_users = db.execute('SELECT COUNT(*) FROM users WHERE is_active=1').fetchone()[0]
    total_history = db.execute('SELECT COUNT(*) FROM history').fetchone()[0]
    today_history = db.execute("SELECT COUNT(*) FROM history WHERE date(created_at)=date('now')").fetchone()[0]
    # 最近7天计算量
    rows = db.execute("""SELECT date(created_at) as d, COUNT(*) as c
                         FROM history WHERE created_at >= date('now','-6 days')
                         GROUP BY date(created_at) ORDER BY d""").fetchall()
    daily = [{'date': r['d'], 'count': r['c']} for r in rows]
    return jsonify({
        'total_users': total_users, 'active_users': active_users,
        'total_history': total_history, 'today_history': today_history,
        'daily': daily,
    })


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users():
    db = get_db()
    rows = db.execute("""SELECT u.id, u.username, u.is_admin, u.is_active, u.created_at,
                         (SELECT COUNT(*) FROM history h WHERE h.user_id=u.id) as calc_count
                         FROM users u ORDER BY u.id DESC""").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/admin/users/<int:uid>/toggle', methods=['POST'])
@admin_required
def admin_toggle_user(uid):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    if user['is_admin']:
        return jsonify({'error': '不能禁用管理员账号'}), 400
    new_status = 0 if user['is_active'] else 1
    db.execute('UPDATE users SET is_active=? WHERE id=?', (new_status, uid))
    db.commit()
    return jsonify({'ok': True, 'is_active': bool(new_status)})


@app.route('/api/admin/history', methods=['GET'])
@admin_required
def admin_history():
    db = get_db()
    rows = db.execute("""SELECT h.*, u.username
                         FROM history h JOIN users u ON h.user_id=u.id
                         ORDER BY h.id DESC LIMIT 100""").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/admin/history/<int:hid>', methods=['DELETE'])
@admin_required
def admin_delete_history(hid):
    db = get_db()
    db.execute('DELETE FROM history WHERE id=?', (hid,))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/admin/users/<int:uid>/vip', methods=['POST'])
@admin_required
def admin_set_vip(uid):
    data = request.get_json() or {}
    days = int(data.get('days', 30))  # 默认开通30天，传0为永久
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    if days == 0:
        # 永久VIP
        db.execute('UPDATE users SET is_vip=1, vip_expire_at=NULL WHERE id=?', (uid,))
        expire_text = '永久'
    else:
        expire = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime('%Y-%m-%d')
        db.execute('UPDATE users SET is_vip=1, vip_expire_at=? WHERE id=?', (expire, uid))
        expire_text = expire
    db.commit()
    return jsonify({'ok': True, 'vip_expire_at': expire_text})


@app.route('/api/admin/users/<int:uid>/vip', methods=['DELETE'])
@admin_required
def admin_remove_vip(uid):
    db = get_db()
    db.execute('UPDATE users SET is_vip=0, vip_expire_at=NULL WHERE id=?', (uid,))
    db.commit()
    return jsonify({'ok': True})


# ===================== 启动 =====================

if __name__ == '__main__':
    print("=" * 50)
    print("  称骨算命网站已启动")
    print("  访问地址：http://127.0.0.1:5000")
    print("  首次使用请先注册账号（第一个注册者自动成为管理员）")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
