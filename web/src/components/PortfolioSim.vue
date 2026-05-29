<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { CandlestickChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([CandlestickChart, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

/* ---------- state ---------- */
const view = ref('list')
const portfolios = ref([])
const currentId = ref(null)
const summary = ref(null)
const trades = ref([])
const pnlHistory = ref([])
const loading = ref(false)
const error = ref(null)

/* create/edit modal */
const showModal = ref(false)
const modalMode = ref('create')
const formName = ref('')
const formCash = ref(100000)

/* trade modal */
const showTrade = ref(false)
const tradeCode = ref('')
const tradeName = ref('')
const tradeType = ref('buy')
const tradePrice = ref(0)
const tradeQty = ref(100)
const tradeLoading = ref(false)
const priceLoading = ref(false)

/* ---------- portfolio list ---------- */
async function loadPortfolios() {
  loading.value = true
  error.value = null
  try {
    const r = await fetch('/api/portfolios')
    portfolios.value = await r.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function openCreate() {
  modalMode.value = 'create'
  formName.value = ''
  formCash.value = 100000
  showModal.value = true
}

function openEdit(p) {
  modalMode.value = 'edit'
  formName.value = p.name
  formCash.value = p.initial_cash
  currentId.value = p.id
  showModal.value = true
}

async function submitModal() {
  if (!formName.value.trim()) return
  loading.value = true
  error.value = null
  try {
    if (modalMode.value === 'create') {
      await fetch('/api/portfolios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: formName.value.trim(), initial_cash: formCash.value }),
      })
    } else {
      await fetch(`/api/portfolios/${currentId.value}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: formName.value.trim() }),
      })
    }
    showModal.value = false
    await loadPortfolios()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function deletePortfolio(id) {
  if (!confirm('确定删除此组合？所有交易记录将一并删除。')) return
  loading.value = true
  error.value = null
  try {
    await fetch(`/api/portfolios/${id}`, { method: 'DELETE' })
    await loadPortfolios()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

/* ---------- portfolio detail ---------- */
async function openDetail(id) {
  currentId.value = id
  view.value = 'detail'
  await refreshSummary()
}

async function refreshSummary() {
  loading.value = true
  error.value = null
  try {
    const [sr, tr, phr] = await Promise.all([
      fetch(`/api/portfolios/${currentId.value}/summary`),
      fetch(`/api/portfolios/${currentId.value}/trades`),
      fetch(`/api/portfolios/${currentId.value}/pnl-history`),
    ])
    summary.value = await sr.json()
    trades.value = await tr.json()
    pnlHistory.value = await phr.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function backToList() {
  view.value = 'list'
  summary.value = null
  trades.value = []
  pnlHistory.value = []
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  loadPortfolios()
}

/* ---------- trade ---------- */
function openBuy() {
  tradeType.value = 'buy'
  tradeCode.value = ''
  tradeName.value = ''
  tradePrice.value = 0
  tradeQty.value = 100
  showTrade.value = true
}

function openSell(h) {
  tradeType.value = 'sell'
  tradeCode.value = h.stock_code
  tradeName.value = h.stock_name
  tradePrice.value = h.current_price
  tradeQty.value = h.quantity
  showTrade.value = true
}

async function fetchPrice() {
  const code = tradeCode.value.trim()
  if (!code || !/^(\d{6}|[A-Za-z]{2}\d{6})$/.test(code)) return
  priceLoading.value = true
  error.value = null
  try {
    const r = await fetch(`/api/stock-price?code=${code}`)
    if (!r.ok) {
      const b = await r.json().catch(() => ({}))
      throw new Error(b.detail || '获取价格失败')
    }
    const q = await r.json()
    tradePrice.value = q.price
    tradeName.value = q.name
  } catch (e) {
    error.value = e.message
  } finally {
    priceLoading.value = false
  }
}

async function submitTrade() {
  if (!tradeCode.value.trim() || tradeQty.value <= 0 || tradePrice.value <= 0) return
  tradeLoading.value = true
  error.value = null
  try {
    const r = await fetch(`/api/portfolios/${currentId.value}/trades`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stock_code: tradeCode.value.trim(),
        stock_name: tradeName.value || tradeCode.value.trim(),
        trade_type: tradeType.value,
        price: tradePrice.value,
        quantity: tradeQty.value,
      }),
    })
    if (!r.ok) {
      const b = await r.json().catch(() => ({}))
      throw new Error(b.detail || '交易失败')
    }
    showTrade.value = false
    await refreshSummary()
  } catch (e) {
    error.value = e.message
  } finally {
    tradeLoading.value = false
  }
}

/* ---------- helpers ---------- */
function fmt(v, d = 2) {
  return Number(v).toFixed(d)
}

/* auto-fetch price when valid code is entered (e.g. 000001 or SZ000725) */
let priceTimer = null
watch(tradeCode, (val) => {
  if (priceTimer) clearTimeout(priceTimer)
  const v = val.trim().toUpperCase()
  const isBare = /^\d{6}$/.test(v)
  const isPrefixed = /^(SH|SZ|BJ)\d{6}$/.test(v)
  if (isBare || isPrefixed) {
    priceTimer = setTimeout(() => fetchPrice(), 300)
  }
})

/* chart data */
const chartColors = ['#1a73e8', '#e8710a', '#0d904f', '#d32f2f', '#7b1fa2', '#00838f', '#c2185b', '#fbc02d']

const holdingBars = computed(() => {
  if (!summary.value || summary.value.holdings.length === 0) return []
  const total = summary.value.total_market_value + summary.value.cash_remaining
  if (total <= 0) return []
  return summary.value.holdings.map((h, i) => ({
    name: h.stock_name,
    code: h.stock_code,
    value: h.market_value,
    pct: (h.market_value / total) * 100,
    pnl: h.unrealized_pnl,
    pnlPct: h.unrealized_pnl_pct,
    color: chartColors[i % chartColors.length],
  }))
})

const cashBar = computed(() => {
  if (!summary.value) return null
  const total = summary.value.total_market_value + summary.value.cash_remaining
  if (total <= 0) return null
  return {
    pct: (summary.value.cash_remaining / total) * 100,
    value: summary.value.cash_remaining,
  }
})

const pnlBars = computed(() => {
  if (!summary.value || summary.value.holdings.length === 0) return []
  const maxAbs = Math.max(...summary.value.holdings.map(h => Math.abs(h.unrealized_pnl)), 1)
  return summary.value.holdings.map((h, i) => ({
    name: h.stock_name,
    pnl: h.unrealized_pnl,
    pct: (h.unrealized_pnl / maxAbs) * 50,
    color: h.unrealized_pnl >= 0 ? '#d32f2f' : '#2e7d32',
  }))
})

/* P&L history chart (ECharts) */
const chartRef = ref(null)
let chartInstance = null

function buildChartOption() {
  if (!pnlHistory.value || pnlHistory.value.length === 0) return null
  const data = pnlHistory.value

  const xData = data.map((d, i) => `${i + 1}`)
  const kData = [] // [open, close, low, high]
  const pnlPctData = []
  const tooltipData = []

  for (let i = 0; i < data.length; i++) {
    const prev = i > 0 ? data[i - 1].realized_pnl : 0
    const cur = data[i].realized_pnl
    const low = Math.min(prev, cur)
    const high = Math.max(prev, cur)
    kData.push([prev, cur, low, high])
    pnlPctData.push(data[i].pnl_pct)
    tooltipData.push(data[i])
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter(params) {
        const idx = params[0].dataIndex
        const d = tooltipData[idx]
        const type = d.trade_type === 'buy' ? '买入' : '卖出'
        const lines = [
          `<b>${type} ${d.stock_name}</b> @ ${d.price}`,
          `盈亏: ${d.realized_pnl >= 0 ? '+' : ''}${d.realized_pnl.toFixed(2)}`,
          `盈亏率: ${d.pnl_pct >= 0 ? '+' : ''}${d.pnl_pct.toFixed(2)}%`,
        ]
        return lines.join('<br/>')
      },
    },
    legend: {
      data: ['累计盈亏', '盈亏率'],
      bottom: 0,
      textStyle: { fontSize: 11 },
    },
    grid: { left: 55, right: 55, top: 10, bottom: 40 },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: {
        formatter(val) {
          const idx = parseInt(val) - 1
          const d = tooltipData[idx]
          return d ? d.time.replace('T', '\n').slice(5, 16) : val
        },
        fontSize: 10,
      },
    },
    yAxis: [
      {
        type: 'value',
        name: '盈亏额',
        position: 'left',
        axisLabel: { fontSize: 10, formatter: v => v >= 0 ? `+${v}` : v },
        splitLine: { lineStyle: { type: 'dashed', color: '#eee' } },
      },
      {
        type: 'value',
        name: '盈亏率%',
        position: 'right',
        axisLabel: { fontSize: 10, formatter: v => `${v}%` },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '累计盈亏',
        type: 'candlestick',
        data: kData,
        itemStyle: {
          color: '#d32f2f',       // up (positive) fill
          color0: '#2e7d32',      // down (negative) fill
          borderColor: '#d32f2f', // up border
          borderColor0: '#2e7d32',// down border
        },
      },
      {
        name: '盈亏率',
        type: 'line',
        yAxisIndex: 1,
        data: pnlPctData,
        smooth: true,
        lineStyle: { width: 2, color: '#1a73e8' },
        itemStyle: { color: '#1a73e8' },
        symbol: 'circle',
        symbolSize: 5,
      },
    ],
  }
}

function renderChart() {
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  const opt = buildChartOption()
  if (opt) {
    chartInstance.setOption(opt, true)
  } else {
    chartInstance.clear()
  }
}

function handleResize() {
  chartInstance?.resize()
}

watch(pnlHistory, () => {
  nextTick(() => {
    if (chartRef.value) {
      renderChart()
    } else {
      // DOM not ready yet (v-if still false), retry after a frame
      requestAnimationFrame(() => nextTick(renderChart))
    }
  })
})
onMounted(() => { window.addEventListener('resize', handleResize) })
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
  chartInstance = null
})

function pnlClass(v) {
  if (v > 0) return 'positive'
  if (v < 0) return 'negative'
  return ''
}

function tradeTime(t) {
  return t.replace('T', ' ')
}

/* init */
loadPortfolios()
</script>

<template>
  <div class="container">
    <!-- ========== LIST VIEW ========== -->
    <template v-if="view === 'list'">
      <div class="header-row">
        <div>
          <h1>组合模拟</h1>
          <p class="desc">创建股票组合，模拟买入卖出，跟踪收益表现。</p>
        </div>
        <button class="btn primary" @click="openCreate">+ 新建组合</button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <div v-if="portfolios.length === 0 && !loading" class="empty">
        暂无组合，点击右上角"新建组合"开始。
      </div>

      <div class="portfolio-grid">
        <div v-for="p in portfolios" :key="p.id" class="portfolio-card" @click="openDetail(p.id)">
          <div class="card-header">
            <span class="card-name">{{ p.name }}</span>
            <div class="card-actions" @click.stop>
              <button class="icon-btn" title="编辑" @click="openEdit(p)">&#9998;</button>
              <button class="icon-btn danger" title="删除" @click="deletePortfolio(p.id)">&#10005;</button>
            </div>
          </div>
          <div class="card-body">
            <div class="card-stat">
              <span class="label">初始资金</span>
              <span class="value">&yen;{{ fmt(p.initial_cash, 0) }}</span>
            </div>
            <div class="card-stat">
              <span class="label">创建时间</span>
              <span class="value small">{{ p.created_at }}</span>
            </div>
          </div>
          <div class="card-footer">点击查看持仓 &rarr;</div>
        </div>
      </div>
    </template>

    <!-- ========== DETAIL VIEW ========== -->
    <template v-if="view === 'detail' && summary">
      <div class="header-row">
        <div class="detail-title">
          <button class="btn back" @click="backToList">&larr; 返回</button>
          <h1>{{ summary.name }}</h1>
        </div>
        <button class="btn primary" @click="openBuy">+ 买入股票</button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <!-- summary cards -->
      <div class="summary-row">
        <div class="summary-card">
          <span class="label">初始资金</span>
          <span class="value">&yen;{{ fmt(summary.initial_cash, 0) }}</span>
        </div>
        <div class="summary-card">
          <span class="label">持仓市值</span>
          <span class="value">&yen;{{ fmt(summary.total_market_value) }}</span>
        </div>
        <div class="summary-card">
          <span class="label">可用现金</span>
          <span class="value">&yen;{{ fmt(summary.cash_remaining) }}</span>
        </div>
        <div class="summary-card">
          <span class="label">总盈亏</span>
          <span class="value" :class="pnlClass(summary.total_unrealized_pnl)">
            {{ summary.total_unrealized_pnl > 0 ? '+' : '' }}&yen;{{ fmt(summary.total_unrealized_pnl) }}
            ({{ summary.total_pnl_pct > 0 ? '+' : '' }}{{ fmt(summary.total_pnl_pct) }}%)
          </span>
        </div>
      </div>

      <!-- charts -->
      <div v-if="summary.holdings.length > 0" class="charts-row">
        <!-- allocation chart -->
        <div class="chart-card">
          <h3 class="chart-title">持仓占比</h3>
          <div class="alloc-chart">
            <div class="alloc-bar-track">
              <div
                v-for="(b, i) in holdingBars"
                :key="b.code"
                class="alloc-bar-seg"
                :style="{ width: b.pct + '%', background: b.color }"
                :title="b.name + ' ' + fmt(b.pct, 1) + '%'"
              ></div>
              <div
                v-if="cashBar"
                class="alloc-bar-seg cash"
                :style="{ width: cashBar.pct + '%' }"
                :title="'现金 ' + fmt(cashBar.pct, 1) + '%'"
              ></div>
            </div>
            <div class="alloc-legend">
              <div v-for="b in holdingBars" :key="b.code" class="legend-item">
                <span class="legend-dot" :style="{ background: b.color }"></span>
                <span class="legend-name">{{ b.name }}</span>
                <span class="legend-pct">{{ fmt(b.pct, 1) }}%</span>
              </div>
              <div v-if="cashBar" class="legend-item">
                <span class="legend-dot cash"></span>
                <span class="legend-name">现金</span>
                <span class="legend-pct">{{ fmt(cashBar.pct, 1) }}%</span>
              </div>
            </div>
          </div>
        </div>

        <!-- P&L chart -->
        <div class="chart-card">
          <h3 class="chart-title">个股盈亏</h3>
          <div class="pnl-chart">
            <div v-for="b in pnlBars" :key="b.name" class="pnl-row">
              <span class="pnl-label">{{ b.name }}</span>
              <div class="pnl-bar-track">
                <div
                  class="pnl-bar"
                  :class="b.pnl >= 0 ? 'pos' : 'neg'"
                  :style="b.pnl >= 0
                    ? { width: Math.abs(b.pct) + '%' }
                    : { width: Math.abs(b.pct) + '%', marginLeft: (50 - Math.abs(b.pct)) + '%' }"
                ></div>
              </div>
              <span class="pnl-val" :class="b.pnl >= 0 ? 'positive' : 'negative'">
                {{ b.pnl > 0 ? '+' : '' }}{{ fmt(b.pnl) }}
              </span>
            </div>
            <div v-if="pnlBars.length === 0" class="empty-sm">暂无数据</div>
          </div>
        </div>
      </div>

      <!-- P&L history chart (ECharts candlestick) -->
      <div v-if="pnlHistory.length > 0" class="chart-card full-width">
        <div class="chart-header">
          <h3 class="chart-title">累计盈亏走势</h3>
        </div>
        <div ref="chartRef" class="echart-container"></div>
      </div>

      <!-- holdings table -->
      <h2 class="section-title">持仓明细</h2>
      <div v-if="summary.holdings.length === 0" class="empty">暂无持仓，点击"买入股票"开始交易。</div>
      <table v-else>
        <colgroup>
          <col style="width:70px" /><col style="width:70px" /><col style="width:60px" />
          <col style="width:70px" /><col style="width:65px" /><col style="width:85px" />
          <col style="width:80px" /><col style="width:65px" /><col style="width:50px" />
        </colgroup>
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>数量</th>
            <th>成本价</th>
            <th>现价</th>
            <th>市值</th>
            <th>盈亏</th>
            <th>盈亏%</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="h in summary.holdings" :key="h.stock_code">
            <td>{{ h.stock_code }}</td>
            <td>{{ h.stock_name }}</td>
            <td class="num">{{ h.quantity }}</td>
            <td class="num">{{ fmt(h.avg_cost, 3) }}</td>
            <td class="num">{{ fmt(h.current_price) }}</td>
            <td class="num">&yen;{{ fmt(h.market_value) }}</td>
            <td class="num" :class="pnlClass(h.unrealized_pnl)">
              {{ h.unrealized_pnl > 0 ? '+' : '' }}&yen;{{ fmt(h.unrealized_pnl) }}
            </td>
            <td class="num" :class="pnlClass(h.unrealized_pnl_pct)">
              {{ h.unrealized_pnl_pct > 0 ? '+' : '' }}{{ fmt(h.unrealized_pnl_pct) }}%
            </td>
            <td>
              <button class="btn small sell" @click="openSell(h)">卖出</button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- trade history -->
      <h2 class="section-title">交易记录</h2>
      <div v-if="trades.length === 0" class="empty">暂无交易记录。</div>
      <table v-else>
        <colgroup>
          <col style="width:120px" /><col style="width:50px" /><col style="width:70px" />
          <col style="width:70px" /><col style="width:75px" /><col style="width:65px" />
          <col style="width:90px" />
        </colgroup>
        <thead>
          <tr>
            <th>时间</th>
            <th>类型</th>
            <th>代码</th>
            <th>名称</th>
            <th>价格</th>
            <th>数量</th>
            <th>金额</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in trades" :key="t.id">
            <td>{{ tradeTime(t.created_at) }}</td>
            <td>
              <span :class="t.trade_type === 'buy' ? 'tag-buy' : 'tag-sell'">
                {{ t.trade_type === 'buy' ? '买入' : '卖出' }}
              </span>
            </td>
            <td>{{ t.stock_code }}</td>
            <td>{{ t.stock_name }}</td>
            <td class="num">{{ fmt(t.price, 3) }}</td>
            <td class="num">{{ t.quantity }}</td>
            <td class="num">&yen;{{ fmt(t.amount) }}</td>
          </tr>
        </tbody>
      </table>
    </template>

    <!-- ========== CREATE/EDIT MODAL ========== -->
    <div v-if="showModal" class="modal-mask" @click.self="showModal = false">
      <div class="modal">
        <h3>{{ modalMode === 'create' ? '新建组合' : '编辑组合' }}</h3>
        <div class="form-group">
          <label>组合名称</label>
          <input v-model="formName" type="text" placeholder="如：科技股组合" @keydown.enter="submitModal" />
        </div>
        <div v-if="modalMode === 'create'" class="form-group">
          <label>初始资金 (元)</label>
          <input v-model.number="formCash" type="number" min="1000" step="10000" />
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showModal = false">取消</button>
          <button class="btn primary" :disabled="!formName.trim()" @click="submitModal">
            {{ modalMode === 'create' ? '创建' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ========== TRADE MODAL ========== -->
    <div v-if="showTrade" class="modal-mask" @click.self="showTrade = false">
      <div class="modal">
        <h3>{{ tradeType === 'buy' ? '买入' : '卖出' }}股票</h3>
        <div class="form-group">
          <label>股票代码</label>
          <input
            v-model="tradeCode"
            type="text"
            placeholder="输入代码如 000001 或 SZ000725"
            maxlength="8"
            :disabled="tradeType === 'sell'"
          />
          <div v-if="priceLoading" class="stock-hint">获取价格中...</div>
          <div v-else-if="tradeName" class="stock-hint">{{ tradeName }} - &yen;{{ fmt(tradePrice) }}</div>
        </div>
        <div class="form-group">
          <label>价格 (元)</label>
          <input v-model.number="tradePrice" type="number" step="0.01" min="0.01" />
        </div>
        <div class="form-group">
          <label>数量 (股)</label>
          <input v-model.number="tradeQty" type="number" step="100" min="1" />
        </div>
        <div class="trade-preview">
          交易金额: &yen;{{ fmt(tradePrice * tradeQty) }}
        </div>
        <div v-if="error" class="error">{{ error }}</div>
        <div class="modal-actions">
          <button class="btn" @click="showTrade = false">取消</button>
          <button
            class="btn"
            :class="tradeType === 'buy' ? 'primary' : 'sell'"
            :disabled="tradeLoading || !tradeCode.trim() || tradePrice <= 0 || tradeQty <= 0"
            @click="submitTrade"
          >
            {{ tradeLoading ? '提交中...' : (tradeType === 'buy' ? '确认买入' : '确认卖出') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container { padding: 24px 32px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
h1 { font-size: 1.4rem; margin-bottom: 4px; }
.desc { color: #888; font-size: 13px; margin-bottom: 16px; }

.header-row { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; gap: 16px; flex-wrap: wrap; }
.detail-title { display: flex; align-items: center; gap: 12px; }
.detail-title h1 { margin: 0; }

/* buttons */
.btn { padding: 7px 18px; border: 1px solid #ddd; border-radius: 6px; background: #fff; font-size: 13px; cursor: pointer; transition: all 0.15s; }
.btn:hover:not(:disabled) { background: #f5f5f5; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn.primary { background: #1a73e8; color: #fff; border-color: #1a73e8; }
.btn.primary:hover:not(:disabled) { background: #1557b0; }
.btn.sell { background: #2e7d32; color: #fff; border-color: #2e7d32; }
.btn.sell:hover:not(:disabled) { background: #1b5e20; }
.btn.small { padding: 4px 12px; font-size: 12px; }
.btn.back { padding: 5px 14px; font-size: 13px; }
.icon-btn { background: none; border: none; cursor: pointer; font-size: 16px; padding: 4px 8px; border-radius: 4px; color: #666; }
.icon-btn:hover { background: #eee; }
.icon-btn.danger:hover { background: #fce4ec; color: #c62828; }

.error { color: #d32f2f; font-size: 13px; margin-bottom: 12px; }
.empty { color: #999; text-align: center; padding: 40px 0; font-size: 14px; }

/* portfolio grid */
.portfolio-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.portfolio-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px 20px; cursor: pointer; transition: border-color 0.15s, box-shadow 0.15s; }
.portfolio-card:hover { border-color: #1a73e8; box-shadow: 0 2px 12px rgba(26, 115, 232, 0.1); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.card-name { font-size: 16px; font-weight: 600; }
.card-actions { display: flex; gap: 2px; }
.card-body { display: flex; gap: 24px; margin-bottom: 12px; }
.card-stat { display: flex; flex-direction: column; gap: 2px; }
.card-stat .label { font-size: 11px; color: #999; }
.card-stat .value { font-size: 15px; font-weight: 500; }
.card-stat .value.small { font-size: 12px; font-weight: 400; color: #666; }
.card-footer { font-size: 12px; color: #1a73e8; border-top: 1px solid #f0f0f0; padding-top: 10px; }

/* summary */
.summary-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }
.summary-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.summary-card .label { font-size: 12px; color: #999; }
.summary-card .value { font-size: 18px; font-weight: 600; }

.section-title { font-size: 15px; font-weight: 600; margin: 20px 0 10px; color: #333; }

/* tables */
table { width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 13px; border: 1px solid #ddd; margin-bottom: 16px; }
th, td { padding: 7px 8px; border-bottom: 1px solid #eee; border-left: 1px solid #eee; text-align: left; box-sizing: border-box; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
th:first-child, td:first-child { border-left: none; }
th { border-bottom: 2px solid #ccc; background: #f5f5f5; font-size: 12px; color: #555; }
tbody tr:nth-child(even) { background: #f8f9fb; }
tbody tr:hover { background: #e8f0fe; }
.num { text-align: right; font-variant-numeric: tabular-nums; }

.positive { color: #d32f2f; }
.negative { color: #2e7d32; }
.tag-buy { color: #d32f2f; font-weight: 500; }
.tag-sell { color: #2e7d32; font-weight: 500; }

/* modals */
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #fff; border-radius: 12px; padding: 24px 28px; width: 400px; max-width: 90vw; box-shadow: 0 8px 32px rgba(0,0,0,0.15); }
.modal h3 { margin: 0 0 16px; font-size: 16px; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; color: #666; margin-bottom: 4px; }
.form-group input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; outline: none; box-sizing: border-box; }
.form-group input:focus { border-color: #1a73e8; }
.form-group input:disabled { background: #f5f5f5; }
.input-row { display: flex; gap: 8px; }
.input-row input { flex: 1; }
.stock-hint { font-size: 12px; color: #1a73e8; margin-top: 4px; }
.trade-preview { background: #f5f7fa; padding: 10px 14px; border-radius: 6px; font-size: 14px; font-weight: 500; margin-bottom: 12px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }

/* charts */
.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
@media (max-width: 800px) { .charts-row { grid-template-columns: 1fr; } }
.chart-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; }
.chart-title { font-size: 13px; font-weight: 600; color: #555; margin: 0 0 12px; }

.alloc-bar-track { display: flex; height: 24px; border-radius: 4px; overflow: hidden; background: #eee; margin-bottom: 12px; }
.alloc-bar-seg { min-width: 2px; transition: width 0.3s; }
.alloc-bar-seg.cash { background: #e0e0e0; }
.alloc-legend { display: flex; flex-wrap: wrap; gap: 6px 16px; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 12px; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.legend-dot.cash { background: #e0e0e0; }
.legend-name { color: #555; }
.legend-pct { color: #999; font-variant-numeric: tabular-nums; }

.pnl-chart { display: flex; flex-direction: column; gap: 8px; }
.pnl-row { display: flex; align-items: center; gap: 8px; }
.pnl-label { width: 60px; font-size: 12px; color: #555; text-align: right; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pnl-bar-track { flex: 1; height: 16px; background: #f0f0f0; border-radius: 3px; position: relative; display: flex; align-items: center; }
.pnl-bar { height: 100%; border-radius: 3px; transition: width 0.3s; min-width: 2px; }
.pnl-bar.pos { background: rgba(211, 47, 47, 0.7); margin-left: 50%; }
.pnl-bar.neg { background: rgba(46, 125, 50, 0.7); }
.pnl-bar-track::after { content: ''; position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: #ccc; }
.pnl-val { width: 70px; font-size: 12px; text-align: right; font-variant-numeric: tabular-nums; flex-shrink: 0; }
.empty-sm { color: #bbb; font-size: 12px; text-align: center; padding: 16px 0; }

/* P&L history chart (ECharts) */
.full-width { margin-bottom: 24px; }
.chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.chart-header .chart-title { margin: 0; }
.echart-container { width: 100%; height: 300px; }
</style>
