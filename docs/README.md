# 呼叫中心职场管理系统

## 系统概述

呼叫中心职场管理系统，覆盖员工端与管理员端的核心流程：个人业绩/薪资/信息管理，以及看板、人员管理、业绩录入、薪资统计、团队管理、收入成本分析、定制中心等功能。

## 技术栈

- **后端**: Flask 3.0 + SQLite
- **前端**: Jinja2 模板 + 原生 JavaScript + Chart.js
- **认证**: Session + SHA256 密码哈希
- **安全**: 基于角色的访问控制(RBAC) + 数据范围隔离

## 角色与权限

- **员工 (employee)**: 个人业绩、薪资、信息查看与修改
- **中层 (manager)**: 管理端功能（限团队数据）
- **高层 (admin)**: 全部管理功能 + 团队管理 + 账号管理

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python init_db.py
```

### 3. 启动应用

```bash
python app.py
```

应用将在 http://127.0.0.1:5000 启动

### 4. 默认账号

初始化后会创建以下测试账号：

- **管理员**: admin / admin123
- **经理**: manager / manager123  
- **员工**: emp001 / emp123

## 项目结构

```
call-center-2.0/
├── app.py                  # 主应用入口
├── config.py              # 配置文件
├── requirements.txt       # Python依赖
├── init_db.py            # 数据库初始化脚本
├── data/                 # 数据目录
│   └── callcenter.db    # SQLite数据库
├── core/                 # 核心业务逻辑
│   ├── database.py      # 数据库连接
│   ├── auth.py          # 认证与权限
│   ├── commission.py    # 提成计算引擎
│   ├── status_engine.py # 状态流转引擎
│   └── salary_engine.py # 薪资计算引擎
├── routes/              # 路由模块
│   ├── auth_routes.py   # 认证路由
│   ├── employee_routes.py  # 员工端路由
│   └── admin_routes.py  # 管理端路由
├── templates/           # 前端模板
│   ├── base.html       # 基础模板
│   ├── login.html      # 登录页
│   ├── employee/       # 员工端页面
│   └── admin/          # 管理端页面
└── static/             # 静态资源
    ├── css/            # 样式文件
    ├── js/             # JavaScript文件
    └── images/         # 图片资源
```

## 核心业务规则

### 日提成计算

- 1-3单: 10元/单
- 4-5单: 20元/单
- ≥6单: 30元/单

### 人员状态流转

- **trainee → C**: 在岗满3天
- **C → B**: 在岗≤6天 且 最近3天出单≥3
- **C → eliminated**: 在岗>6天 且 最近3天出单<3
- **B → A**: 在岗≤9天 且 最近6天出单≥12
- **B → C**: 在岗>9天 且 最近6天出单<12
- **A → C**: 最近6天出单≤12 或 月末(>25号)有效工作日<20

### 月度薪资计算

- **trainee**: 仅日提成
- **C**: 固定薪资(min(达标天数×30, 90)) + 日提成
- **B**: 晋级后前6天出勤×88 + 日提成
- **A**: 底薪2200 + 全勤奖(400) + 绩效奖(0/300/600/1000) + 日提成

## 安全特性

- 密码 SHA256 哈希存储
- Session 会话管理
- 基于角色的数据隔离
- 敏感信息（手机号）加密存储
- SQL注入防护
- CSRF保护

## 开发规范

### UI 设计 Token

系统采用统一的设计 Token，禁止硬编码样式：

- **主题色**: Primary(#2563EB), Success(#10B981), Warning(#F59E0B), Danger(#EF4444)
- **间距**: 4/8/12/16/24/32px
- **圆角**: 按钮8px, 卡片12px
- **字体**: 14-16px 正文, 24/20/16px 标题

### 代码规范

- 使用装饰器进行权限控制
- 数据库操作使用参数化查询
- 错误处理统一返回JSON格式
- 日志记录关键操作

## 部署建议

- **开发环境**: SQLite + Flask 开发服务器
- **生产环境**: MySQL/PostgreSQL + Gunicorn/uWSGI + Nginx
- **并发量**: SQLite适合<100并发，生产建议使用 MySQL/PostgreSQL

## 许可证

专有软件 - 仅供授权使用

## 联系支持

如有问题请联系技术支持团队


