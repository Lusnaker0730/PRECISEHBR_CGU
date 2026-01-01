# Docker 部署指南

> **PRECISE-HBR SMART on FHIR Application - 容器化部署文檔**

## 📋 目錄

1. [快速開始](#快速開始)
2. [開發環境](#開發環境)
3. [生產環境](#生產環境)
4. [配置說明](#配置說明)
5. [常用命令](#常用命令)
6. [常見問題](#常見問題)
7. [監控和維護](#監控和維護)
8. [更新記錄](#更新記錄)

---

## 🚀 快速開始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB 可用內存

### 快速啟動（開發環境）

```bash
# 1. 複製環境變量模板
cp .env.example .env

# 2. 編輯配置（填入你的 SMART on FHIR 配置）
nano .env

# 3. 啟動服務
docker-compose up -d

# 4. 查看日志
docker-compose logs -f smart-app

# 5. 訪問應用
open http://localhost:8080
```

---

## 💻 開發環境

### 1. 配置環境變量

```bash
# 複製環境變量模板
cp .env.example .env

# 或使用本地開發模板
cp local.env.template .env

# 編輯 .env 文件，填入你的配置
nano .env  # 或使用其他編輯器
```

**必須配置的變量：**
```env
# Flask 應用密鑰（使用強密碼，至少32字符）
FLASK_SECRET_KEY=<生成安全密鑰>

# SMART on FHIR 配置
SMART_CLIENT_ID=<你的客戶端ID>
SMART_CLIENT_SECRET=<你的客戶端密鑰>
SMART_REDIRECT_URI=http://localhost:8080/callback

# FHIR 服務器配置
SMART_EHR_BASE_URL=https://fhir-myrecord.cerner.com/dstu2/ec2458f2-1e24-41c8-b71b-0e701af7583d
```

**生成安全密鑰：**
```bash
# 方法1：使用 openssl
openssl rand -base64 32

# 方法2：使用 Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 方法3：使用 PowerShell (Windows)
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

### 2. 構建並啟動容器

```bash
# 構建 Docker 鏡像
docker-compose build

# 啟動容器（後台運行）
docker-compose up -d

# 查看日志（實時）
docker-compose logs -f smart-app

# 查看容器狀態
docker-compose ps
```

### 3. 訪問應用

打開瀏覽器訪問：
- **應用主頁：** http://localhost:8080
- **健康檢查：** http://localhost:8080/health
- **CDS Services：** http://localhost:8080/cds-services

### 4. 開發環境特性

✅ **代碼熱重載** - 本地代碼掛載到容器，修改即時生效
✅ **實時日誌** - 可查看應用運行日誌
✅ **健康檢查** - 每30秒自動檢查應用狀態
✅ **自動重啟** - 容器異常會自動重啟（`unless-stopped`）
✅ **日誌輪轉** - 自動管理日誌文件（最大10MB，保留3個文件）

### 5. 停止容器

```bash
# 停止容器
docker-compose down

# 停止並刪除數據卷
docker-compose down -v
```

---

## 🏭 生產環境

### 1. 準備生產配置

```bash
# 複製生產環境模板
cp production.env.template production.env

# 編輯生產環境配置
nano production.env
```

**生產環境必須配置：**
```env
FLASK_ENV=production
FLASK_SECRET_KEY=<強密鑰-至少32字符>
SMART_CLIENT_ID=<生產客戶端ID>
SMART_CLIENT_SECRET=<生產客戶端密鑰>
SMART_REDIRECT_URI=https://your-domain.com/callback
SMART_EHR_BASE_URL=<生產FHIR服務器>
LOG_LEVEL=INFO
```

### 2. 使用生產配置啟動

```bash
# 使用生產配置構建和啟動
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 查看狀態
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 查看日誌
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

### 3. 健康檢查

```bash
# 檢查容器健康狀態
docker ps

# 測試健康檢查端點
curl http://localhost:8080/health

# 應返回：{"status": "healthy"}
```

### 4. 生產環境特性

✅ **無代碼掛載** - 代碼打包在鏡像內，不依賴主機文件
✅ **資源限制** - CPU: 1核，內存: 1GB
✅ **嚴格健康檢查** - 每15秒檢查一次
✅ **自動重啟** - 總是自動重啟（`always`）
✅ **壓縮日誌** - 優化日誌存儲

### 5. 生產環境最佳實踐

#### 使用 HTTPS（必須）

**方法1：使用 Nginx 反向代理**
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**方法2：使用 Let's Encrypt SSL**
```bash
# 安裝 Certbot
sudo apt-get install certbot python3-certbot-nginx

# 獲取證書
sudo certbot --nginx -d your-domain.com
```

#### 安全配置

- ✅ 使用強密鑰（至少32字符）
- ✅ 啟用 CSRF 保護
- ✅ 配置適當的 CORS 策略
- ✅ 限制資源訪問
- ✅ 定期更新依賴包
- ✅ 不要在日誌中記錄敏感信息

#### 監控和日誌

- ✅ 配置日誌輪轉
- ✅ 設置資源限制
- ✅ 監控容器健康狀態
- ✅ 設置告警通知
- ✅ 定期備份數據

---

## ⚙️ 配置說明

### Docker Compose 文件結構

```
smart_fhir_app/
├── Dockerfile                    # 容器鏡像定義
├── docker-compose.yml            # 基礎配置（開發環境）
├── docker-compose.prod.yml       # 生產環境覆蓋配置
├── .dockerignore                 # Docker 構建忽略文件
├── .env.example                  # 環境變量示例
├── local.env.template            # 本地開發模板
└── production.env.template       # 生產環境模板
```

### docker-compose.yml - 開發環境配置

```yaml
services:
  smart-app:
    build:
      context: .
      dockerfile: Dockerfile
    image: smart-fhir-app:latest
    container_name: smart_fhir_app
    ports:
      - "8080:8080"
    env_file:
      - .env
    volumes:
      - .:/app                    # 掛載代碼支持熱重載
      - /app/__pycache__          # 排除 Python 緩存
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped       # 自動重啟（除非手動停止）
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### docker-compose.prod.yml - 生產環境覆蓋配置

```yaml
services:
  smart-app:
    env_file:
      - production.env            # 使用生產環境變量
    volumes: []                   # 不掛載代碼
    restart: always               # 總是自動重啟
    healthcheck:
      interval: 15s               # 更頻繁的健康檢查
      timeout: 5s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: '1.0'             # CPU 限制：1核
          memory: 1G              # 內存限制：1GB
        reservations:
          cpus: '0.5'             # CPU 保留：0.5核
          memory: 512M            # 內存保留：512MB
```

### Dockerfile 說明

```dockerfile
# 使用輕量級 Python 3.11 鏡像
FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴（包括 curl 用於健康檢查）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件並安裝（利用 Docker 緩存層）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY . .

# 聲明端口
EXPOSE 8080

# 啟動應用（使用 Gunicorn）
CMD ["gunicorn", "-b", ":8080", "--timeout", "120", "--workers", "4", "APP:app"]
```

### 環境變量說明

| 變量名 | 說明 | 必需 | 默認值 | 範例 |
|--------|------|------|--------|------|
| `FLASK_ENV` | Flask 環境 | 是 | development | production |
| `FLASK_SECRET_KEY` | Flask 會話密鑰 | 是 | - | your-secret-key-32-chars |
| `SMART_CLIENT_ID` | SMART 客戶端 ID | 是 | - | your-client-id |
| `SMART_CLIENT_SECRET` | SMART 客戶端密鑰 | 否 | - | your-secret |
| `SMART_REDIRECT_URI` | OAuth 回調 URI | 是 | - | http://localhost:8080/callback |
| `SMART_EHR_BASE_URL` | FHIR 服務器 URL | 是 | - | https://fhir.cerner.com/... |
| `LOG_LEVEL` | 日誌級別 | 否 | INFO | DEBUG/INFO/WARNING/ERROR |
| `TESTING` | 測試模式 | 否 | false | true/false |

---

## 🔧 常用命令

### 容器管理

```bash
# 查看容器狀態
docker-compose ps

# 查看容器詳細信息
docker-compose config

# 查看容器資源使用
docker stats smart_fhir_app

# 重啟服務
docker-compose restart smart-app

# 停止並刪除容器
docker-compose down
```

### 日誌查看

```bash
# 查看所有日誌
docker-compose logs smart-app

# 實時查看日誌
docker-compose logs -f smart-app

# 查看最近 100 行日誌
docker-compose logs --tail=100 smart-app

# 導出日誌到文件
docker-compose logs smart-app > app.log
```

### 進入容器

```bash
# 進入容器 Bash
docker-compose exec smart-app bash

# 進入 Python 交互式環境
docker-compose exec smart-app python

# 執行一次性命令
docker-compose exec smart-app python -c "print('Hello')"
```

### 重新構建

```bash
# 重新構建鏡像
docker-compose build --no-cache

# 強制重新創建容器
docker-compose up -d --force-recreate

# 生產環境重新構建
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate
```

### 清理資源

```bash
# 停止並刪除容器、網絡
docker-compose down

# 刪除數據卷
docker-compose down -v

# 刪除鏡像
docker rmi smart-fhir-app:latest

# 清理所有未使用的鏡像和容器
docker system prune -a

# 查看磁盤使用情況
docker system df
```

---

## 🐛 常見問題

### 1. 端口已被佔用

**錯誤：**
```
Error: Bind for 0.0.0.0:8080 failed: port is already allocated
```

**解決方法：**

**選項1：修改端口映射**
```yaml
# docker-compose.yml
ports:
  - "8081:8080"  # 使用不同的主機端口
```

**選項2：查找並停止佔用端口的進程**
```bash
# Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F

# Mac/Linux
lsof -i :8080
kill -9 <PID>
```

---

### 2. 權限問題

**錯誤：**
```
Permission denied while trying to connect to the Docker daemon socket
```

**解決方法：**

**Linux：**
```bash
# 添加用戶到 docker 組
sudo usermod -aG docker $USER

# 重新登錄或執行
newgrp docker

# 驗證
docker ps
```

**Windows/Mac：**
- 確保 Docker Desktop 正在運行
- 以管理員身份運行 PowerShell/Terminal

---

### 3. 容器無法連接到 FHIR 服務器

**檢查步驟：**

1. **確認配置正確**
```bash
# 查看環境變量
docker-compose exec smart-app env | grep SMART
```

2. **測試網絡連通性**
```bash
# 進入容器測試
docker-compose exec smart-app bash
curl -I https://fhir-myrecord.cerner.com
```

3. **查看詳細日誌**
```bash
docker-compose logs smart-app | grep -i error
docker-compose logs smart-app | grep -i fhir
```

4. **檢查防火牆設置**
- 確保容器可以訪問外部 HTTPS (443) 端口

---

### 4. 環境變量未生效

**原因：**
- `.env` 文件格式錯誤
- `.env` 文件未被讀取
- 緩存的舊鏡像

**解決方法：**

```bash
# 1. 驗證 .env 文件格式（不要有空格）
cat .env
# 正確：FLASK_SECRET_KEY=value
# 錯誤：FLASK_SECRET_KEY = value

# 2. 完全重建
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 3. 驗證環境變量
docker-compose exec smart-app env | grep FLASK
```

---

### 5. 代碼更改未反映

**開發環境：**
- ✅ 檢查 `volumes` 配置是否正確
- ✅ 確認文件已保存
- ✅ 重啟容器：`docker-compose restart`

**生產環境：**
- ⚠️ 需要重新構建鏡像（生產環境不掛載代碼）
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

### 6. 健康檢查失敗

**錯誤：**
```
unhealthy: Health check failed
```

**排查步驟：**

```bash
# 1. 查看容器日誌
docker-compose logs smart-app

# 2. 手動測試健康檢查端點
curl http://localhost:8080/health

# 3. 進入容器內部測試
docker-compose exec smart-app curl http://localhost:8080/health

# 4. 檢查應用是否正常啟動
docker-compose exec smart-app ps aux | grep gunicorn
```

---

### 7. `.env` 文件找不到

**錯誤：**
```
env file F:\PreciseHBR\smart_fhir_app\.env not found
```

**解決方法：**
```bash
# 複製模板並配置
cp .env.example .env
nano .env

# 或使用本地開發模板
cp local.env.template .env
```

---

### 8. Docker Compose 版本警告

**警告：**
```
the attribute `version` is obsolete, it will be ignored
```

**說明：**
- Docker Compose v2.x 不再需要 `version` 屬性
- 此警告可以安全忽略
- 我們已經移除了 `version: '3.8'` 行

---

## 📊 監控和維護

### 查看資源使用

```bash
# 查看容器資源使用（實時）
docker stats smart_fhir_app

# 查看容器詳細信息
docker inspect smart_fhir_app

# 查看 Docker 磁盤使用
docker system df
docker system df -v
```

### 日誌管理

**查看日誌：**
```bash
# 實時日誌
docker-compose logs -f smart-app

# 查看最近 N 行
docker-compose logs --tail=100 smart-app

# 查看特定時間範圍
docker-compose logs --since 30m smart-app
docker-compose logs --since 2024-01-01T00:00:00 smart-app
```

**導出和分析日誌：**
```bash
# 導出日誌
docker-compose logs smart-app > app-$(date +%Y%m%d).log

# 搜索錯誤
docker-compose logs smart-app | grep -i error

# 統計錯誤數量
docker-compose logs smart-app | grep -i error | wc -l
```

### 健康檢查

```bash
# 檢查容器健康狀態
docker ps --format "table {{.Names}}\t{{.Status}}"

# 檢查健康檢查端點
curl -s http://localhost:8080/health | jq

# 監控健康狀態（持續）
watch -n 5 'docker ps --format "table {{.Names}}\t{{.Status}}"'
```

### 備份和恢復

**備份容器狀態：**
```bash
# 提交容器為鏡像
docker commit smart_fhir_app smart-fhir-app:backup-$(date +%Y%m%d)

# 導出鏡像
docker save smart-fhir-app:backup-$(date +%Y%m%d) -o backup-$(date +%Y%m%d).tar

# 壓縮備份
gzip backup-$(date +%Y%m%d).tar
```

**恢復備份：**
```bash
# 導入鏡像
gunzip backup-20240101.tar.gz
docker load -i backup-20240101.tar

# 運行備份鏡像
docker run -d --name smart_fhir_app_restored smart-fhir-app:backup-20240101
```

### 性能優化

**監控性能瓶頸：**
```bash
# 查看容器進程
docker-compose exec smart-app top

# 查看網絡連接
docker-compose exec smart-app netstat -an

# 查看應用性能
docker-compose exec smart-app python -m cProfile -s cumtime APP.py
```

**優化建議：**
- ✅ 增加 Gunicorn workers：`--workers 4`
- ✅ 調整超時設置：`--timeout 120`
- ✅ 使用 Redis 緩存
- ✅ 配置 CDN 加速靜態資源
- ✅ 啟用 gzip 壓縮

---

## 🚀 高級配置

### 使用 Docker Swarm 部署

```bash
# 1. 初始化 Swarm
docker swarm init

# 2. 部署服務棧
docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml smart-fhir

# 3. 查看服務
docker service ls
docker service ps smart-fhir_smart-app

# 4. 查看服務日誌
docker service logs smart-fhir_smart-app

# 5. 擴展服務
docker service scale smart-fhir_smart-app=3

# 6. 刪除服務棧
docker stack rm smart-fhir
```

### 使用 Kubernetes 部署

參考 `.github/workflows/` 中的 Kubernetes 部署配置。

### 多階段構建優化

```dockerfile
# 構建階段
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 運行階段
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8080
CMD ["gunicorn", "-b", ":8080", "APP:app"]
```

---

## 📈 更新記錄

### ✅ 最近更新（2025-11-10）

#### 配置優化
- ✅ 移除過時的 `version: '3.8'` 屬性
- ✅ 統一環境文件管理（`.env` 和 `production.env`）
- ✅ 創建 `.env.example` 和 `local.env.template`

#### 功能增強
- ✅ 添加健康檢查配置（30秒間隔）
- ✅ 添加自動重啟策略（`unless-stopped` / `always`）
- ✅ 配置日誌輪轉（最大10MB，保留3個文件）
- ✅ 生產環境資源限制（CPU: 1核，內存: 1GB）

#### 生產部署
- ✅ 創建 `docker-compose.prod.yml` 生產配置
- ✅ 更嚴格的健康檢查（15秒間隔）
- ✅ 不掛載本地代碼（生產環境）
- ✅ 壓縮日誌存儲

### 📊 改進對比

| 特性 | 更新前 | 更新後 |
|------|--------|--------|
| 環境文件 | `docker.env`（不存在） | `.env` / `production.env` ✅ |
| 健康檢查 | ❌ 無 | ✅ 自動檢查（30s/15s） |
| 日誌管理 | ❌ 無限制 | ✅ 10MB 輪轉，保留3個文件 |
| 重啟策略 | ❌ 無 | ✅ `unless-stopped` / `always` |
| 資源限制 | ❌ 無 | ✅ CPU/內存限制（生產） |
| 生產配置 | ❌ 無 | ✅ `docker-compose.prod.yml` |
| 文檔 | ❌ 分散 | ✅ 統一的完整指南 |
| Docker Compose 版本 | `version: '3.8'` | 移除（v2.x 標準） ✅ |

### 🔐 安全改進

1. **環境變量分離：** 開發和生產使用不同的環境文件
2. **不暴露敏感信息：** `.env` 文件被 `.gitignore` 忽略
3. **示例文件：** 提供 `.env.example` 作為參考
4. **資源隔離：** 生產環境明確的資源限制
5. **日誌保護：** 不在日誌中記錄 ePHI 和敏感信息

---

## 📚 相關文檔

- [Docker 官方文檔](https://docs.docker.com/)
- [Docker Compose 文檔](https://docs.docker.com/compose/)
- [項目 CI/CD 文檔](README_CI_CD.md)
- [項目結構說明](PROJECT_STRUCTURE.md)
- [PRECISE-HBR 說明](PRECISE-HBR.md)

---

## 🆘 需要幫助？

### 問題排查流程

1. ✅ 查看本文檔的[常見問題](#常見問題)部分
2. ✅ 檢查容器日誌：`docker-compose logs smart-app`
3. ✅ 驗證環境配置：`docker-compose config`
4. ✅ 測試健康檢查：`curl http://localhost:8080/health`
5. ✅ 查看項目文檔：[docs/](docs/)

### 獲取支持

- 📖 查看[項目文檔](docs/)
- 🐛 提交 [GitHub Issue](https://github.com/Lusnaker0730/smart_fhir_app/issues)
- 💬 聯系開發團隊

---

**最後更新：** 2025年11月10日  
**維護者：** PRECISE-HBR 開發團隊  
**狀態：** ✅ 已完成並測試

