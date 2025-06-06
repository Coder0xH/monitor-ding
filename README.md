# TradingView Alert Monitor & Binance Futures Trading API

这是一个基于 FastAPI 的服务，用于接收 TradingView 警报并转发到钉钉，同时提供币安合约交易 API 功能。

## 功能特性

### 1. TradingView 警报转发
- 接收 TradingView 警报
- 自动转发到钉钉群组
- 支持 JSON 和文本格式

### 2. 币安合约交易 API
- 创建合约订单（市价单、限价单、止损单等）
- 设置杠杆倍数
- 查询持仓信息
- 查询账户余额
- 查询未成交订单
- 取消订单
- 获取行情数据

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量示例文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的币安 API 密钥：
```bash
BINANCE_API_KEY=your_actual_api_key
BINANCE_SECRET_KEY=your_actual_secret_key
```

### 3. 币安 API 密钥配置

1. 登录 [币安官网](https://www.binance.com)
2. 进入 "API 管理" 页面
3. 创建新的 API 密钥
4. **重要：启用合约交易权限**
5. 建议设置 IP 白名单以提高安全性

## 运行服务

```bash
python main.py
```

服务将在 `http://localhost:80` 启动。

## API 接口文档

### TradingView 警报接口

#### POST /webhook/tradingview
接收 TradingView 警报并转发到钉钉

### 币安合约交易接口

#### POST /api/futures/order
创建合约订单

**请求体示例：**
```json
{
  "symbol": "BTCUSDT",
  "side": "buy",
  "type": "market",
  "amount": 0.001,
  "leverage": 10
}
```

**参数说明：**
- `symbol`: 交易对符号（如 "BTCUSDT"）
- `side`: 订单方向（"buy" 或 "sell"）
- `type`: 订单类型（"market", "limit", "stop", "take_profit"）
- `amount`: 订单数量
- `price`: 限价单价格（可选）
- `stop_price`: 止损价格（可选）
- `reduce_only`: 是否为减仓单（可选）
- `leverage`: 杠杆倍数（可选）

#### POST /api/futures/leverage
设置杠杆倍数

**请求体示例：**
```json
{
  "symbol": "BTCUSDT",
  "leverage": 20
}
```

#### GET /api/futures/positions
获取所有持仓信息

#### GET /api/futures/balance
获取合约账户余额

#### GET /api/futures/orders/{symbol}
获取指定交易对的未成交订单

#### DELETE /api/futures/orders/{order_id}?symbol={symbol}
取消指定订单

#### GET /api/futures/ticker/{symbol}
获取指定交易对的行情数据

## 使用示例

### 1. 创建市价买单

```bash
curl -X POST "http://localhost:80/api/futures/order" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "side": "buy",
    "type": "market",
    "amount": 0.001,
    "leverage": 10
  }'
```

### 2. 创建限价卖单

```bash
curl -X POST "http://localhost:80/api/futures/order" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "side": "sell",
    "type": "limit",
    "amount": 0.001,
    "price": 45000
  }'
```

### 3. 设置杠杆

```bash
curl -X POST "http://localhost:80/api/futures/leverage" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "leverage": 20
  }'
```

### 4. 查询持仓

```bash
curl "http://localhost:80/api/futures/positions"
```

### 5. 查询余额

```bash
curl "http://localhost:80/api/futures/balance"
```

## 安全注意事项

1. **API 密钥安全**：
   - 永远不要在代码中硬编码 API 密钥
   - 使用环境变量存储敏感信息
   - 定期轮换 API 密钥

2. **网络安全**：
   - 在生产环境中使用 HTTPS
   - 设置 API 密钥的 IP 白名单
   - 考虑使用防火墙限制访问

3. **权限控制**：
   - 只启用必要的 API 权限
   - 避免启用提现权限
   - 定期检查 API 使用情况

## 错误处理

所有 API 接口都包含完整的错误处理机制：

- **503 Service Unavailable**：币安 API 未配置或不可用
- **500 Internal Server Error**：服务器内部错误
- **400 Bad Request**：请求参数错误

错误响应格式：
```json
{
  "detail": "错误描述信息"
}
}
```

## 日志记录

服务包含详细的日志记录功能，记录所有重要操作和错误信息，便于调试和监控。

## 开发和测试

### 测试网络

在开发和测试阶段，建议使用币安测试网络：

1. 在 `main.py` 中设置 `sandbox: True`
2. 使用测试网络的 API 密钥
3. 测试网络地址：https://testnet.binancefuture.com

### API 文档

启动服务后，可以访问自动生成的 API 文档：
- Swagger UI: http://localhost:80/docs
- ReDoc: http://localhost:80/redoc

## 许可证

本项目仅供学习和研究使用。使用本项目进行实际交易时，请自行承担风险。
