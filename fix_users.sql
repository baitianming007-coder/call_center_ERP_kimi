-- 快速修复用户账号
-- 统一密码: 123456 的hash值

DELETE FROM users;

-- 插入测试账号 (密码hash: 123456)
INSERT INTO users (username, password, role) VALUES 
('admin', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'admin'),
('manager', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'manager'),
('manager001', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'manager'),
('manager002', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'manager'),
('manager003', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'manager'),
('manager004', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'manager'),
('manager005', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'manager'),
('finance', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'finance');

-- 为前10个员工创建账号
INSERT OR IGNORE INTO users (username, password, role, employee_id)
SELECT LOWER(employee_no), '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', 'employee', id
FROM employees 
WHERE is_active = 1 
LIMIT 10;




