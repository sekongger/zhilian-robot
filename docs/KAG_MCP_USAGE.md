# KAG MCP 使用说明

本文档对应仓库内新增的 `kag-mcp` sidecar 服务。

目标：

- 给外部智能体提供标准 MCP SSE 接口
- 复用现有 OpenSPG + KAG 运行时
- 默认提供只读知识问答与证据检索能力

## 1. 当前提供的功能

`kag-mcp` 当前直接复用 KAG 原生 MCP Server，默认暴露以下工具：

- `qa-pipeline`
  作用：对当前绑定的 OpenSPG/KAG 项目做问答推理，返回最终答案。
- `kb-retrieve`
  作用：检索知识库里的 SPO 三元组和文档片段，返回 `summary + references` 的 JSON。

对应实现见：

- `modules/kag/kag/mcp/server/kag_mcp_server.py`

## 2. 部署方式

### 本地或服务器直接启动

根目录已经接入 `docker-compose.yml`，默认服务名为 `kag-mcp`。

```bash
bash deploy.sh
```

如果只想启动 MCP：

```bash
docker compose --env-file .env up -d kag-mcp
```

如果不想启动 MCP：

```bash
bash deploy.sh --skip-kag-mcp
```

远端部署时也支持跳过：

```bash
bash scripts/deploy-server.sh --skip-kag-mcp
```

### 默认访问地址

```text
http://127.0.0.1:3000/sse
```

端口可通过 `KAG_MCP_PORT` 调整。

## 2.1 线上服务器与外部访问说明

仓库内默认远端部署服务器配置为：

```text
47.111.125.169
```

对应依据：

- `scripts/deploy-server.sh` 默认 `--host`
- `.env.remote` 中的数据库、OpenSPG 与 MCP 相关地址

因此，如果你把 `kag-mcp` 直接部署在当前远端机器，且云防火墙/安全组放行了 `3000` 端口，外部调用者可以直接使用：

```text
http://47.111.125.169:3000/sse
```

宿主机 Nginx 这层我也已经补上了 `/mcp/` 代理，因此还可以通过：

```text
http://47.111.125.169:8001/mcp/sse
```

但这里有两个前提：

- `kag-mcp` 服务已经在这台机器上实际启动
- `3000` 端口已经对外开放

## 2.2 2026-03-19 实测结论

我在 `2026-03-19` 对当前线上入口做了网络验证，最新结果如下：

- `http://47.111.125.169:8100`：可达，返回 `200 OK`
- `http://47.111.125.169:8000/health`：可达，`GET` 返回健康结果
- `http://47.111.125.169:8887/actuator/health`：HTTP 可达，但返回体带登录错误，说明 OpenSPG 不应直接视为匿名可用接口
- `http://47.111.125.169:3000/sse`：已验证可返回标准 SSE 响应与 `event: endpoint`
- `http://47.111.125.169:8001/mcp/sse`：已验证可通过宿主机 Nginx 反向代理返回标准 SSE 响应
- `https://ai-zhilian.quant-chi.com/mcp/sse`：源站链路已打通，但从外部客户端请求仍表现为超时，说明最外层公网网关/代理层仍需继续放通或关闭缓冲

结论要分开看：

- `47.111.125.169` 这台机器，确实是仓库里默认的部署服务器 IP
- 目前已经确认可用的地址是：
  `http://47.111.125.169:3000/sse`
  `http://47.111.125.169:8001/mcp/sse`
- 如果你要走公网 HTTPS 域名 `https://ai-zhilian.quant-chi.com/mcp/sse`，最外层域名网关还需要继续配合

## 2.3 域名与 IP 不是同一层

当前平台对外域名：

```text
https://ai-zhilian.quant-chi.com
```

我在 `2026-03-19` 实测时发现，这个域名解析到的不是 `47.111.125.169`，而是另一个网关地址。

这意味着：

- 前端域名是经过额外网关或反向代理转发的
- 如果要把 MCP 挂到现有域名下，必须在当前前端 Nginx 或更外层网关显式增加 `/mcp/` 转发

当前仓库已经把前端 Nginx 接成：

- `/mcp/` 反向代理到 `kag-mcp:3000`，用于 SSE 入口
- `/messages/` 反向代理到 `kag-mcp:3000`，用于 MCP 会话回调

推荐接入地址分三类：

- 服务器直连：`http://47.111.125.169:3000/sse`
- 宿主机 Nginx 转发：`http://47.111.125.169:8001/mcp/sse`
- 公网 HTTPS 域名：`https://ai-zhilian.quant-chi.com/mcp/sse`

如果外部网络无法直接访问 `47.111.125.169` 的端口，而只能访问公网域名，那么外部对接时应当只使用：

```text
https://ai-zhilian.quant-chi.com/mcp/sse
```

## 3. 关键环境变量

最重要的是以下几项：

- `OPENAI_API_KEY`
  用于 KAG 推理问答和总结。
- `OPENAI_API_BASE`
  Chat 模型 OpenAI 兼容接口地址。
- `OPENAI_MODEL`
  Chat 模型名称。
- `OPENSPG_BASE_URL`
  OpenSPG 服务地址。
- `KAG_PROJECT_HOST_ADDR`
  KAG 访问 OpenSPG 的地址，未显式设置时默认回落到 `OPENSPG_BASE_URL`。
- `KAG_PROJECT_ID`
  要暴露给 MCP 的 OpenSPG/KAG 项目 ID。
- `KAG_PROJECT_NAMESPACE`
  项目命名空间。
- `KAG_MCP_PORT`
  MCP SSE 端口，默认 `3000`。
- `KAG_MCP_ENABLED_TOOLS`
  可选 `qa-pipeline`、`kb-retrieve`、`all`，默认 `all`。
- `KAG_VECTOR_MODEL`
  向量模型，默认 `BAAI/bge-m3`。
- `KAG_VECTOR_DIMENSIONS`
  向量维度，默认 `1024`。

配置模板位于：

- `deploy/kag-mcp/kag_config.yaml.tmpl`

镜像入口脚本位于：

- `deploy/kag-mcp/entrypoint.sh`

## 4. 外部智能体接入方式

### Cursor

如果你是在公网环境下接入，优先使用域名地址：

在 MCP 配置中加入：

```json
{
  "mcpServers": {
    "zhilian-kag": {
      "url": "https://ai-zhilian.quant-chi.com/mcp/sse"
    }
  }
}
```

如果你是在与服务器同网段的内网环境，也可以改成：

```json
{
  "mcpServers": {
    "zhilian-kag": {
      "url": "http://47.111.125.169:8001/mcp/sse"
    }
  }
}
```

### Claude Desktop

如果你的运行环境支持 HTTP/SSE MCP，同样填入：

```json
{
  "mcpServers": {
    "zhilian-kag": {
      "url": "https://ai-zhilian.quant-chi.com/mcp/sse"
    }
  }
}
```

如果要对外网开放，建议放到反向代理后面，例如：

```text
https://your-domain.example.com/sse
```

如果你当前就是部署在仓库默认远端服务器上，也可以按下面三个地址联调：

```text
http://47.111.125.169:3000/sse
http://47.111.125.169:8001/mcp/sse
https://ai-zhilian.quant-chi.com/mcp/sse
```

对应消息回调路径会由同一域名下的 `/messages/` 代理到 MCP 服务：

```text
http://47.111.125.169:8001/messages/
https://ai-zhilian.quant-chi.com/messages/
```

其中公网 HTTPS 域名是否能真正透传 SSE，取决于最外层网关是否同时放通 `/mcp/` 与 `/messages/`。

当前仓库外部对接的默认建议是：

- 公网对接：`https://ai-zhilian.quant-chi.com/mcp/sse`
- 内网排障：`http://47.111.125.169:8001/mcp/sse`

## 4.1 联调步骤

下面是一套最小可复现的联调顺序，建议按这个顺序排查。

### Step 1：验证 SSE 入口

```bash
curl -i --http1.1 --no-buffer --max-time 10 https://ai-zhilian.quant-chi.com/mcp/sse
```

预期至少看到：

```text
HTTP/1.1 200 OK
Content-Type: text/event-stream; charset=utf-8

event: endpoint
data: /messages/?session_id=...
```

说明：

- `curl: (28) Operation timed out` 在这里通常是正常的
- SSE 是长连接，`curl` 到了 `--max-time` 会主动退出
- 关键不是是否超时，而是有没有拿到 `200 + text/event-stream + endpoint`

### Step 2：验证消息回调路径

拿上一步返回的 `session_id`，客户端后续会请求：

```text
https://ai-zhilian.quant-chi.com/messages/?session_id=...
```

如果想快速确认这条路径不是 404，可以先故意用假 `session_id`：

```bash
curl -i --http1.1 --max-time 8 'https://ai-zhilian.quant-chi.com/messages/?session_id=test'
```

预期返回类似：

```text
HTTP/1.1 400 Bad Request
Invalid session ID
```

这说明公网层已经把 `/messages/` 正确转发到 MCP 服务，而不是被前端静态页吞掉。

### Step 3：验证初始化请求可被接受

我在 `2026-03-19` 用 HTTP/SSE 手工完成过一次最小 MCP 会话验证，确认以下请求可以通过公网 HTTPS 域名被服务端接受：

- `GET /mcp/sse`
- `POST /messages/?session_id=...` with `initialize`
- `POST /messages/?session_id=...` with `notifications/initialized`
- `POST /messages/?session_id=...` with `tools/list`

服务端日志里对应返回是 `202 Accepted`，说明公网 HTTPS 域名已经不只是“页面能打开”，而是 MCP 协议链路已经接到服务端。

### Step 4：在真实 MCP 客户端里接入

推荐直接用下面任一地址：

```json
{
  "mcpServers": {
    "zhilian-kag": {
      "url": "http://47.111.125.169:8001/mcp/sse"
    }
  }
}
```

如果你的最外层公网网关已经确认支持 SSE 透传，也可以改成：

```json
{
  "mcpServers": {
    "zhilian-kag": {
      "url": "https://ai-zhilian.quant-chi.com/mcp/sse"
    }
  }
}
```

### Step 5：验证工具可见且可调用

接入后至少做两次调用：

1. `tools/list`
   预期能看到：
   `qa-pipeline`
   `kb-retrieve`
2. 实际调用一个简单问题，例如：

```text
请根据知识库回答：当前系统提供哪些 MCP 工具？
```

或：

```text
请检索“新能源电池材料”相关知识，并返回引用证据。
```

如果 `tools/list` 可见但调用失败，优先检查：

- `OPENAI_API_KEY`
- `OPENSPG_BASE_URL`
- `KAG_PROJECT_ID`
- 外层网关是否同时放通了 `/messages/`

## 5. 典型调用效果

### `qa-pipeline`

适合直接问知识库问题，例如：

```text
请根据知识库回答：某公司最近涉及哪些产业链变化？
```

### `kb-retrieve`

适合让 Agent 先拿证据，再自己组织回答，例如：

```text
请检索和“新能源电池材料”相关的知识条目，并保留引用证据。
```

## 6. 运维与排查

查看服务状态：

```bash
docker compose --env-file .env ps kag-mcp
```

查看日志：

```bash
docker compose --env-file .env logs -f kag-mcp
```

单独重建镜像：

```bash
docker compose --env-file .env build kag-mcp
docker compose --env-file .env up -d kag-mcp
```

## 7. 安全建议

当前 `kag-mcp` 本身不带鉴权。

如果要给外部调用者使用，建议至少做下面几件事：

- 不要直接把 OpenSPG `8887` 暴露到公网
- 不要直接把 `kag-mcp` 明文暴露到公网
- 使用 Nginx / 网关 / Zero Trust 层做 HTTPS 和认证
- 把模型密钥放在运行时环境变量，不要写死到镜像或仓库文件里

## 8. 当前能力边界

这次接入的是“原生 KAG MCP”，所以能力边界也很清晰：

- 已支持：知识问答、证据检索
- 未直接支持：工作流触发、图谱写入、平台管理操作

如果后续要把平台侧能力也暴露给外部智能体，建议单独再做一个 `backend-mcp-gateway`，内部调用现有 FastAPI 接口，而不是继续往 `kag-mcp` 里混写平台逻辑。
