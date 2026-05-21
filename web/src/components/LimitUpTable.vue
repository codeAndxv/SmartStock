<script setup>
import { ref } from 'vue'

const data = ref(null)
const loading = ref(false)
const error = ref(null)
const sortKey = ref('predicted_change')
const sortAsc = ref(false)

const progress = ref({ current: 0, total: 0, code: '', name: '' })

function startScan() {
  loading.value = true
  error.value = null
  data.value = null
  progress.value = { current: 0, total: 0, code: '', name: '' }

  const evtSource = new EventSource('/api/limit-up/stream')

  evtSource.onmessage = (event) => {
    const msg = JSON.parse(event.data)

    if (msg.type === 'progress') {
      progress.value = {
        current: msg.current,
        total: msg.total,
        code: msg.code,
        name: msg.name,
      }
    } else if (msg.type === 'done') {
      data.value = msg
      loading.value = false
      evtSource.close()
    } else if (msg.type === 'error') {
      error.value = msg.message
      loading.value = false
      evtSource.close()
    }
  }

  evtSource.onerror = () => {
    error.value = '连接中断'
    loading.value = false
    evtSource.close()
  }
}

function sortBy(key) {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
  } else {
    sortKey.value = key
    sortAsc.value = false
  }
}

function sortedPredictions() {
  if (!data.value) return []
  const list = [...data.value.predictions]
  list.sort((a, b) => {
    const va = a[sortKey.value]
    const vb = b[sortKey.value]
    return sortAsc.value ? va - vb : vb - va
  })
  return list
}

function fmt(val, decimals = 2) {
  return Number(val).toFixed(decimals)
}

function changeClass(val) {
  if (val > 0) return 'positive'
  if (val < 0) return 'negative'
  return ''
}

function xueqiuUrl(code) {
  let prefix = 'SZ'
  if (code.startsWith('6') || code.startsWith('68')) prefix = 'SH'
  else if (code.startsWith('8')) prefix = 'BJ'
  return `https://xueqiu.com/S/${prefix}${code}`
}
</script>

<template>
  <div class="container">
    <h1>涨停分析</h1>
    <p class="desc">扫描今日涨停股票，分析所属行业和近期行情，预测明日涨跌幅。</p>

    <button class="scan-btn" :disabled="loading" @click="startScan">
      {{ loading ? '扫描中...' : '开始扫描' }}
    </button>

    <div v-if="loading" class="progress-area">
      <div class="progress-bar">
        <div
          class="progress-fill"
          :style="{ width: (progress.total ? (progress.current / progress.total * 100) : 0) + '%' }"
        ></div>
      </div>
      <div class="progress-text">
        正在分析 {{ progress.current }} / {{ progress.total }}：{{ progress.code }} {{ progress.name }}
      </div>
    </div>

    <div v-if="error" class="status error">Error: {{ error }}</div>

    <template v-if="data">
      <div class="meta">
        日期: {{ data.date }} | 涨停数量: {{ data.count }}
        <button class="refresh" @click="startScan" :disabled="loading">刷新</button>
      </div>

      <table>
        <thead>
          <tr>
            <th @click="sortBy('code')">代码</th>
            <th @click="sortBy('name')">名称</th>
            <th @click="sortBy('price')">最新价</th>
            <th @click="sortBy('today_change')">今日涨幅</th>
            <th @click="sortBy('predicted_change')">明日预测</th>
            <th @click="sortBy('industry')">所属行业</th>
            <th @click="sortBy('ytd_change')">年内涨幅</th>
            <th @click="sortBy('score')">评分</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in sortedPredictions()" :key="p.code">
            <td>{{ p.code }}</td>
            <td><a :href="xueqiuUrl(p.code)" target="_blank" class="stock-link">{{ p.name }}</a></td>
            <td class="num">{{ fmt(p.price) }}</td>
            <td class="num" :class="changeClass(p.today_change)">
              {{ fmt(p.today_change) }}%
            </td>
            <td class="num" :class="changeClass(p.predicted_change)">
              {{ fmt(p.predicted_change, 1) }}%
            </td>
            <td>{{ p.industry }}</td>
            <td class="num" :class="changeClass(p.ytd_change)">
              {{ fmt(p.ytd_change, 1) }}%
            </td>
            <td class="num" :class="changeClass(p.score)">
              {{ p.score > 0 ? '+' : '' }}{{ p.score }}
            </td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<style scoped>
.container {
  padding: 24px 32px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

h1 {
  font-size: 1.4rem;
  margin-bottom: 4px;
}

.desc {
  color: #888;
  font-size: 13px;
  margin-bottom: 16px;
}

.scan-btn {
  padding: 8px 24px;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.scan-btn:hover:not(:disabled) {
  background: #1557b0;
}

.scan-btn:disabled {
  background: #94c4f7;
  cursor: not-allowed;
}

.progress-area {
  margin-top: 16px;
  margin-bottom: 8px;
}

.progress-bar {
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #1a73e8;
  border-radius: 3px;
  transition: width 0.2s;
}

.progress-text {
  margin-top: 6px;
  font-size: 12px;
  color: #666;
}

.meta {
  margin: 16px 0 12px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.refresh {
  padding: 3px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
}

.refresh:hover:not(:disabled) {
  background: #f0f0f0;
}

.status {
  padding: 20px;
  text-align: center;
  color: #666;
}

.error {
  color: #d32f2f;
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
  border: 1px solid #ddd;
  border-radius: 6px;
  overflow: hidden;
}

th {
  text-align: left;
  padding: 7px 8px;
  border-bottom: 2px solid #ccc;
  border-left: 1px solid #e0e0e0;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  font-size: 12px;
  color: #555;
  background: #f5f5f5;
}

th:first-child {
  border-left: none;
}

th:hover {
  background: #eaeaea;
}

td {
  padding: 5px 8px;
  border-bottom: 1px solid #eee;
  border-left: 1px solid #eee;
}

td:first-child {
  border-left: none;
}

tbody tr:nth-child(even) {
  background: #eef1f5;
}

tbody tr:nth-child(odd) {
  background: #fff;
}

tbody tr:hover {
  background: #e8f0fe;
}

.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.positive {
  color: #d32f2f;
}

.negative {
  color: #2e7d32;
}

.stock-link {
  color: #1a73e8;
  text-decoration: none;
}

.stock-link:hover {
  text-decoration: underline;
}
</style>
