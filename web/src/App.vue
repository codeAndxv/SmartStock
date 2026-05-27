<script setup>
import { ref } from 'vue'
import LimitUpTable from './components/LimitUpTable.vue'
import StockLinks from './components/StockLinks.vue'
import PortfolioSim from './components/PortfolioSim.vue'

const activeFeature = ref(null)

const features = [
  { key: 'limit-up', label: '涨停分析' },
  { key: 'stock-links', label: '股票社区' },
  { key: 'portfolio', label: '组合模拟' },
]

function selectFeature(key) {
  activeFeature.value = key
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo">SmartStock</div>
      <nav>
        <ul>
          <li
            v-for="f in features"
            :key="f.key"
            :class="{ active: activeFeature === f.key }"
            @click="selectFeature(f.key)"
          >
            {{ f.label }}
          </li>
        </ul>
      </nav>
    </aside>
    <main class="content">
      <LimitUpTable v-if="activeFeature === 'limit-up'" />
      <StockLinks v-else-if="activeFeature === 'stock-links'" />
      <PortfolioSim v-else-if="activeFeature === 'portfolio'" />
      <div v-else class="placeholder">
        <p>请从左侧选择功能</p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 200px;
  background: #1a1a2e;
  color: #eee;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.logo {
  padding: 20px 16px;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid #2a2a4a;
  letter-spacing: 0.5px;
}

nav {
  flex: 1;
  padding: 8px 0;
}

ul {
  list-style: none;
}

li {
  padding: 10px 20px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.15s;
}

li:hover {
  background: #2a2a4a;
}

li.active {
  background: #16213e;
  border-left: 3px solid #4fc3f7;
  padding-left: 17px;
}

.content {
  flex: 1;
  overflow: auto;
  background: #f8f9fa;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  font-size: 16px;
}
</style>
