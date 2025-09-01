# 使用官方Python 3.9运行时作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV WATERMARK_API_KEY=goodluck.yunchuang
ENV PORT=5006
ENV WATERMARK_IMAGE_PATH=logo.png

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p uploads outputs && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app/uploads /app/outputs /app
USER appuser

# 暴露端口
EXPOSE ${PORT:-5006}

# 确保非root用户对必要目录有权限
RUN chown -R appuser:appuser /app/uploads /app/outputs

# 启动应用
CMD ["python", "watermark_api.py"]