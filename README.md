# 称骨算命网站

基于 Flask 的传统命理工具网站，支持用户注册登录、VIP 会员系统、称骨计算、合婚分析、取名推荐、八字详批、黄道吉日、深度命理报告、五行开运、流年运势、姓名测评、多人对比、历史记录、六十甲子对照表、后台管理。

在线演示：https://jaraim.pythonanywhere.com

## 功能列表

### 免费功能

| 功能 | 说明 |
|------|------|
| 用户系统 | 注册/登录/登出，密码哈希存储，历史记录按用户隔离 |
| 称骨计算 | 标准称骨法 + 宫位称骨法（四柱），男/女命称骨歌 |
| 基础取名 | 八字五行补缺，单字名推荐（8个），点击可复制 |
| 多人对比 | 最多2人生辰并排对比，按骨重排序 |
| 历史记录 | 自动保存计算历史，普通用户限20条，支持删除/清空 |
| 六十甲子 | 60组干支/生肖/纳音对照表，支持搜索 |

### VIP 专属功能（10项）

| 功能 | 说明 |
|------|------|
| 深度报告 | 性格、事业、财运、婚姻、健康、大运全方位分析 |
| 合婚分析 | 两人八字从生肖、五行、日柱、骨重四维分析，百分制评分 |
| 高级取名 | 12个双字名方案 + 三才五格分析 + 逐字寓意详解 |
| 八字详批 | 十神分析、日主强弱、用神忌神、8步大运排盘、藏干五行统计 |
| 黄道吉日 | 结婚/开业/搬家/出行/安葬择日，建除十二神+黄道黑道，综合评分 |
| 五行开运 | 喜用神、幸运颜色/数字/方位、适合行业、推荐饰品、开运建议 |
| 流年运势 | 未来5/10/15年逐年运势，十神+太岁关系+年龄+详细断语 |
| 姓名测评 | 已有姓名打分、三才五格、八字契合度、改名建议 |
| 多人对比Pro | 最多4人同时对比 |
| PDF导出 | 深度报告/合婚报告一键导出精美PDF（A4排版） |

### 后台管理

| 功能 | 说明 |
|------|------|
| 数据统计 | 总用户数、活跃用户、总计算次数、今日计算、近7天柱状图 |
| 用户管理 | 查看所有用户、禁用/启用账号、开通/取消VIP（支持天数/永久） |
| 记录管理 | 查看所有用户计算记录、删除记录 |
| 站点设置 | 管理员微信/QQ/电话、VIP定价（月卡/季卡/年卡） |

## VIP 定价（可在后台修改）

- 月卡：9.9 元
- 季卡：24.9 元
- 年卡：79 元

管理员在后台手动开通 VIP（用户微信付款后，管理员输入用户名和天数即可）。

## 快速开始

### 1. 安装依赖

```bash
pip install flask zhdate
```

### 2. 启动网站

```bash
cd chenggu_web
python app.py
```

### 3. 访问

打开浏览器访问：**http://127.0.0.1:5000**

首次使用点击"注册"创建账号，**第一个注册的用户自动成为管理员**。

## 文件结构

```
chenggu_web/
├── app.py                  # Flask 后端（路由 + API + 数据库 + 后台管理）
├── chenggu_core.py         # 核心算法（称骨/四柱/取名/合婚/八字详批/择日/三才五格）
├── init_db.py              # 数据库初始化脚本（备用，app.py 自动建表）
├── chenggu.db              # SQLite 数据库（首次运行自动生成）
├── templates/
│   ├── login.html          # 登录/注册页
│   ├── index.html          # 主功能页（12个标签页）
│   ├── admin.html          # 后台管理页
│   └── report.html         # PDF报告打印页
└── README.md               # 本文件
```

## 数据库表结构

- **users**：id, username, password_hash, is_admin, is_active, is_vip, vip_expire_at, created_at
- **history**：id, user_id, name, birth_year/month/day/hour, gender, standard_total, palace_total, song, created_at
- **site_settings**：key, value（管理员联系方式、VIP价格等）

## 部署到服务器

### 方式一：PythonAnywhere（免费，推荐新手）

1. 注册 https://www.pythonanywhere.com
2. 在 Bash 中克隆项目：
   ```bash
   git clone https://github.com/jaraim/chenggu-web.git
   cd chenggu-web
   pip install flask zhdate --user
   ```
3. 添加 Web App，选择 Python 3.10 + Flask
4. 配置 Source code、Working directory 指向 `/home/你的用户名/chenggu-web`
5. 配置 Virtualenv 指向 `/home/你的用户名/chenggu-web/venv`
6. 修改 WSGI 文件指向 app.py
7. 点击 Reload

更新代码：
```bash
cd /home/你的用户名/chenggu-web
git pull
# 然后在 Web 页面点 Reload
```

### 方式二：云服务器（Ubuntu + Nginx + Gunicorn）

```bash
# 安装
pip install gunicorn flask zhdate

# 启动（后台运行）
cd /path/to/chenggu-web
gunicorn -w 2 -b 127.0.0.1:5000 app:app

# Nginx 反向代理配置
# location / {
#     proxy_pass http://127.0.0.1:5000;
#     proxy_set_header Host $host;
#     proxy_set_header X-Real-IP $remote_addr;
# }
```

### 方式三：Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install flask zhdate gunicorn
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

## 生产环境注意事项

1. **修改密钥**：将 `app.py` 中的 `app.secret_key` 改为随机字符串
2. **关闭 debug**：生产环境将 `app.run(debug=True)` 改为 `debug=False`
3. **数据库备份**：定期备份 `chenggu.db` 文件
4. **HTTPS**：生产环境建议配置 SSL 证书

## API 接口

所有接口（除注册/登录/六十甲子/站点配置）需登录后访问。带 ⭐ 的为 VIP 专属接口。

### 认证

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/register` | POST | 注册 |
| `/api/login` | POST | 登录 |
| `/api/logout` | POST | 登出 |

### 命理功能

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/calc` | POST | 称骨计算 |
| `/api/marriage` | POST | 合婚分析（VIP看完整） |
| `/api/name` | POST | 取名推荐（VIP看双字名+三才五格） |
| `/api/deep` | POST | 深度报告（VIP看完整）⭐ |
| `/api/compare` | POST | 多人对比（VIP最多4人） |
| `/api/bazi-detail` | POST | 八字详批 ⭐ |
| `/api/wuxing-luck` | POST | 五行开运指南 ⭐ |
| `/api/liunian` | POST | 流年运势详解 ⭐ |
| `/api/name-eval` | POST | 姓名测评 ⭐ |
| `/api/select-day` | POST | 黄道吉日查询 ⭐ |

### 历史记录

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/history` | GET/DELETE | 历史记录列表/清空 |
| `/api/history/<id>` | DELETE | 删除单条历史 |

### 配置

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/jiazi` | GET | 六十甲子表 |
| `/api/settings` | GET | 站点配置（VIP价格+管理员联系方式） |

### 管理员（需管理员权限）

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/admin/stats` | GET | 数据统计 |
| `/api/admin/users` | GET | 用户列表 |
| `/api/admin/users/<id>/toggle` | POST | 禁用/启用用户 |
| `/api/admin/users/<id>/vip` | POST/DELETE | 开通/取消VIP |
| `/api/admin/history` | GET | 所有计算记录 |
| `/api/admin/history/<id>` | DELETE | 删除记录 |
| `/api/admin/settings` | POST | 修改站点配置 |

## 技术栈

- **后端**：Python 3.10+ / Flask
- **数据库**：SQLite（零配置，单文件）
- **前端**：原生 HTML/CSS/JavaScript（无框架依赖）
- **农历转换**：zhdate
- **部署**：PythonAnywhere / Gunicorn + Nginx / Docker

## 免责声明

本站内容基于传统命理文化，仅供娱乐参考，不构成任何人生决策建议。
