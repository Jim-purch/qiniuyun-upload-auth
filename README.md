# Qiniu Upload Auth Service

一个基于 FastAPI 的后端服务，通过用户登录后发放七牛云上传凭证。数据库使用 SQLite，并内置管理员用户管理页面。

## 功能

- 用户注册/登录（JWT）
- 登录后获取七牛云上传凭证（uptoken）
- 管理员用户管理页面（列表、创建、编辑、删除）
- Docker 部署与 docker-compose 支持

## 运行（本地）

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 启动服务：
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
3. 访问：
   - 根路径：`http://localhost:8000/`
   - 管理员登录页：`http://localhost:8000/admin/login`
   - 管理用户：`http://localhost:8000/admin/users`

## 接口简介

- `POST /api/register`：注册用户，传入 `{ email, password }`
- `POST /api/login`：登录，返回 `access_token`，并设置 `httponly` Cookie
- `GET /api/me`：获取当前登录用户信息
- `GET /api/upload-token?key=&expires=`：获取七牛上传凭证（需登录）
  - 适用于简单场景，无策略（policy）。
  
  
- `POST /api/upload-token`：携带策略生成上传凭证（需登录）
  - Body（示例）：
    ```json
    {
      "key": "uploads/example.txt",
      "expires": 3600,
      "policy": {
        "callbackUrl": "https://yourapp.example.com/qiniu/callback",
        "callbackBody": "{\"key\":$(key),\"hash\":$(etag),\"size\":$(fsize)}",
        "callbackBodyType": "application/json",
        "mimeLimit": "image/*",
        "fsizeLimit": 5242880,
        "returnBody": "{\"key\":$(key),\"hash\":$(etag),\"size\":$(fsize)}",
        "deleteAfterDays": 7,
        "fileType": 1
      }
    }
    ```
  - `policy` 字段将原样传递给七牛 SDK 的 `upload_token(..., policy)` 用于回调、上传限制等策略控制。

## 七牛云凭证配置

在环境变量中配置：

- `QINIU_ACCESS_KEY`
- `QINIU_SECRET_KEY`
- `QINIU_BUCKET`

## 管理员账户引导

设置环境变量 `ADMIN_EMAIL` 与 `ADMIN_PASSWORD`，可通过 `POST /api/bootstrap-admin` 创建管理员。

## Docker 运行

1. 拷贝 `.env.example` 为 `.env` 并填入实际配置。
2. 启动：
   ```bash
   docker compose up --build -d
   ```
3. 数据持久化：SQLite 位于容器内 `/app/data/data.db`，已通过卷映射到本地 `./data` 目录。

## 安全与生产建议

- 修改 `JWT_SECRET_KEY`，并在生产启用 HTTPS。
- 为管理员账户设置强密码，限制公开注册（可按需调整注册逻辑）。
- 根据业务需要对 `upload_token` 的 `policy` 做更精细控制。