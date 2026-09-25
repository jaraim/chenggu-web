# 称骨算命网站

基于 Flask 的传统命理工具网站，支持用户注册登录、称骨计算、合婚分析、取名推荐、深度命理报告、多人对比、历史记录、六十甲子对照表。

## 功能列表

| 功能 | 说明 |
|------|------|
| 用户系统 | 注册/登录/登出，密码哈希存储，历史记录按用户隔离 |
| 称骨计算 | 标准称骨法 + 宫位称骨法（四柱），男/女命称骨歌 |
| 合婚分析 | 两人八字从生肖、五行、日柱、骨重四维分析，百分制评分 |
| 取名推荐 | 八字五行补缺，按性别推荐单字名/双字名，点击可复制 |
| 深度报告 | 性格、事业、财运、婚姻、健康、大运全方位分析 |
| 多人对比 | 最多4人生辰并排对比，按骨重排序 |
| 历史记录 | 自动保存计算历史，支持删除/清空 |
| 六十甲子 | 60组干支/生肖/纳音对照表，支持搜索 |

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

首次使用点击"注册"创建账号，然后登录即可使用全部功能。

## 文件结构

```
chenggu_web/
├── app.py              # Flask 后端（路由 + API + 数据库）
├── chenggu_core.py     # 核心算法（称骨/四柱/取名/合婚/深度报告）
├── init_db.py          # 数据库初始化脚本
├── chenggu.db          # SQLite 数据库（首次运行自动生成）
├── templates/
│   ├── login.html      # 登录/注册页
│   └── index.html      # 主功能页（7个标签页）
└── README.md           # 本文件
```

## 部署到服务器

### 方式一：PythonAnywhere（免费，推荐新手）

1. 注册 https://www.pythonanywhere.com
2. 上传本项目文件到 `/home/你的用户名/chenggu_web/`
3. 在 Bash 中运行：`pip install flask zhdate --user`
4. 添加 Web App，选择 Flask，路径指向 `app.py`
5. 将 `app.py` 中的 `app.secret_key` 改为随机字符串

### 方式二：云服务器（Ubuntu + Nginx + Gunicorn）

```bash
# 安装
pip install gunicorn flask zhdate

# 启动（后台运行）
cd /path/to/chenggu_web
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
   ```python
   app.secret_key = os.environ.get('SECRET_KEY', '你的随机密钥')
   ```
2. **关闭 debug**：生产环境将 `app.run(debug=True)` 改为 `debug=False`
3. **数据库备份**：定期备份 `chenggu.db` 文件
4. **HTTPS**：生产环境建议配置 SSL 证书

## API 接口

所有接口（除注册/登录/六十甲子）需登录后访问。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/register` | POST | 注册 |
| `/api/login` | POST | 登录 |
| `/api/logout` | POST | 登出 |
| `/api/calc` | POST | 称骨计算 |
| `/api/history` | GET/DELETE | 历史记录列表/清空 |
| `/api/history/<id>` | DELETE | 删除单条历史 |
| `/api/compare` | POST | 多人对比 |
| `/api/name` | POST | 取名推荐 |
| `/api/marriage` | POST | 合婚分析 |
| `/api/deep` | POST | 深度报告 |
| `/api/jiazi` | GET | 六十甲子表 |

## 免责声明

本站内容基于传统命理文化，仅供娱乐参考，不构成任何人生决策建议。
