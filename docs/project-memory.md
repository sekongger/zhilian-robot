# 项目记忆

更新时间：2026-03-17

## 线上部署

线上标准发布唯一推荐入口：

```bash
cd /Users/youfang/Documents/zhilian-robot
bash scripts/deploy-server.sh --remove-legacy-copy
```

补充说明：

- 目标服务器：`47.111.125.169`
- 远端代码目录：`/root/zhilian-robot`
- 旧目录：`/root/zhilian/zhilian-robot`
- 该脚本会：
  - 通过 `ssh + rsync` 同步当前工作区
  - 保留远端 `.env` / `.env.remote`
  - 重启 OpenSPG 栈
  - 在远端执行 `bash deploy.sh --skip-pull`

常用变体：

```bash
# 只重启远端，不重新 rsync
bash scripts/deploy-server.sh --skip-rsync

# 如果改了 modules/openspg，并希望远端用本地源码构建 OpenSPG
bash scripts/deploy-server.sh --build-local-openspg-image --remove-legacy-copy
```

## 当前主链

当前前台主入口主链为：

```text
OpenKS describe()
-> schema adapter
-> KAG sync_schema()
-> OpenSPG
-> KnowledgeRun / KnowledgeArtifact / ServiceRelease
```

`openks_direct` 仍保留在后端中，但不再作为主 UI 的默认链路。
