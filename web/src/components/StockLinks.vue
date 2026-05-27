<script setup>
import { ref } from 'vue'

const query = ref('')
const loading = ref(false)
const error = ref(null)
const result = ref(null)

async function search() {
  const q = query.value.trim()
  if (!q) return

  loading.value = true
  error.value = null
  result.value = null

  try {
    const resp = await fetch(`/api/stock-links?code=${encodeURIComponent(q)}`)
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `请求失败 (${resp.status})`)
    }
    result.value = await resp.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function onKeydown(e) {
  if (e.key === 'Enter') search()
}

const iconMap = {
  snowflake: 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/2744.svg',
  chat: 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f4ac.svg',
  chart: 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f4c8.svg',
  news: 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f4f0.svg',
  building: 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f3e2.svg',
  search: 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f50d.svg',
  document: 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f4c4.svg',
}
</script>

<template>
  <div class="container">
    <h1>股票社区</h1>
    <p class="desc">输入股票代码或名称，快速跳转各大股票社区与信息平台。</p>

    <div class="search-bar">
      <input
        v-model="query"
        type="text"
        placeholder="输入股票代码（如 000001）或名称（如 平安银行）"
        @keydown="onKeydown"
      />
      <button class="search-btn" :disabled="loading || !query.trim()" @click="search">
        {{ loading ? '查询中...' : '查询' }}
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="result" class="result-area">
      <div class="stock-header">
        <span class="stock-name">{{ result.name }}</span>
        <span class="stock-code">{{ result.code }}</span>
        <span v-if="result.full_name !== result.name" class="stock-full">{{ result.full_name }}</span>
      </div>

      <div class="links-grid">
        <a
          v-for="link in result.links"
          :key="link.name"
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
          class="link-card"
        >
          <div class="link-icon">
            <img :src="iconMap[link.icon] || iconMap.document" :alt="link.name" />
          </div>
          <div class="link-info">
            <div class="link-name">{{ link.name }}</div>
            <div class="link-desc">{{ link.description }}</div>
          </div>
          <div class="link-arrow">&rsaquo;</div>
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container { padding: 24px 32px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
h1 { font-size: 1.4rem; margin-bottom: 4px; }
.desc { color: #888; font-size: 13px; margin-bottom: 16px; }

.search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.search-bar input {
  flex: 1;
  max-width: 400px;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}

.search-bar input:focus {
  border-color: #1a73e8;
}

.search-btn {
  padding: 8px 24px;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.search-btn:hover:not(:disabled) { background: #1557b0; }
.search-btn:disabled { background: #94c4f7; cursor: not-allowed; }

.error { color: #d32f2f; margin-bottom: 16px; font-size: 13px; }

.stock-header {
  margin-bottom: 16px;
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.stock-name { font-size: 20px; font-weight: 600; }
.stock-code { font-size: 14px; color: #666; font-variant-numeric: tabular-nums; }
.stock-full { font-size: 13px; color: #999; }

.links-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}

.link-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.link-card:hover {
  border-color: #1a73e8;
  box-shadow: 0 2px 8px rgba(26, 115, 232, 0.1);
}

.link-icon {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 8px;
}

.link-icon img {
  width: 22px;
  height: 22px;
}

.link-info { flex: 1; min-width: 0; }
.link-name { font-size: 14px; font-weight: 500; margin-bottom: 2px; }
.link-desc { font-size: 12px; color: #888; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.link-arrow { font-size: 20px; color: #ccc; flex-shrink: 0; }
.link-card:hover .link-arrow { color: #1a73e8; }
</style>
