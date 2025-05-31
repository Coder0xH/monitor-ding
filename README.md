# TradingView Alert to DingTalk Monitor

一个基于FastAPI的服务，用于接收TradingView警报并转发到钉钉群组。

## 功能特性

- 🚀 基于FastAPI的高性能Web服务
- 📊 接收TradingView警报数据
- 💬 自动转发警报到钉钉群组
- 🔍 完整的日志记录
- 🧪 内置测试接口
- 📝 详细的API文档

## 项目结构

```
monitor/
├── main.py              # 主应用文件
├── pyproject.toml       # 项目配置和依赖
├── README.md           # 项目说明
├── .gitignore          # Git忽略文件
└── .python-version     # Python版本配置
```

## 安装和运行

### 前提条件

- Python 3.11+
- uv (Python包管理器)

### 安装依赖

```bash
# 同步项目依赖
uv sync
```

### 运行服务

```bash
# 使用uv运行
uv run python main.py

# 或者激活虚拟环境后运行
source .venv/bin/activate  # macOS/Linux
python main.py
```

服务将在 `http://localhost:8000` 启动。


## 消息格式

钉钉群组将收到格式化的警报消息：

```
🟢 TradingView Alert

📊 Symbol: BTCUSDT
🎯 Action: BUY
💰 Price: $45000.0
⏰ Time: 2024-01-01T12:00:00
📝 Message: 突破阻力位
```

## 开发

### 查看API文档

启动服务后，访问以下地址查看自动生成的API文档：

- Swagger UI: `http://localhost:8000/docs`

### 日志

应用使用Python标准logging模块记录日志，包括：

- 接收到的警报信息
- 钉钉发送状态
- 错误信息

### 测试

使用curl测试API：

```bash
# 测试健康检查
curl http://localhost:8000/

# 测试警报接收
curl -X POST http://localhost:8000/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "action": "BUY",
    "price": 45000.0,
    "message": "测试警报"
  }'
```

## 部署

### 生产环境运行

```bash
# 使用uvicorn直接运行
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# 或者使用gunicorn (需要额外安装)
uv add gunicorn
uv run gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv && uv sync

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 许可证

MIT License

## 作者

Dexter - 2025# monitor-ding
