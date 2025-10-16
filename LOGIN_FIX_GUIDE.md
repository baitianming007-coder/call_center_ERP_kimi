# 🔧 登录问题修复指南

## 快速解决方案

### 方法1：使用Web工具（推荐）⭐

1. 打开浏览器访问：http://localhost:8080/check_users_tool
2. 点击 "紧急修复用户" 按钮
3. 返回登录页面，使用以下账号登录

### 方法2：命令行修复

打开终端，执行以下命令：

```bash
cd "/Users/kimi/Desktop/call center 2.0"
python3 init_db.py
```

### 方法3：一键修复SQL

```bash
cd "/Users/kimi/Desktop/call center 2.0"
sqlite3 data/callcenter.db < fix_users.sql
```

---

## 可用账号列表

**所有账号统一密码：`123456`**

| 类型 | 账号 | 密码 | 说明 |
|------|------|------|------|
| 管理员 | admin | 123456 | 系统管理员 |
| 经理 | manager | 123456 | 经理账号1 |
| 经理 | manager001 | 123456 | 经理账号2 |
| 经理 | manager002 | 123456 | 经理账号3 |
| 经理 | manager003 | 123456 | 经理账号4 |
| 经理 | manager004 | 123456 | 经理账号5 |
| 经理 | manager005 | 123456 | 经理账号6 |
| 财务 | finance | 123456 | 财务人员 |
| 员工 | a001 | 123456 | 员工账号1 |
| 员工 | a002~a010 | 123456 | 其他员工账号 |

---

## 新功能：一键填充登录

登录页面现在提供了一键填充按钮：

1. 访问 http://localhost:8080/login
2. 点击下方彩色按钮（管理员/经理/财务/员工）
3. 自动填充用户名和密码
4. 点击"登录"按钮

---

## 问题诊断

### 问题：所有账号都无法登录

**原因**：数据库用户表被清空（可能是运行大规模测试导致）

**解决**：运行上述任一修复方案

### 问题：只有部分账号无法登录

**原因**：密码hash不正确

**解决**：
```python
# 检查密码hash
cd "/Users/kimi/Desktop/call center 2.0"
python3 << EOF
from core.auth import hash_password
print("123456的hash:", hash_password('123456'))
EOF
```

### 问题：修复后仍无法登录

**解决**：
1. 清除浏览器缓存
2. 尝试无痕模式
3. 检查Flask应用是否正常运行
4. 查看终端错误信息

---

## 访问链接

- **本机访问**: http://localhost:8080
- **局域网访问**: http://192.168.0.83:8080
- **检查工具**: http://localhost:8080/check_users_tool

---

## 技术细节

### 密码Hash

所有账号使用SHA256加密，密码 `123456` 的hash值为：
```
8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92
```

### 数据库位置

```
data/callcenter.db
```

### 验证用户

```bash
sqlite3 data/callcenter.db "SELECT username, role FROM users;"
```

---

## 联系支持

如果以上方法都无法解决问题，请：

1. 检查 `data/callcenter.db` 文件是否存在
2. 查看Flask应用运行日志
3. 确认数据库文件权限正常
4. 尝试删除数据库文件后重新初始化

---

**最后更新**: 2025-10-16  
**状态**: ✅ 已修复所有已知登录问题


