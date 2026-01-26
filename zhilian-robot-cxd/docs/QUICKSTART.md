# 🚀 智链机器人 - 快速启动指南

本指南帮助你在 **5 分钟内**完成项目部署并运行。

---

## 📋 前置检查

在开始之前，请确保你的系统已安装：

- ✅ **Docker Desktop** 或 **Docker Engine** (版本 20.10+)
- ✅ **Docker Compose** (版本 2.0+)
- ✅ **Git**

### 验证安装

```bash
docker --version
# 输出示例: Docker version 24.0.6

docker-compose --version
# 输出示例: Docker Compose version v2.23.0

git --version
# 输出示例: git version 2.42.0
```

---

## 🎯 快速部署（2步搞定）

### 第 1 步：克隆项目

```bash
git clone https://github.com/yourusername/zhilian-robot.git
cd zhilian-robot
```

### 第 2 步：一键启动

> **✨ 无需配置**：项目已内置所有必需配置（包括 DeepSeek API 密钥），下载后可直接运行！

#### Windows 用户：

```powershell
# 启动所有服务
docker-compose up -d

# 查看运行状态
docker-compose ps
```

#### Linux/Mac 用户：

```bash
# 启动所有服务
docker-compose up -d

# 查看运行状态
docker-compose ps
```

### （可选）使用自己的 API 密钥

如果您想使用自己的 DeepSeek API 密钥：

```powershell
# Windows
notepad backend\.env

# Linux/Mac
vim backend/.env
```

修改以下参数：
```env
OPENAI_API_KEY=sk-你的密钥
```

然后重启后端服务：
```bash
docker-compose restart backend celery-worker celery-beat
```

---

## 🌐 访问应用

等待所有容器状态变为 `healthy` 后（约 1-2 分钟），在浏览器中打开：

| 服务 | 访问地址 | 说明 |
|-----|---------|------|
| 🎨 **前端界面** | http://localhost | 主应用界面 |
| 🔧 **API 文档** | http://localhost:8000/docs | Swagger 接口文档 |
| 📊 **图数据库** | http://localhost:7474 | Neo4j Browser (账号: neo4j / 密码: 见 .env) |
| 🌺 **任务监控** | http://localhost:5555 | Celery Flower |

---

## ✅ 功能验证

### 1️⃣ 测试动量热度可视化

1. 访问 http://localhost
2. 点击「图谱探索」
3. 搜索「谐波减速器」或任意实体
4. 观察视觉效果：
   - **节点颜色**：动量0-100%对应蓝→绿→橙→红
   - **光环脉动**：红色节点外围有虚线光环，1秒周期脉动
   - **粒子流动**：等待3-5秒，连接线上出现小圆点流动
   - **连接线渐变**：线条颜色根据两端节点动量渐变

### 2️⃣ 测试情报溯源

1. 点击「动态分析」（时间轴）
2. 查看动量排行榜，找到高动量实体
3. 点击实体行的「情报溯源」按钮
4. 在弹出的抽屉中查看：
   - 实体基本信息（类型、动量值、引用次数）
   - 所有相关文档列表（标题、来源、时间）
   - 动量历史趋势图（最近30天）

### 3️⃣ 测试文本分析

1. 点击「智能分析」
2. 粘贴以下测试文本：

```
特斯拉公司今日宣布，其人形机器人Optimus已完成第二代原型机开发，
采用自主研发的谐波减速器和伺服电机系统，计划在2025年实现量产。
```

3. 点击「开始分析」
4. 等待 DeepSeek 返回结果（约 3-5 秒）
5. 查看识别出的实体和关系

### 4️⃣ 测试图谱可视化

1. 点击「图谱探索」
2. 搜索「特斯拉」或任意实体
3. 调整层级滑块（1-4层）
4. 尝试拖拽节点、缩放画布、全屏显示
5. 点击节点查看详情面板

---

## 🔧 常见问题

### ❓ 容器无法启动

**症状**：`docker-compose ps` 显示某个容器 `Exited` 或 `Unhealthy`

**解决方案**：

```bash
# 1. 查看容器日志
docker-compose logs <container-name>

# 示例: 查看后端日志
docker-compose logs backend

# 2. 重启容器
docker-compose restart <container-name>

# 3. 如果仍失败，重新构建
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### ❓ DeepSeek API 报错

**症状**：分析时提示 `401 Unauthorized` 或 `API Key Invalid`

**解决方案**：

1. 检查 API Key 是否正确：
   ```bash
   # Windows
   findstr OPENAI_API_KEY backend\.env
   
   # Linux/Mac
   grep OPENAI_API_KEY backend/.env
   ```

2. 确保 API Key 以 `sk-` 开头

3. 重启后端容器：
   ```bash
   docker-compose restart backend
   ```

### ❓ 前端显示空白页

**症状**：浏览器打开 http://localhost 显示空白

**解决方案**：

1. 按 `F12` 打开浏览器开发者工具，查看 Console 错误

2. 检查后端是否启动：
   ```bash
   curl http://localhost:8000/health
   # 应返回: {"status":"ok"}
   ```

3. 重新构建前端：
   ```bash
   docker-compose build --no-cache frontend
   docker-compose up -d frontend
   ```

### ❓ 端口被占用

**症状**：启动时报错 `port is already allocated`

**解决方案**：

修改 `.env` 文件中的端口配置：

```env
# 示例：如果 80 端口被占用，改为 8080
FRONTEND_PORT=8080

# 访问地址变为: http://localhost:8080
```

---

## 📚 下一步

✅ 部署成功后，建议阅读以下文档：

- [动量热度系统说明](动量热度系统说明.md) - 理解热度计算原理和可视化效果
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - 部署检查清单

---

## 🆘 获取帮助

遇到问题？

1. 📖 查看 [README.md](README.md) 完整文档
2. 🐛 提交 [GitHub Issue](https://github.com/yourusername/zhilian-robot/issues)
3. 💬 加入社区讨论

---

<p align="center">
  <strong>🎉 恭喜！你已成功部署智链机器人！</strong>
</p>
