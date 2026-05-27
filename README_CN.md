# SmartStock

A股涨停板扫描器，附带次日走势预测。

## 产品目标

- 扫描指定交易日所有涨停股票
- 分析每只股票的近期交易模式、所属行业和基本面
- 使用多因子评分模型预测次日走势
- 在可排序的网页表格中展示结果，支持实时进度显示

## 工作原理

1. 从 AKShare（东方财富数据源）获取每日涨停股票池
2. 对每只股票，拉取30日K线数据（新浪）和公司资料（雪球）
3. 基于6个因子对股票评分：连板数、炸板次数、封板时间、换手率、成交量趋势、价格趋势
4. 将总分映射为预测的次日涨跌幅百分比
5. 通过 SSE（Server-Sent Events）向前端推送实时进度

## 项目结构

```
SmartStock/
├── backend/                # FastAPI 服务 + Python 环境
│   ├── .venv/              # 虚拟环境
│   ├── pyproject.toml      # Python 依赖
│   ├── app.py              # API 接口
│   ├── core/               # 业务逻辑
│   │   ├── scan_limit_up.py # 扫描与预测
│   │   └── stock_info.py   # AKShare 数据辅助
│   └── cli/                # 命令行工具
│       └── main.py         # CLI 示例
├── web/                    # Vue 3 + Vite 前端
│   └── src/
│       ├── App.vue
│       └── components/
│           └── LimitUpTable.vue
└── API_NOTES.md            # AKShare API 连接说明
```

## 环境配置

### 前置要求

- Python 3.11+
- Node.js 18+

### 后端

```bash
cd backend

# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e ".[dev]"
cd ..
```

### 前端

```bash
cd web
npm install
```

## 启动应用

打开两个终端：

```bash
# 终端 1 — 后端 (端口 8000)
source backend/.venv/bin/activate
uvicorn backend.app:app --host 0.0.0.0 --port 8000

# 终端 2 — 前端 (端口 5173)
cd web
npm run dev
```

然后打开 http://localhost:5173，点击侧边栏的"涨停分析"，再点击"开始扫描"。

## 命令行使用

```bash
source backend/.venv/bin/activate
python -m backend.cli.main [股票代码] [天数]
```
