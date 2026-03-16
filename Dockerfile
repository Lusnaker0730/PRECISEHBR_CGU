# 1. 使用官方的 Python 執行環境作為基礎映像檔
# 我們選擇 3.11-slim 版本，它比較小且與您的 app.yaml 設定一致
FROM python:3.11-slim

# 2. 設定容器內的工作目錄
WORKDIR /app

# 3. 複製依賴套件需求檔案到工作目錄
# 我們只先複製這個檔案，是為了利用 Docker 的快取機制
COPY requirements.txt .

# 4. 安裝依賴套件
# --no-cache-dir 可以減少映像檔的大小
RUN pip install --no-cache-dir -r requirements.txt

# 5. 複製應用程式的所有原始碼到工作目錄
COPY . .

# 6. 向 Docker 聲明容器將會監聽的 port
# 這與我們在 gunicorn 指令中使用的 port 一致
EXPOSE 9000

# 7. 設定容器啟動時要執行的指令
# 這與您 app.yaml 中的 entrypoint 非常相似
CMD ["gunicorn", "-b", ":9000", "--timeout", "120", "APP:app"]