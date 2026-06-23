# OpenSPG + KAG 服务器部署与运行说明

本文档对应当前仓库内已固化的运行时与脚本：

- `dev/release/server/Dockerfile`
- `dev/release/server/kag-runtime-requirements.txt`
- `dev/release/server/build-local-server-image.sh`
- `dev/release/server/install-prereqs.sh`
- `dev/release/server/deploy-stack.sh`

目标：

1. 服务镜像内置 `Python + Pemja + KAG`，不依赖临时容器补丁；
2. 本地/服务器都能一键部署与验证；
3. KAG 样例可复现执行。

## 1. 一键安装服务器依赖

在目标服务器执行：

```bash
cd /path/to/openspg
chmod +x dev/release/server/install-prereqs.sh
./dev/release/server/install-prereqs.sh
```

脚本会安装：Docker / Docker Compose / JDK8 / Maven / Python3 构建依赖。

## 2. 构建并启动 OpenSPG

```bash
cd /path/to/openspg
chmod +x dev/release/server/build-local-server-image.sh dev/release/server/deploy-stack.sh

# 构建本地镜像（含 KAG + Pemja）
OPENSPG_SERVER_IMAGE_TAG=openspg-server:local ./dev/release/server/build-local-server-image.sh

# 启动全栈
OPENSPG_SERVER_IMAGE_TAG=openspg-server:local ./dev/release/server/deploy-stack.sh up

# 运行时校验（健康检查 + Python bridge 导入）
OPENSPG_SERVER_IMAGE_TAG=openspg-server:local ./dev/release/server/deploy-stack.sh verify
```

`verify` 通过时应看到 `kag/knext/pemja/bridge` 的导入路径输出。

## 3. 运行 KAG 企业抽取样例（仅企业）

```bash
cd /path/to/openspg
source KAG/.venv/bin/activate
cd KAG/kag/examples/EnterpriseNewsCompanyOnly20260227213459

# 同步项目配置（project id=2）
knext project update

# 提交 schema（仅 Company 实体）
knext schema commit

# 跑构建链路
cd builder
if [ -d ckpt ]; then mv ckpt ckpt_bak_$(date +%Y%m%d%H%M%S); fi
python indexer.py

# 导出抽样结果（Company 实体）
python export_company_sample.py
cat data/new1_company_entities.json
```

当前抽样结果（示例）：

- `英飞凌科技股份公司`
- `infineon technologies ag`

## 4. 常用运维命令

```bash
# 查看状态
./dev/release/server/deploy-stack.sh status

# 查看 server 日志
./dev/release/server/deploy-stack.sh logs

# 仅重启 server
OPENSPG_SERVER_IMAGE_TAG=openspg-server:local ./dev/release/server/deploy-stack.sh restart

# 停止全栈
./dev/release/server/deploy-stack.sh down
```

## 5. 故障排查

1. UI 任务报 `No module named 'kag'`

- 先执行 `deploy-stack.sh verify`，确认容器内 `kag/knext/pemja` 可导入。
- 如失败，重新 `build-local-server-image.sh` + `deploy-stack.sh restart`。

2. 抽样为空

- 确认是否命中旧 checkpoint：先备份/清理 `builder/ckpt` 后重跑。
- 本样例已提供 `company_only_ner` 提示词，强制只抽 `Company`。

3. 服务健康异常

- 检查 `docker ps`、`deploy-stack.sh logs`。
- 检查 8887/3306/7687/9000 端口是否冲突。

