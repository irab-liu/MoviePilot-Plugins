<template>
  <div class="maoyan-heat-list">
    <!-- 标题栏：标题 + TOP30 + 缓存标签 + 更新时间 + 刷新按钮 -->
    <VRow>
      <VCol cols="12">
        <div class="d-flex align-center mb-4 flex-wrap gap-2">
          <VIcon size="x-small" start>mdi-fire</VIcon>
          <span class="text-h6 font-weight-bold">猫眼发现</span>
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
        <div class="text-caption text-grey mt-2">正在抓取猫眼发现数据...</div>
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

    <!-- 媒体详情弹窗（旧前端/浏览器降级：宿主未提供 ui.dialog 时内联渲染） -->
    <MediaDetailDialog
      v-if="!hostDialogAvailable"
      v-model="detailOpenLocal"
      :detail="detail"
      :loading="detailLoading"
      :error="detailError"
      :selected-item="selectedItem"
      :cast="cast"
      :cast-loading="castLoading"
      :subscribing-ids="Array.from(subscribing)"
      :image-domain="imageDomain"
      @retry="retryMediaDetail"
      @system-detail="openSystemMediaDetail"
      @subscribe="handleDetailSubscribe"
      @close="handleDetailClosedByDialog"
    />
    <!-- 成功提示 snackbar -->
    <VSnackbar v-model="snackbarShow" color="success" timeout="3000" location="top">
      {{ snackbarMsg }}
    </VSnackbar>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import MediaDetailDialog from './MediaDetailDialog.vue'

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
  /** 新版前端注入的宿主 SDK；提供 ui.dialog 时详情走宿主弹窗，旧前端回退内联渲染 */
  hostSdk?: {
    ui?: {
      dialog?: (
        component: any,
        props?: Record<string, any>,
        events?: Record<string, (...args: any[]) => void>,
        options?: { closeOn?: string[] | false },
      ) => { close: () => void; updateProps: (props: Record<string, any>) => void }
    }
  }
}>()
const emit = defineEmits<{ close: [] }>()

// ---- 响应式状态 ----

const items = ref<HeatItem[]>([])
const loading = ref(false)
const fromCache = ref(false)
const updateTime = ref('')
/** 宿主 TMDB 图片域名（由后端 get-cache 下发，替代硬编码 image.tmdb.org） */
const imageDomain = ref('image.tmdb.org')
/** 内联降级模式的详情弹窗开关 */
const detailOpenLocal = ref(false)
/** 宿主 ui.dialog 返回的控制器；非空表示详情已通过宿主弹窗打开 */
const detailController = ref<{ close: () => void; updateProps: (props: Record<string, any>) => void } | null>(null)
/** 新版前端提供 ui.dialog 时使用宿主弹窗，否则内联渲染详情弹窗 */
const hostDialogAvailable = computed(() => Boolean(props.hostSdk?.ui?.dialog))
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
  syncDetailDialog()
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
  syncDetailDialog()

  // 重新读取缓存以同步状态
  await loadCache()
  if (selectedItem.value?.tmdbid) {
    const updated = items.value.find((row) => row.tmdbid === selectedItem.value?.tmdbid)
    if (updated) {
      selectedItem.value = { ...selectedItem.value, status: updated.status }
    }
  }
  syncDetailDialog()
}

// ---- 详情弹窗 ----

/** 汇总详情弹窗展示所需的一帧快照，宿主弹窗通过 updateProps 同步 */
function detailSnapshot() {
  return {
    detail: detail.value,
    loading: detailLoading.value,
    error: detailError.value,
    selectedItem: selectedItem.value,
    cast: cast.value,
    castLoading: castLoading.value,
    subscribingIds: Array.from(subscribing.value),
    imageDomain: imageDomain.value,
  }
}

/** 宿主弹窗打开后，把最新详情状态推入弹窗 */
function syncDetailDialog() {
  detailController.value?.updateProps(detailSnapshot())
}

/** 打开详情弹窗：新版前端走宿主 ui.dialog，旧前端/浏览器回退内联渲染 */
function showDetailDialog() {
  if (hostDialogAvailable.value) {
    if (detailController.value) {
      syncDetailDialog()
      return
    }
    detailController.value = props.hostSdk!.ui!.dialog!(
      MediaDetailDialog,
      detailSnapshot(),
      {
        close: handleDetailClosedByDialog,
        retry: retryMediaDetail,
        'system-detail': openSystemMediaDetail,
        subscribe: handleDetailSubscribe,
      },
      { closeOn: ['close'] },
    )
    return
  }
  detailOpenLocal.value = true
}

/** 关闭详情弹窗并清理详情状态 */
function closeDetailDialog() {
  detailController.value?.close()
  detailController.value = null
  detailOpenLocal.value = false
  resetDetailState()
}

/** 详情弹窗自己发起关闭（原生关闭按钮 / 降级内联弹窗） */
function handleDetailClosedByDialog() {
  detailController.value = null
  detailOpenLocal.value = false
  resetDetailState()
}

/** 清空详情状态，回到列表 */
function resetDetailState() {
  detailLoading.value = false
  detailError.value = ''
  detail.value = null
  selectedItem.value = null
  cast.value = []
  castLoading.value = false
}

/** 详情弹窗内的订阅按钮 */
function handleDetailSubscribe() {
  if (selectedItem.value) void subscribe(selectedItem.value)
}

/** 打开插件内媒体详情弹窗 */
async function openMediaDetail(item: HeatItem) {
  if (!item.tmdbid) return
  selectedItem.value = item
  detailLoading.value = true
  detailError.value = ''
  detail.value = null
  cast.value = []
  castLoading.value = false
  showDetailDialog()
  syncDetailDialog()

  const url = `media/${encodeURIComponent(String(item.tmdbid))}`
  try {
    const result = await props.api?.get(url, { params: { media_source: 'themoviedb', type_name: '电视剧' } })
    // pluginApi envelope 模式：{ success, message, data }
    if (result?.data && typeof result.data === 'object' && !Array.isArray(result.data)) {
      detail.value = result.data
    } else if (result && typeof result === 'object') {
      detail.value = result
    }
    syncDetailDialog()
    // 带季数条目：宿主 /media/{id} 返回的是剧集主记录（第 1 季视角），
    // 用该季数据覆盖简介/首播/海报/演员，避免详情页显示成第 1 季。
    const seasonCastReady = item.season ? await applySeasonDetail(item) : false
    if (detail.value?.tmdb_id && !seasonCastReady) {
      await fetchCast(detail.value.tmdb_id)
    }
  } catch (error: any) {
    detailError.value = error?.message || '媒体详情加载失败'
    syncDetailDialog()
  } finally {
    detailLoading.value = false
    syncDetailDialog()
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
      syncDetailDialog()
      return true
    }
    syncDetailDialog()
  } catch (e) {
    console.warn(componentTag, '季详情加载失败', e)
  }
  return false
}

/** 加载演员阵容 */
async function fetchCast(tmdbId: number) {
  castLoading.value = true
  cast.value = []
  syncDetailDialog()
  try {
    const url = buildPluginUrl('get-cast')
    const result = await props.api?.get(url, { params: { tmdbid: tmdbId } })
    cast.value = result?.data || []
  } catch (e) {
    console.warn(componentTag, '演员阵容加载失败', e)
  } finally {
    castLoading.value = false
    syncDetailDialog()
  }
}

/** 重试加载详情 */
function retryMediaDetail() {
  if (selectedItem.value) void openMediaDetail(selectedItem.value)
}

/** 关闭插件页面：详情弹窗开→只关详情回列表；否则 emit('close') 通知宿主关闭（PluginDataDialog.vue 监听 @close） */
function closePage() {
  if (detailController.value || detailOpenLocal.value) {
    closeDetailDialog()
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
