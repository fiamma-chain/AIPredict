# Web 界面

这是 AI Trading Arena 的 Web 前端界面。

## 功能特性

- 📊 实时排行榜展示
- 📈 策略性能可视化
- 🎯 多维度指标对比
- 🔄 自动数据刷新
- 📱 响应式设计

## 使用方法

### 1. 启动后端服务

```bash
cd ..
python main.py
```

### 2. 访问 Web 界面

在浏览器中打开：`web/index.html`

或者使用简单的 HTTP 服务器：

```bash
cd web
python -m http.server 8080
```

然后访问：`http://localhost:8080`

## API 端点

Web 界面会连接到以下 API 端点：

- `GET /leaderboard` - 获取排行榜
- `GET /leaderboard/summary` - 获取统计摘要
- `GET /strategies` - 获取所有策略
- `GET /strategies/{id}` - 获取策略详情
- `WS /ws` - WebSocket 实时数据推送

## 自定义

你可以通过修改 `index.html` 中的 `API_URL` 变量来更改 API 服务器地址：

```javascript
const API_URL = 'http://localhost:8000';
```

## 排行榜指标

- **总盈亏** - 累计盈亏金额
- **ROI%** - 投资回报率
- **胜率** - 盈利交易占比
- **夏普比率** - 风险调整后收益

