<template>
  <div class="maoyan-heat-list">
    <!-- 标题栏：标题 + TOP30 + 缓存标签 + 更新时间 + 刷新按钮 -->
    <VRow>
      <VCol cols="12">
        <div class="d-flex align-center mb-4 flex-wrap gap-2">
          <VIcon size="x-small" start>mdi-fire</VIcon>
          <span class="text-h6 font-weight-bold">猫眼网播热度榜</span>
          <VChip size="small" color="error" class="ml-1">TOP30</VChip>
          <VChip v-if="fromCache" size="small" color="success" variant="tonal">缓存</VChip>
          <span v-if="updateTime" class="text-caption text-grey ml-1">{{ updateTime }}</span>
          <VSpacer />
          <VBtn size="small" color="primary" :loading="loading" @click="refreshData">
            <VIcon start>mdi-refresh</VIcon>
            刷新
          </VBtn>
          <VBtn size="small" variant="text" icon="mdi-close" @click="closePage" />
        </div>
      </VCol>
    </VRow>

    <!-- 加载中状态 -->
    <VRow v-if="loading && items.length === 0">
      <VCol cols="12" class="text-center py-8">
        <VProgressCircular indeterminate color="primary" />
        <div class="text-caption text-grey mt-2">正在抓取猫眼热度数据...</div>
      </VCol>
    </VRow>

    <!-- 空数据状态 -->
    <VRow v-else-if="items.length === 0">
      <VCol cols="12" class="text-center py-8">
        <VAlert type="info" variant="tonal">暂无数据，请点击"刷新"按钮获取</VAlert>
      </VCol>
    </VRow>

    <!-- 热度列表 -->
    <div v-else class="maoyan-cards-grid">
      <div v-for="item in items" :key="item.rank" class="maoyan-card-wrapper">
        <VCard variant="outlined" rounded="lg" class="h-100">
          <VRow no-gutters align="center">
            <!-- 海报区域 -->
            <VCol cols="auto" class="pa-2">
              <div style="position: relative">
                <VImg
                  :src="resolvePoster(item.poster, 'card-' + item.rank)"
                  width="133"
                  height="200"
                  cover
                  rounded="sm"
                  class="bg-grey-lighten-3"
                  :class="{ 'cursor-pointer': item.tmdbid }"
                  @error="handlePosterError('card-' + item.rank)"
                  @click="openMediaDetail(item)"
                />
                <!-- 状态标签（海报底部） -->
                <div
                  :style="`position: absolute; bottom: 0; left: 0; right: 0; background: ${getStatusColor(item)}; color: white; font-size: 12px; text-align: center; padding: 3px 0; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px;`"
                >
                  {{ item.status || '未添加订阅' }}
                </div>
              </div>
            </VCol>

            <!-- 信息区域 -->
            <VCol class="pa-2 d-flex flex-column justify-space-between" style="min-height: 200px;">
              <div>
                <div class="d-flex align-center mb-1">
                  <VChip size="x-small" color="primary" class="mr-1">{{ item.rank }}</VChip>
                  <span style="font-size: 14px; font-weight: bold; line-height: 1.3;">{{ item.name }}</span>
                </div>
                <div class="text-grey mb-1" style="font-size: 12px;">
                  <VIcon size="small" class="mr-1">mdi-television-classic</VIcon>
                  {{ item.platform || '未知平台' }}
                </div>
                <div class="text-grey mb-1" style="font-size: 12px;">
                  <VIcon size="small" class="mr-1">mdi-clock-outline</VIcon>
                  {{ item.days || '未知' }}
                </div>
                <div class="text-grey mb-1" style="font-size: 12px;">
                  <VIcon size="small" color="error" class="mr-1">mdi-fire</VIcon>
                  热度: {{ item.heat || 0 }}
                </div>
                <div class="text-grey mb-1" style="font-size: 12px;">
                  <VIcon size="small" class="mr-1">mdi-play-circle-outline</VIcon>
                  {{ item.plays || '未知' }}
                </div>
                <div class="text-grey mb-1" style="font-size: 12px;" v-if="item.actors">
                  <VIcon size="small" class="mr-1">mdi-account-group</VIcon>
                  {{ Array.isArray(item.actors) ? item.actors.join(' / ') : item.actors }}
                </div>
              </div>
              <!-- 卡片订阅按钮 -->
              <div>
                <VBtn
                  size="small"
                  class="mt-1"
                  :color="(item.status || '未添加订阅') === '未添加订阅' ? 'primary' : 'grey'"
                  :variant="(item.status || '未添加订阅') === '未添加订阅' ? 'elevated' : 'tonal'"
                  :loading="isSubscribing(item.tmdbid)"
                  :disabled="(item.status || '未添加订阅') !== '未添加订阅'"
                  @click="subscribe(item)"
                >
                  {{ (item.status || '未添加订阅') === '未添加订阅' ? '订阅' : item.status }}
                </VBtn>
              </div>
            </VCol>
          </VRow>
        </VCard>
      </div>
    </div>

    <!-- 媒体详情弹窗 -->
    <VDialog v-model="detailOpen" max-width="1000" scrollable persistent>
      <VCard class="media-detail-card">
        <VCardTitle class="d-flex align-center px-4 pt-4 pb-0">
          <span class="text-h6">{{ (detail || selectedItem)?.title || selectedItem?.name || '媒体详情' }}</span>
          <VSpacer />
          <VBtn icon="mdi-close" variant="text" @click="closeMediaDetail" />
        </VCardTitle>
        <VCardText class="px-4 pb-4">
          <!-- 详情加载中 -->
          <div v-if="detailLoading" class="text-center py-12">
            <VProgressCircular indeterminate color="primary" />
            <div class="text-caption text-grey mt-3">正在加载媒体详情...</div>
          </div>
          <!-- 详情错误 -->
          <VAlert v-else-if="detailError" type="error" variant="tonal" class="my-4">
            {{ detailError }}
            <template #append>
              <VBtn size="small" variant="tonal" @click="retryMediaDetail">重试</VBtn>
            </template>
          </VAlert>
          <!-- 详情内容 -->
          <div v-else-if="detail" class="media-page">
            <!-- 头部：海报 + 标题 + 操作按钮 -->
            <div class="media-header">
              <div class="media-poster">
                <VImg
                  :src="resolvePoster(getW500Image(detail.poster_path) || selectedItem?.poster, 'detail-' + detail.tmdb_id)"
                  cover
                  class="object-cover ring-1 ring-gray-500"
                  style="aspect-ratio: 2 / 3"
                  @error="handlePosterError('detail-' + detail.tmdb_id)"
                >
                  <template #placeholder>
                    <div class="w-full h-full">
                      <VSkeletonLoader class="object-cover" style="aspect-ratio: 2 / 3" />
                    </div>
                  </template>
                </VImg>
              </div>
              <div class="media-title">
                <h1 class="d-flex flex-column flex-lg-row align-items-center align-items-lg-baseline">
                  <span>{{ detail.title || selectedItem?.name || '未知名称' }}</span>
                  <span v-if="detail.year" class="text-lg ms-1">（{{ detail.year }}）</span>
                  <VChip
                    v-if="detail.season_number"
                    size="small"
                    color="primary"
                    variant="tonal"
                    class="ms-2"
                  >第 {{ detail.season_number }} 季</VChip>
                </h1>
                <span class="media-attributes">
                  <span v-if="detail.runtime || detail.episode_run_time?.[0]">
                    {{ detail.runtime || detail.episode_run_time?.[0] }}分钟
                  </span>
                  <span v-if="(detail.runtime || detail.episode_run_time?.[0]) && detail.genres?.length" class="mx-1">|</span>
                  <span v-if="detail.genres?.length">{{ getGenresName(detail.genres) }}</span>
                </span>
                <div class="mt-2">
                  <VChip v-if="detail.vote_average" size="small" color="amber" variant="tonal" class="me-2 mb-1">
                    <VIcon start size="small">mdi-star</VIcon>
                    {{ detail.vote_average }}
                  </VChip>
                  <VChip v-if="detail.status" size="small" variant="tonal" class="me-2 mb-1">
                    {{ detail.status }}
                  </VChip>
                </div>
                <!-- 操作按钮：系统详情 + 订阅 -->
                <div class="media-actions">
                  <VBtn size="small" color="primary" variant="tonal" @click="openSystemMediaDetail">
                    <VIcon start size="small">mdi-open-in-new</VIcon>
                    系统详情
                  </VBtn>
                  <VBtn
                    v-if="selectedItem?.tmdbid"
                    size="small"
                    class="ms-2"
                    :color="(selectedItem?.status || '未添加订阅') === '未添加订阅' ? 'success' : 'grey'"
                    :variant="(selectedItem?.status || '未添加订阅') === '未添加订阅' ? 'elevated' : 'tonal'"
                    :loading="isSubscribing(selectedItem?.tmdbid)"
                    :disabled="(selectedItem?.status || '未添加订阅') !== '未添加订阅'"
                    @click="subscribe(selectedItem)"
                  >
                    {{ (selectedItem?.status || '未添加订阅') === '未添加订阅' ? '订阅' : selectedItem?.status }}
                  </VBtn>
                </div>
              </div>
            </div>
            <!-- 简介 + 侧边栏 -->
            <div class="media-overview">
              <div class="media-overview-left">
                <div v-if="detail.tagline" class="tagline">{{ detail.tagline }}</div>
                <h2 v-if="detail.overview" class="mt-3">简介</h2>
                <p v-if="detail.overview">{{ detail.overview }}</p>
                <p v-else class="text-grey text-body-2">暂无简介</p>
                <!-- 导演 -->
                <ul v-if="detail.directors?.length" class="media-crew mt-4">
                  <li v-for="director in detail.directors" :key="director.id">
                    <span>{{ director.job }}</span>
                    <span class="crew-name">{{ director.name }}</span>
                  </li>
                </ul>
                <!-- 演员阵容 -->
                <div v-if="detail.tmdb_id" class="cast-section mt-6">
                  <h2 class="cast-title">演员阵容</h2>
                  <div v-if="castLoading" class="text-center py-4">
                    <VProgressCircular indeterminate color="primary" size="small" />
                    <div class="text-caption text-grey mt-2">加载演员信息...</div>
                  </div>
                  <div v-else-if="cast.length" class="cast-list">
                    <div v-for="person in cast" :key="person.id" class="cast-card">
                      <VImg
                        :src="resolvePoster(getW500Image(person.profile_path), 'cast-' + person.id)"
                        cover
                        class="cast-photo"
                        :aspect-ratio="2 / 3"
                        loading="lazy"
                        @error="handlePosterError('cast-' + person.id)"
                      />
                      <div class="cast-name">{{ person.name }}</div>
                      <div class="cast-character">{{ person.character }}</div>
                    </div>
                  </div>
                  <div v-else class="text-grey text-body-2">暂无演员信息</div>
                </div>
                <!-- 外部链接 -->
                <div class="mt-4">
                  <a v-if="detail.tmdb_id" :href="`https://www.themoviedb.org/tv/${detail.tmdb_id}`" target="_blank" class="me-2">
                    <div class="inline-flex cursor-pointer items-center rounded-full bg-gray-600 px-2 py-1 text-sm text-gray-200 ring-1 ring-gray-500 hover:bg-gray-700">
                      <VIcon icon="mdi-link" size="small" />
                      <span class="ms-1">TheMovieDb</span>
                    </div>
                  </a>
                  <a v-if="detail.douban_id" :href="`https://movie.douban.com/subject/${detail.douban_id}`" target="_blank" class="me-2">
                    <div class="inline-flex cursor-pointer items-center rounded-full bg-gray-600 px-2 py-1 text-sm text-gray-200 ring-1 ring-gray-500 hover:bg-gray-700">
                      <VIcon icon="mdi-link" size="small" />
                      <span class="ms-1">豆瓣</span>
                    </div>
                  </a>
                  <a v-if="detail.imdb_id" :href="`https://www.imdb.com/title/${detail.imdb_id}`" target="_blank" class="me-2">
                    <div class="inline-flex cursor-pointer items-center rounded-full bg-gray-600 px-2 py-1 text-sm text-gray-200 ring-1 ring-gray-500 hover:bg-gray-700">
                      <VIcon icon="mdi-link" size="small" />
                      <span class="ms-1">IMDb</span>
                    </div>
                  </a>
                </div>
              </div>
              <!-- 侧边栏：评分 + 事实信息 -->
              <div class="media-overview-right">
                <div class="media-facts">
                  <div v-if="detail.vote_average" class="media-ratings">
                    <VRating :model-value="detail.vote_average" density="compact" length="10" readonly class="ma-2" />
                  </div>
                  <div v-if="detail.tmdb_id" class="media-fact">
                    <span>ID</span>
                    <span class="media-fact-value">{{ detail.tmdb_id }}</span>
                  </div>
                  <div v-if="detail.original_title || detail.original_name" class="media-fact">
                    <span>原始标题</span>
                    <span class="media-fact-value">{{ detail.original_title || detail.original_name }}</span>
                  </div>
                  <div v-if="detail.status" class="media-fact">
                    <span>状态</span>
                    <span class="media-fact-value">{{ detail.status }}</span>
                  </div>
                  <div v-if="detail.release_date || detail.first_air_date" class="media-fact">
                    <span>{{ detail.season_number ? '本季首播' : '发布日期' }}</span>
                    <span class="media-fact-value">{{ detail.season_number
                        ? (detail.first_air_date || detail.release_date)
                        : (detail.release_date || detail.first_air_date) }}</span>
                  </div>
                  <div v-if="detail.season_number && detail.number_of_episodes" class="media-fact">
                    <span>集数</span>
                    <span class="media-fact-value">第 {{ detail.season_number }} 季 共 {{ detail.number_of_episodes }} 集</span>
                  </div>
                  <div v-else-if="detail.number_of_episodes" class="media-fact">
                    <span>集数</span>
                    <span class="media-fact-value">{{ detail.number_of_episodes }} 集</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </VCardText>
      </VCard>
    </VDialog>
    <!-- 成功提示 snackbar -->
    <VSnackbar v-model="snackbarShow" color="success" timeout="3000" location="top">
      {{ snackbarMsg }}
    </VSnackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

// ---- 类型定义 ----

/** 热度列表条目 */
interface HeatItem {
  rank: number
  name: string
  platform: string
  days: string
  heat: number
  plays: string
  tmdbid: number
  poster: string
  actors?: string[] | string
  status?: string
  /** TMDB 季号；>0 表示该剧为多季剧的某一季（如「问心2」-> 2） */
  season?: number
}

/** 媒体详情（松散的 TMDB 结构） */
type MediaDetail = Record<string, any>

// ---- 组件属性 ----

const props = defineProps<{
  api?: { get: (url: string, params?: any) => Promise<any>; post: (url: string, data?: any) => Promise<any> }
  pluginId?: string
}>()
const emit = defineEmits<{ close: [] }>()

// ---- 响应式状态 ----

const items = ref<HeatItem[]>([])
const loading = ref(false)
const fromCache = ref(false)
const updateTime = ref('')
/** 宿主 TMDB 图片域名（由后端 get-cache 下发，替代硬编码 image.tmdb.org） */
const imageDomain = ref('image.tmdb.org')
const detailOpen = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const detail = ref<MediaDetail | null>(null)
const selectedItem = ref<HeatItem | null>(null)
const cast = ref<any[]>([])
const castLoading = ref(false)
/** 正在订阅中的 tmdbid 集合，用于显示按钮加载状态 */
const subscribing = ref<Set<number>>(new Set())
/** 成功提示 snackbar */
const snackbarShow = ref(false)
const snackbarMsg = ref('')

const componentTag = '[MaoyanDianYing/Page]'

/** 本地占位海报（内联 SVG data URI，无外网依赖） */
const POSTER_PLACEHOLDER = "data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22500%22%20height%3D%22750%22%20viewBox%3D%220%200%20500%20750%22%3E%3Crect%20width%3D%22500%22%20height%3D%22750%22%20fill%3D%22%231e1e2e%22%2F%3E%3Crect%20x%3D%22180%22%20y%3D%22270%22%20width%3D%22140%22%20height%3D%22110%22%20rx%3D%2210%22%20fill%3D%22none%22%20stroke%3D%22%23444%22%20stroke-width%3D%223%22%2F%3E%3Ccircle%20cx%3D%22210%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22250%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22290%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22210%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22250%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22290%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ctext%20x%3D%22250%22%20y%3D%22440%22%20text-anchor%3D%22middle%22%20fill%3D%22%23555%22%20font-size%3D%2228%22%20font-family%3D%22system-ui%2Csans-serif%22%3E%E6%9A%82%E6%97%A0%E6%B5%B7%E6%8A%A5%3C%2Ftext%3E%3C%2Fsvg%3E"

/** 加载失败的海报 key 集合 */
const failedPosters = ref<Set<string>>(new Set())

/** 标记海报加载失败 */
function handlePosterError(key: string) {
  const s = new Set(failedPosters.value)
  s.add(key)
  failedPosters.value = s
}

/** 将远程图片 URL 转为宿主图片代理地址，走已配置代理访问被墙的 image.tmdb.org */
function toProxyUrl(url: string): string {
  if (!url || !/^https?:\/\//i.test(url)) return url
  const base = (window as any).MoviePilotAPI?.defaults?.baseURL || '/api/v1/'
  const normalized = base.endsWith('/') ? base : `${base}/`
  const abs = normalized.startsWith('/') ? normalized : `/${normalized}`
  return `${abs}system/img/1?imgurl=${encodeURIComponent(url)}`
}

/** 解析海报 URL：空或失败时返回本地占位；否则走宿主图片代理 */
function resolvePoster(poster: string | undefined, key: string): string {
  if (!poster || failedPosters.value.has(key)) return POSTER_PLACEHOLDER
  return toProxyUrl(poster)
}

// ---- 工具函数 ----

/** 构造插件 API 路径（支持插件 ID 隔离） */
function buildPluginUrl(path: string): string {
  return props.pluginId ? `plugin/${props.pluginId}/${path}` : `plugin/MaoyanDianYing/${path}`
}

/** 判断条目是否正在订阅中 */
function isSubscribing(tmdbid: number | undefined): boolean {
  if (!tmdbid) return false
  return subscribing.value.has(tmdbid)
}

/** 根据状态返回对应颜色 */
function getStatusColor(item: HeatItem): string {
  const status = item.status || '未添加订阅'
  if (status === '影片已入库') return '#4CAF50'
  if (status === '订阅已添加') return '#1976D2'
  return '#9E9E9E'
}

/** 拼接 TMDB 图片 URL（域名由后端下发，默认 image.tmdb.org） */
function getW500Image(posterPath: string): string {
  if (!posterPath) return ''
  const base = posterPath.startsWith('http') ? '' : `https://${imageDomain.value}/t/p/w500`
  return `${base}${posterPath}`
}

/** 拼接类型名称 */
function getGenresName(genres: Array<string | { name: string }>): string {
  if (!Array.isArray(genres)) return ''
  return genres.map((genre) => (typeof genre === 'string' ? genre : genre.name)).join('、')
}

// ---- 数据加载 ----

/** 读取缓存数据，不触发抓取 */
async function loadCache() {
  const url = buildPluginUrl('get-cache')
  try {
    const result = await props.api?.get(url)
    if (result?.enabled === false) {
      items.value = []
      fromCache.value = false
      return 'disabled'
    }
    if (typeof result?.image_domain === 'string' && result.image_domain) {
      imageDomain.value = result.image_domain
    }
    const data = result?.data
    if (data?.rows && Array.isArray(data.rows) && data.rows.length > 0) {
      items.value = data.rows.map((row: HeatItem) => ({ ...row, status: row.status || '未添加订阅' }))
      fromCache.value = true
      updateTime.value = data.update_time ? `更新时间：${data.update_time}` : ''
      return true
    }
    return false
  } catch (e) {
    console.warn(componentTag, '获取缓存失败', e)
    return false
  }
}

/** 请求实时抓取并刷新缓存 */
async function fetchData(forceRefresh = false) {
  if (!props.api) return

  // 页面打开只读缓存；缓存为空时等待后台任务完成，绝不在详情页触发抓取
  if (!forceRefresh) {
    const cacheHit = await loadCache()
    if (cacheHit === true) return
    if (cacheHit === 'disabled') return
    // 缓存为空时轮询等待后台抓取完成
    loading.value = true
    const poll = async (attempt: number): Promise<void> => {
      if (attempt > 10) {
        loading.value = false
        return
      }
      await new Promise(resolve => window.setTimeout(resolve, 2000))
      const cacheResult = await loadCache()
      if (cacheResult === true || cacheResult === 'disabled') {
        loading.value = false
        return
      }
      await poll(attempt + 1)
    }
    await poll(1)
    return
  }

  // 用户手动点击刷新：调用 run-once API
  const url = buildPluginUrl('run-once')
  loading.value = true
  try {
    const result = await props.api.post(url)
    const rows = result?.data?.rows
    if (Array.isArray(rows)) {
      items.value = rows.map((row: HeatItem) => ({ ...row, status: row.status || '未添加订阅' }))
      fromCache.value = false
    }
  } catch (e) {
    console.error(componentTag, '获取数据失败', e)
  } finally {
    loading.value = false
  }
}

/** 点击刷新按钮 */
function refreshData() {
  void fetchData(true)
}

// ---- 订阅功能 ----

/** 订阅指定条目 */
async function subscribe(item: HeatItem) {
  const url = buildPluginUrl('subscribe')
  if (!props.api) return

  subscribing.value.add(item.tmdbid)
  try {
    const result = await props.api.post(url, {
      tmdbid: item.tmdbid,
      name: item.name,
      season: item.season || 0,
    })
    if (result?.success) {
      // 立即更新当前项状态，按钮同步变灰
      item.status = '订阅已添加'
      if (selectedItem.value?.tmdbid === item.tmdbid) {
        selectedItem.value = { ...selectedItem.value, status: '订阅已添加' }
      }
      // 显示成功提示
      snackbarMsg.value = result?.message || '订阅已添加'
      snackbarShow.value = true
    } else {
      alert(result?.message || '订阅失败，请稍后重试')
    }
  } catch (e) {
    console.error(componentTag, '订阅失败', e)
    alert('订阅失败，请检查网络连接')
  }
  subscribing.value.delete(item.tmdbid)

  // 重新读取缓存以同步状态
  await loadCache()
  if (selectedItem.value?.tmdbid) {
    const updated = items.value.find((row) => row.tmdbid === selectedItem.value?.tmdbid)
    if (updated) {
      selectedItem.value = { ...selectedItem.value, status: updated.status }
    }
  }
}

// ---- 详情弹窗 ----

/** 打开插件内媒体详情弹窗 */
async function openMediaDetail(item: HeatItem) {
  if (!item.tmdbid) return
  selectedItem.value = item
  detailOpen.value = true
  detailLoading.value = true
  detailError.value = ''
  detail.value = null

  const url = `media/${encodeURIComponent(String(item.tmdbid))}`
  try {
    const result = await props.api?.get(url, { params: { media_source: 'themoviedb', type_name: '电视剧' } })
    // pluginApi envelope 模式：{ success, message, data }
    if (result?.data && typeof result.data === 'object' && !Array.isArray(result.data)) {
      detail.value = result.data
    } else if (result && typeof result === 'object') {
      detail.value = result
    }
    // 带季数条目：宿主 /media/{id} 返回的是剧集主记录（第 1 季视角），
    // 用该季数据覆盖简介/首播/海报/演员，避免详情页显示成第 1 季。
    const seasonCastReady = item.season ? await applySeasonDetail(item) : false
    if (detail.value?.tmdb_id && !seasonCastReady) {
      await fetchCast(detail.value.tmdb_id)
    }
  } catch (error: any) {
    detailError.value = error?.message || '媒体详情加载失败'
  } finally {
    detailLoading.value = false
  }
}

/** 用指定季的详情覆盖详情弹窗内容（简介/首播/海报/演员/集数） */
async function applySeasonDetail(item: HeatItem): Promise<boolean> {
  if (!item.season || !detail.value) return false
  try {
    const url = buildPluginUrl('get-season')
    const result = await props.api?.get(url, { params: { tmdbid: item.tmdbid, season: item.season } })
    const seasonData = result?.data
    if (!seasonData) return false
    // 仅覆盖季级字段，其余（类型/时长/评分等）保留宿主数据
    if (seasonData.overview) detail.value.overview = seasonData.overview
    if (seasonData.air_date) detail.value.first_air_date = seasonData.air_date
    if (seasonData.poster_path) detail.value.poster_path = seasonData.poster_path
    if (seasonData.vote_average) detail.value.vote_average = seasonData.vote_average
    if (seasonData.episode_count) detail.value.number_of_episodes = seasonData.episode_count
    detail.value.season_number = seasonData.season_number
    // 季详情自带演员时直接采用，避免 cast 接口取到主记录（第 1 季）演员
    if (seasonData.cast?.length) {
      cast.value = seasonData.cast
      return true
    }
  } catch (e) {
    console.warn(componentTag, '季详情加载失败', e)
  }
  return false
}

/** 加载演员阵容 */
async function fetchCast(tmdbId: number) {
  castLoading.value = true
  cast.value = []
  try {
    const url = buildPluginUrl('get-cast')
    const result = await props.api?.get(url, { params: { tmdbid: tmdbId } })
    cast.value = result?.data || []
  } catch (e) {
    console.warn(componentTag, '演员阵容加载失败', e)
  } finally {
    castLoading.value = false
  }
}

/** 重试加载详情 */
function retryMediaDetail() {
  if (selectedItem.value) void openMediaDetail(selectedItem.value)
}

/** 关闭详情弹窗 */
function closeMediaDetail() {
  detailOpen.value = false
  detail.value = null
  detailError.value = ''
  selectedItem.value = null
}

/** 关闭插件页面：弹窗开→只关弹窗回列表；否则 emit('close') 通知宿主关闭（PluginDataDialog.vue:198 监听 @close） */
function closePage() {
  if (detailOpen.value) {
    detailOpen.value = false
    return
  }
  emit('close')
}

/** 跳转到系统原生媒体详情页 */
function openSystemMediaDetail() {
  if (!selectedItem.value?.tmdbid) return
  const url = `${window.location.origin}${window.location.pathname}#/media?media_source=themoviedb&media_id=${selectedItem.value.tmdbid}&title=${encodeURIComponent(selectedItem.value.name)}&type=电视剧`
  window.open(url, '_blank', 'noopener,noreferrer')
}

// ---- 生命周期 ----

onMounted(() => {
  void fetchData(false)
})
</script>

<style scoped>
.maoyan-heat-list {
  padding: 16px;
}
.cursor-pointer {
  cursor: pointer;
  transition: transform 0.2s ease;
}
.cursor-pointer:hover {
  transform: scale(1.05);
}
.gap-2 {
  gap: 8px;
}

/* ---- MediaDetailView-style layout ---- */
.media-detail-card .media-poster {
  overflow: hidden;
  border-radius: var(--app-surface-radius, 12px);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 10%), 0 1px 2px -1px rgba(0, 0, 0, 10%);
  inline-size: 8rem;
  transition: border-radius 0.2s ease;
}
.media-detail-card .media-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-block-start: 1rem;
}
.media-detail-card .media-title {
  display: flex;
  flex: 1 1 0%;
  flex-direction: column;
  margin-block-start: 1rem;
  text-align: center;
}
.media-detail-card .media-title > h1 {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 2rem;
  inline-size: 100%;
}
@media (width < 1024px) {
  .media-detail-card .media-title > h1 {
    align-items: center;
    text-align: center;
  }
}
.media-detail-card .media-attributes {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  margin-block-start: 0.25rem;
  font-size: 0.875rem;
  line-height: 1.25rem;
}
.media-detail-card .media-actions {
  display: flex;
  gap: 0.5rem;
  margin-block-start: 1rem;
  justify-content: center;
}
.media-detail-card .media-overview {
  display: flex;
  flex-direction: column;
  padding-block: 2rem 1rem;
}
.media-detail-card .media-overview-left {
  flex: 1 1 0%;
  min-inline-size: 0;
}
.media-detail-card .media-overview h2 {
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.75rem;
}
.media-detail-card .tagline {
  font-size: 1.25rem;
  font-style: italic;
  line-height: 1.75rem;
  margin-block-end: 1rem;
}
.media-detail-card ul.media-crew {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-block-start: 1.5rem;
}
.media-detail-card ul.media-crew > li {
  display: flex;
  flex-direction: column;
  font-weight: 700;
  grid-column: span 1 / span 1;
}
.media-detail-card .crew-name {
  font-weight: 400;
}
@media (width >= 1280px) {
  .media-detail-card .media-poster { inline-size: 13rem; }
  .media-detail-card .media-title > h1 { font-size: 2.25rem; line-height: 2.5rem; }
}
.media-detail-card .media-overview-right {
  display: none;
}
.media-detail-card .media-facts {
  display: flex;
  flex-direction: column;
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid rgb(55 65 81 / 1);
}
.media-detail-card .media-ratings {
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgb(55 65 81 / 1);
  font-weight: 500;
  padding: 0.5rem 1rem;
}
.media-detail-card .media-fact {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid rgb(55 65 81 / 1);
  padding: 0.5rem 1rem;
}
.media-detail-card .media-fact-value {
  font-weight: 700;
}
@media (width >= 768px) {
  .media-detail-card .media-poster { inline-size: 11rem; }
}
@media (width >= 1024px) {
  .media-detail-card .media-overview-right { display: block; inline-size: 16rem; }
  .media-detail-card .media-overview { flex-direction: row; }
  .media-detail-card .media-overview-left { margin-inline-end: 2rem; }
  .media-detail-card .media-header { flex-direction: row; align-items: flex-end; gap: 3rem; }
  .media-detail-card .media-title { margin-block-start: 0; margin-inline-end: 1rem; text-align: start; }
  .media-detail-card .media-attributes { justify-content: flex-start; }
  .media-detail-card .media-actions { justify-content: flex-start; }
}
@media (width >= 1280px) {
  .media-detail-card .media-poster { inline-size: 13rem; }
}
.media-detail-card .cast-section .cast-title {
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.75rem;
  margin-block-end: 1rem;
}
.media-detail-card .cast-list {
  display: flex;
  gap: 0.75rem;
  overflow-x: auto;
  padding-block-end: 0.5rem;
}
.media-detail-card .cast-card {
  flex: 0 0 auto;
  inline-size: 7rem;
  text-align: center;
}
.media-detail-card .cast-photo {
  border-radius: 0.5rem;
  margin-block-end: 0.5rem;
}
.media-detail-card .cast-name {
  font-size: 0.875rem;
  font-weight: 700;
  line-height: 1.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.media-detail-card .cast-character {
  font-size: 0.75rem;
  line-height: 1rem;
  color: rgb(156 163 175);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 响应式自适应网格：保证每张卡片至少 390px，放得下 4 张就排 4 列，空间小自动退到 3 列甚至 2 列，卡片永不被挤压变形 */
.maoyan-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(390px, 1fr));
  gap: 12px;
  width: 100%;
}
.maoyan-card-wrapper {
  display: flex;
  min-width: 0;
}
.maoyan-card-wrapper .v-card {
  width: 100%;
}
</style>
