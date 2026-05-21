# AKShare API Notes

## Key Takeaway

**东方财富(EM)的API在当前环境连不通，新浪和雪球接口可以正常使用。** 但EM的涨停池接口（`stock_zt_pool_em`）是例外，可以正常访问。

## Connectivity Status (as of 2026-05-21)

| Data Source | Status | Example Functions |
|---|---|---|
| 东方财富 (EM) | Unreachable — connection reset | `stock_zh_a_spot_em`, `stock_individual_info_em` |
| 新浪 (Sina) | Working | `stock_zh_a_daily`, `stock_info_a_code_name` |
| 雪球 (Xueqiu) | Working | `stock_individual_basic_info_xq` |
| 东方财富涨停池 (EM ZT Pool) | Working | `stock_zt_pool_em` |

## Working API Reference

### 涨停板数据 (EM)
- `ak.stock_zt_pool_em(date='YYYYMMDD')` — 当日涨停股列表，含行业、连板数、封板时间等

### 历史日线 (Sina)
- `ak.stock_zh_a_daily(symbol='sz000001', start_date, end_date, adjust='qfq')` — 前复权日K
- symbol 格式: `sh600519` / `sz000001` / `bj830001`

### 股票基本信息 (Xueqiu)
- `ak.stock_individual_basic_info_xq(symbol='SZ000001')` — 公司简介、行业、地区、董事长等
- symbol 格式: `SH600519` / `SZ000001` / `BJ830001`

### 股票代码名称 (Sina)
- `ak.stock_info_a_code_name()` — 全量A股代码与名称映射

## Code Prefix Rules

| Code Prefix | Market | Sina Symbol | Xueqiu Symbol |
|---|---|---|---|
| 60xxxx, 68xxxx | 上海 (SH) | `sh{code}` | `SH{code}` |
| 00xxxx, 30xxxx | 深圳 (SZ) | `sz{code}` | `SZ{code}` |
| 8xxxxx | 北交所 (BJ) | `bj{code}` | `BJ{code}` |
