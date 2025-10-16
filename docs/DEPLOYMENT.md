# 部署指南

**版本**: v1.5.0  
**更新**: 2025-10-15

---

## 快速部署

### 1. 环境准备

```bash
# 确保Python 3.9+
python3 --version

# 进入项目目录
cd "/Users/kimi/Desktop/call center 2.0"
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

**依赖清单**:
- Flask 3.0.0
- cryptography 41.0.7
- openpyxl 3.1.2
- reportlab 4.0.7
- PyPDF2 3.0.1
- pandas 2.1.4

### 3. 数据库初始化

数据库文件: `call_center.db`

如需重新初始化:
```bash
python init_db.py
python init_test_data_advanced.py  # 可选：生成测试数据
```

### 4. 启动服务

```bash
python app.py
```

访问: http://127.0.0.1:8080

### 5. 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | 123456 |
| 经理 | manager | 123456 |
| 财务 | finance | 123456 |
| 员工 | a001 | 123456 |

---

## 功能验证

### 核心功能检查清单

- [ ] 登录所有角色
- [ ] 员工管理（查看、添加、编辑）
- [ ] 业绩录入（单条、批量、Excel导入）
- [ ] 状态检查与晋升
- [ ] 薪资计算与查看
- [ ] 工资单生成
- [ ] 报表查看

### 快速测试

```bash
python tests/expert_final_test.py
```

---

## 生产部署建议

### 安全加固

1. **修改默认密码**
```python
# 首次登录后立即修改所有默认密码
```

2. **HTTPS配置**
```bash
# 使用nginx反向代理 + SSL证书
```

3. **数据库备份**
```bash
# 定期备份call_center.db
cp call_center.db backup/call_center_$(date +%Y%m%d).db
```

### 性能优化

1. **启用静态文件压缩**
```html
<!-- 使用压缩版CSS -->
<link rel="stylesheet" href="/static/css/main.min.css">
```

2. **配置缓存**
```python
# 已实现: core/cache.py
```

3. **数据库索引**
```bash
# 执行索引优化（生产环境）
sqlite3 call_center.db < optimize_indexes.sql
```

---

## 监控与维护

### 日志位置
- 应用日志: 控制台输出
- 审计日志: `audit_logs` 表

### 常见问题

**Q: 8080端口被占用**
```bash
# 修改 app.py 中的端口号
app.run(host='0.0.0.0', port=8081)
```

**Q: 数据库锁定**
```bash
# SQLite并发限制，生产环境建议切换到PostgreSQL/MySQL
```

**Q: 性能慢**
```bash
# 检查数据量，定期清理历史数据
# 考虑分库分表
```

---

## 升级指南

### 从旧版本升级

1. 备份数据库
2. 更新代码
3. 运行迁移脚本
4. 重启服务
5. 验证功能

---

## 技术支持

- 文档: `docs/`
- 进度: `docs/PROGRESS.md`
- 问题: 查看 `DELIVERY.md`

---

**部署完成后，建议运行完整测试确保所有功能正常！**

