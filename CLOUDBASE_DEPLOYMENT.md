# 腾讯云CloudBase部署指南

## 📋 目录

1. [准备工作](#准备工作)
2. [方式1：使用CloudBase CLI部署](#方式1使用cloudbase-cli部署推荐)
3. [方式2：使用腾讯云控制台部署](#方式2使用腾讯云控制台部署)
4. [配置说明](#配置说明)
5. [常见问题](#常见问题)

---

## 准备工作

### 1. 注册腾讯云账号

访问：https://cloud.tencent.com/

### 2. 开通CloudBase服务

1. 访问：https://console.cloud.tencent.com/tcb
2. 点击"新建环境"
3. 选择"按量计费"
4. 记录下你的**环境ID**（ENV_ID）

### 3. 安装必要工具

```bash
# 安装CloudBase CLI
npm install -g @cloudbase/cli

# 登录CloudBase
tcb login
```

---

## 方式1：使用CloudBase CLI部署（推荐）

### 步骤1：修改配置文件

编辑 `cloudbaserc.json`，将 `{{env.ENV_ID}}` 替换为你的环境ID：

```json
{
  "version": "2.0",
  "envId": "your-env-id-xxxxxx",  // 替换为你的环境ID
  ...
}
```

### 步骤2：初始化CloudBase框架

```bash
cd "/Users/kimi/Desktop/call center 2.0"
tcb framework deploy
```

### 步骤3：等待部署完成

部署过程大约需要3-5分钟，完成后会显示访问地址。

### 步骤4：访问应用

访问显示的URL，例如：
```
https://call-center-erp-xxxxx.ap-shanghai.app.tcloudbase.com
```

---

## 方式2：使用腾讯云控制台部署

### 步骤1：创建云托管服务

1. 访问：https://console.cloud.tencent.com/tcb/service
2. 选择你的环境
3. 点击"新建服务"
4. 输入服务名称：`call-center-erp`
5. 点击"下一步"

### 步骤2：配置镜像

#### 2.1 构建Docker镜像

在本地构建镜像：

```bash
cd "/Users/kimi/Desktop/call center 2.0"

# 构建镜像
docker build -t call-center-erp:latest .

# 测试镜像
docker run -p 8080:8080 call-center-erp:latest
```

访问 `http://localhost:8080` 测试是否正常。

#### 2.2 推送镜像到腾讯云容器镜像服务

```bash
# 登录腾讯云容器镜像服务
docker login ccr.ccs.tencentyun.com --username=你的账号

# 标记镜像
docker tag call-center-erp:latest ccr.ccs.tencentyun.com/你的命名空间/call-center-erp:latest

# 推送镜像
docker push ccr.ccs.tencentyun.com/你的命名空间/call-center-erp:latest
```

### 步骤3：配置服务

在控制台配置：

- **镜像地址**: `ccr.ccs.tencentyun.com/你的命名空间/call-center-erp:latest`
- **端口**: `8080`
- **CPU**: `1核`
- **内存**: `2GB`
- **实例数量**: `1-5`（弹性伸缩）

### 步骤4：发布版本

点击"发布版本"，等待部署完成。

---

## 配置说明

### 资源配置

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| CPU | 1核 | 基础使用足够 |
| 内存 | 2GB | 建议至少2GB |
| 最小实例 | 1 | 保证服务可用 |
| 最大实例 | 5 | 根据流量自动扩容 |

### 环境变量（可选）

如需配置环境变量，在控制台或`cloudbaserc.json`中添加：

```json
"envVariables": {
  "FLASK_ENV": "production",
  "SECRET_KEY": "your-secret-key"
}
```

### 数据持久化

**重要**: CloudBase云托管默认使用**临时存储**，容器重启后数据会丢失。

如需持久化数据库，有两种方案：

#### 方案1：使用云数据库（推荐）

1. 在CloudBase控制台开通云数据库
2. 修改 `app.py` 连接到云数据库
3. 使用MySQL或PostgreSQL

#### 方案2：使用云文件存储CFS

1. 在控制台挂载CFS
2. 将 `/app/data` 目录挂载到CFS
3. 数据会持久化保存

---

## 域名配置

### 绑定自定义域名

1. 访问：https://console.cloud.tencent.com/tcb/service
2. 选择你的服务
3. 点击"域名管理"
4. 添加自定义域名
5. 配置DNS解析（CNAME记录）

---

## 成本估算

### 免费额度（新用户）

- 云托管：免费1个月（1核2GB，1个实例）
- 流量：10GB/月
- 数据库：1GB存储

### 按量计费（免费额度用完后）

- **云托管**: 约 ¥0.055/核时 + ¥0.032/GB时
- **月成本估算**（1核2GB，24小时运行）:
  - CPU: 1核 × 24小时 × 30天 × ¥0.055 ≈ ¥40
  - 内存: 2GB × 24小时 × 30天 × ¥0.032 ≈ ¥46
  - **总计**: 约 ¥86/月

- **流量费用**: ¥0.8/GB（超过10GB后）

---

## 监控和日志

### 查看日志

```bash
# 使用CLI查看日志
tcb service log call-center-erp

# 或在控制台查看
# https://console.cloud.tencent.com/tcb/service
```

### 监控指标

在控制台可以查看：
- CPU使用率
- 内存使用率
- 请求数量
- 响应时间

---

## 常见问题

### Q1: 部署失败，显示"镜像拉取失败"

**解决方案**:
- 检查镜像地址是否正确
- 确认镜像已成功推送
- 检查容器镜像服务的访问权限

### Q2: 服务启动失败

**解决方案**:
1. 查看日志：`tcb service log call-center-erp`
2. 检查Dockerfile中的启动命令
3. 确认端口配置正确（8080）

### Q3: 无法访问服务

**解决方案**:
- 检查服务状态是否为"运行中"
- 确认安全组规则允许访问
- 检查域名DNS解析是否正确

### Q4: 数据库文件丢失

**原因**: 云托管使用临时存储，容器重启后数据会丢失

**解决方案**:
- 使用云数据库（MySQL/PostgreSQL）
- 或挂载云文件存储CFS

### Q5: 如何更新应用

```bash
# 方式1: 使用CLI（推荐）
tcb framework deploy

# 方式2: 重新构建并推送镜像
docker build -t call-center-erp:latest .
docker tag call-center-erp:latest ccr.ccs.tencentyun.com/命名空间/call-center-erp:latest
docker push ccr.ccs.tencentyun.com/命名空间/call-center-erp:latest

# 然后在控制台"发布新版本"
```

---

## 优化建议

### 1. 使用CDN加速静态资源

将CSS、JS等静态文件上传到云存储，使用CDN加速。

### 2. 配置自动扩缩容

根据实际流量设置合理的最小/最大实例数：
- 夜间低峰：1个实例
- 白天高峰：自动扩展到3-5个实例

### 3. 开启日志持久化

将日志输出到云日志服务（CLS），便于排查问题。

### 4. 配置健康检查

在控制台配置健康检查路径：`/`

---

## 完整部署流程（快速版）

```bash
# 1. 登录CloudBase
tcb login

# 2. 修改cloudbaserc.json中的envId

# 3. 部署
cd "/Users/kimi/Desktop/call center 2.0"
tcb framework deploy

# 4. 等待完成，访问显示的URL
```

---

## 技术支持

- **CloudBase文档**: https://docs.cloudbase.net/
- **云托管文档**: https://docs.cloudbase.net/run/
- **技术社区**: https://cloud.tencent.com/developer/ask

---

## 附录：文件说明

### Dockerfile
定义了Docker镜像的构建过程，包括Python环境、依赖安装、应用启动等。

### .dockerignore
指定在构建镜像时需要忽略的文件，减小镜像体积。

### cloudbaserc.json
CloudBase框架的配置文件，定义了部署参数。

---

**部署完成后，记得：**
1. ✅ 测试所有功能是否正常
2. ✅ 配置自定义域名
3. ✅ 设置监控告警
4. ✅ 定期备份数据

**祝部署顺利！** 🚀

