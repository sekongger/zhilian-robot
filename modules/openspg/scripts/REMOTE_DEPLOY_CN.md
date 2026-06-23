# OpenSPG + zhilian-robot 远端部署说明

## 目标

在本地一次执行，自动完成：

1. 同步本地 `openspg` 与 `zhilian-robot` 源码到远端
2. 在远端构建 OpenSPG 本地镜像（带 Python + Pemja + KAG 运行时）
3. 启动并验证 OpenSPG
4. 启动 zhilian-robot 并联通 OpenSPG

## 目录约定

远端默认目录：

- `/root/zhilian/openspg`
- `/root/zhilian/zhilian-robot`

## 前置条件

### 本地机器

需要安装：

- `sshpass`
- `ssh`
- `rsync`

### 远端机器

需要具备：

- `docker`
- `docker compose` 插件
- root SSH 登录权限

脚本会自动安装其余依赖（Java/Maven/Python 等）。

## 一键部署命令

在本地 `openspg` 根目录执行：

```bash
chmod +x ./scripts/sync_and_remote_deploy.sh
./scripts/sync_and_remote_deploy.sh \
  --host 47.111.125.169 \
  --password '你的root密码'
```

## 可选参数

- `--user`：默认 `root`
- `--remote-root`：默认 `/root/zhilian`
- `--openspg-base-url`：写入 zhilian-robot `.env` 的 `OPENSPG_BASE_URL`，默认 `http://172.17.0.1:8887`
- `--image-tag`：OpenSPG 服务镜像标签，默认 `openspg-server:local`
- `--skip-maven-build`：是否跳过 Maven 编译（`1` 跳过、`0` 编译），默认 `1`

示例：

```bash
./scripts/sync_and_remote_deploy.sh \
  --host 47.111.125.169 \
  --user root \
  --password '你的root密码' \
  --remote-root /root/zhilian \
  --openspg-base-url http://172.17.0.1:8887 \
  --image-tag openspg-server:local \
  --skip-maven-build 1
```

## 部署后访问

- OpenSPG: `http://<服务器IP>:8887`
- zhilian 前端: `http://<服务器IP>:8100`（取决于 `.env` 的 `FRONTEND_PORT`）
- zhilian 后端: `http://<服务器IP>:8000`（取决于 `.env` 的 `BACKEND_PORT`）

## 常见问题

1. OpenSPG 构建慢

- 默认已启用 `--skip-maven-build 1`，直接复用官方 jar 进行镜像打包，一般较快。
- 如需编译本地 Java 代码，显式传 `--skip-maven-build 0`，首次会下载大量 Maven 依赖，耗时较长。

2. zhilian 无法访问 OpenSPG

- 检查远端 `/root/zhilian/zhilian-robot/.env` 中 `OPENSPG_BASE_URL` 是否可达。
- 容器访问宿主机通常用 `http://172.17.0.1:8887`。

3. 端口冲突

- OpenSPG 默认占用 `8887/3306/7474/7687/9000/9001`。
- zhilian 建议使用不同映射端口（例如 3307、7475、7688、9002、9100）。
