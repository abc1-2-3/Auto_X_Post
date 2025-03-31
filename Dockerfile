# 使用官方 Python 基礎映像
FROM python:3.9-slim

# 設置工作目錄
WORKDIR /app

# 複製當前目錄的內容到容器內的 /app 目錄
COPY . /app

# 安裝所需的 Python 依賴項
RUN pip install --no-cache-dir -r requirements.txt

# 暴露應用程序可能使用的端口（如果需要）
# EXPOSE 8000  # 如果你的應用程序需要對外提供服務，取消註釋並設置正確的端口

# 設置環境變量（可選）
#ENV PYTHONUNBUFFERED=1

# 設置容器啟動時執行的命令
CMD ["python", "main.py"]