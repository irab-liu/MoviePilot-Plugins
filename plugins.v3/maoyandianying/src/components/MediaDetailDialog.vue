<template>
  <VDialog
    :model-value="modelValue"
    max-width="1000"
    scrollable
    @update:model-value="onModelUpdate"
  >
    <VCard class="media-detail-card">
      <VCardTitle class="d-flex align-center px-4 pt-4 pb-0">
        <span class="text-h6">{{ title }}</span>
        <VSpacer />
        <VBtn
          icon="mdi-close"
          variant="text"
          data-native-dialog-close
          @click="onClose"
        />
      </VCardTitle>
      <VCardText class="px-4 pb-4">
        <!-- 详情加载中 -->
        <div v-if="loading" class="text-center py-12">
          <VProgressCircular indeterminate color="primary" />
          <div class="text-caption text-grey mt-3">正在加载媒体详情...</div>
        </div>
        <!-- 详情错误 -->
        <VAlert v-else-if="error" type="error" variant="tonal" class="my-4">
          {{ error }}
          <template #append>
            <VBtn size="small" variant="tonal" @click="$emit('retry')">重试</VBtn>
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
                <VBtn size="small" color="primary" variant="tonal" @click="$emit('system-detail')">
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
                  @click="$emit('subscribe')"
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
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

/** 热度列表条目（详情弹窗展示所需字段） */
interface HeatItem {
  rank?: number
  name: string
  platform?: string
  days?: string
  heat?: number
  plays?: string
  tmdbid?: number
  poster?: string
  actors?: string[] | string
  status?: string
  season?: number
}

const props = defineProps<{
  modelValue: boolean
  detail: Record<string, any> | null
  loading: boolean
  error: string
  selectedItem: HeatItem | null
  cast: any[]
  castLoading: boolean
  subscribingIds: number[]
  imageDomain: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  close: []
  retry: []
  'system-detail': []
  subscribe: []
}>()

const title = computed(
  () => (props.detail as any)?.title || props.selectedItem?.name || '媒体详情',
)

const POSTER_PLACEHOLDER = "data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22500%22%20height%3D%22750%22%20viewBox%3D%220%200%20500%20750%22%3E%3Crect%20width%3D%22500%22%20height%3D%22750%22%20fill%3D%22%231e1e2e%22%2F%3E%3Crect%20x%3D%22180%22%20y%3D%22270%22%20width%3D%22140%22%20height%3D%22110%22%20rx%3D%2210%22%20fill%3D%22none%22%20stroke%3D%22%23444%22%20stroke-width%3D%223%22%2F%3E%3Ccircle%20cx%3D%22210%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22250%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22290%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22210%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22250%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22290%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ctext%20x%3D%22250%22%20y%3D%22440%22%20text-anchor%3D%22middle%22%20fill%3D%22%23555%22%20font-size%3D%2228%22%20font-family%3D%22system-ui%2Csans-serif%22%3E%E6%9A%82%E6%97%A0%E6%B5%B7%E6%8A%A5%3C%2Ftext%3E%3C%2Fsvg%3E"
const failedPosters = ref<Set<string>>(new Set())

function onModelUpdate(value: boolean) {
  emit('update:modelValue', value)
  if (!value) emit('close')
}

function onClose() {
  emit('update:modelValue', false)
  emit('close')
}

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

/** 拼接 TMDB 图片 URL（域名由后端下发，默认 image.tmdb.org） */
function getW500Image(posterPath: string): string {
  if (!posterPath) return ''
  const base = posterPath.startsWith('http') ? '' : `https://${props.imageDomain}/t/p/w500`
  return `${base}${posterPath}`
}

/** 拼接类型名称 */
function getGenresName(genres: Array<string | { name: string }>): string {
  if (!Array.isArray(genres)) return ''
  return genres.map((genre) => (typeof genre === 'string' ? genre : genre.name)).join('、')
}

/** 判断条目是否正在订阅中 */
function isSubscribing(tmdbid: number | undefined): boolean {
  if (!tmdbid) return false
  return props.subscribingIds.includes(tmdbid)
}
</script>

<style scoped>
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
</style>
