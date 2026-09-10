import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-pcqpp-6-.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {createTextVNode:_createTextVNode,resolveComponent:_resolveComponent,withCtx:_withCtx,createVNode:_createVNode,createElementVNode:_createElementVNode,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,toDisplayString:_toDisplayString,createElementBlock:_createElementBlock,renderList:_renderList,Fragment:_Fragment,normalizeClass:_normalizeClass,normalizeStyle:_normalizeStyle} = await importShared('vue');

const _hoisted_1 = { class: "maoyan-heat-list" };
const _hoisted_2 = { class: "d-flex align-center mb-4 flex-wrap gap-2" };
const _hoisted_3 = {
  key: 1,
  class: "text-caption text-grey ml-1"
};
const _hoisted_4 = { style: { "position": "relative" } };
const _hoisted_5 = { class: "d-flex align-center mb-1" };
const _hoisted_6 = { style: { "font-size": "12px", "font-weight": "bold" } };
const _hoisted_7 = {
  class: "text-grey mb-1",
  style: { "font-size": "11px" }
};
const _hoisted_8 = {
  class: "text-grey mb-1",
  style: { "font-size": "11px" }
};
const _hoisted_9 = {
  class: "text-grey mb-1",
  style: { "font-size": "11px" }
};
const _hoisted_10 = {
  class: "text-grey mb-1",
  style: { "font-size": "11px" }
};
const _hoisted_11 = {
  key: 0,
  class: "text-grey mb-1",
  style: { "font-size": "11px" }
};
const _hoisted_12 = { class: "text-h6" };
const _hoisted_13 = {
  key: 0,
  class: "text-center py-12"
};
const _hoisted_14 = {
  key: 2,
  class: "media-page"
};
const _hoisted_15 = { class: "media-header" };
const _hoisted_16 = { class: "media-poster" };
const _hoisted_17 = { class: "w-full h-full" };
const _hoisted_18 = { class: "media-title" };
const _hoisted_19 = { class: "d-flex flex-column flex-lg-row align-items-center align-items-lg-baseline" };
const _hoisted_20 = {
  key: 0,
  class: "text-lg ms-1"
};
const _hoisted_21 = { class: "media-attributes" };
const _hoisted_22 = { key: 0 };
const _hoisted_23 = {
  key: 1,
  class: "mx-1"
};
const _hoisted_24 = { key: 2 };
const _hoisted_25 = { class: "mt-2" };
const _hoisted_26 = { class: "media-actions" };
const _hoisted_27 = { class: "media-overview" };
const _hoisted_28 = { class: "media-overview-left" };
const _hoisted_29 = {
  key: 0,
  class: "tagline"
};
const _hoisted_30 = {
  key: 1,
  class: "mt-3"
};
const _hoisted_31 = { key: 2 };
const _hoisted_32 = {
  key: 3,
  class: "text-grey text-body-2"
};
const _hoisted_33 = {
  key: 4,
  class: "media-crew mt-4"
};
const _hoisted_34 = { class: "crew-name" };
const _hoisted_35 = {
  key: 5,
  class: "cast-section mt-6"
};
const _hoisted_36 = {
  key: 0,
  class: "text-center py-4"
};
const _hoisted_37 = {
  key: 1,
  class: "cast-list"
};
const _hoisted_38 = { class: "cast-name" };
const _hoisted_39 = { class: "cast-character" };
const _hoisted_40 = {
  key: 2,
  class: "text-grey text-body-2"
};
const _hoisted_41 = { class: "mt-4" };
const _hoisted_42 = ["href"];
const _hoisted_43 = { class: "inline-flex cursor-pointer items-center rounded-full bg-gray-600 px-2 py-1 text-sm text-gray-200 ring-1 ring-gray-500 hover:bg-gray-700" };
const _hoisted_44 = ["href"];
const _hoisted_45 = { class: "inline-flex cursor-pointer items-center rounded-full bg-gray-600 px-2 py-1 text-sm text-gray-200 ring-1 ring-gray-500 hover:bg-gray-700" };
const _hoisted_46 = ["href"];
const _hoisted_47 = { class: "inline-flex cursor-pointer items-center rounded-full bg-gray-600 px-2 py-1 text-sm text-gray-200 ring-1 ring-gray-500 hover:bg-gray-700" };
const _hoisted_48 = { class: "media-overview-right" };
const _hoisted_49 = { class: "media-facts" };
const _hoisted_50 = {
  key: 0,
  class: "media-ratings"
};
const _hoisted_51 = {
  key: 1,
  class: "media-fact"
};
const _hoisted_52 = { class: "media-fact-value" };
const _hoisted_53 = {
  key: 2,
  class: "media-fact"
};
const _hoisted_54 = { class: "media-fact-value" };
const _hoisted_55 = {
  key: 3,
  class: "media-fact"
};
const _hoisted_56 = { class: "media-fact-value" };
const _hoisted_57 = {
  key: 4,
  class: "media-fact"
};
const _hoisted_58 = { class: "media-fact-value" };
const {ref,onMounted} = await importShared('vue');

const componentTag = "[MaoyanDianYing/Page]";
const POSTER_PLACEHOLDER = "data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22500%22%20height%3D%22750%22%20viewBox%3D%220%200%20500%20750%22%3E%3Crect%20width%3D%22500%22%20height%3D%22750%22%20fill%3D%22%231e1e2e%22%2F%3E%3Crect%20x%3D%22180%22%20y%3D%22270%22%20width%3D%22140%22%20height%3D%22110%22%20rx%3D%2210%22%20fill%3D%22none%22%20stroke%3D%22%23444%22%20stroke-width%3D%223%22%2F%3E%3Ccircle%20cx%3D%22210%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22250%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22290%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22210%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22250%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22290%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ctext%20x%3D%22250%22%20y%3D%22440%22%20text-anchor%3D%22middle%22%20fill%3D%22%23555%22%20font-size%3D%2228%22%20font-family%3D%22system-ui%2Csans-serif%22%3E%E6%9A%82%E6%97%A0%E6%B5%B7%E6%8A%A5%3C%2Ftext%3E%3C%2Fsvg%3E";
const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "HeatList",
  props: {
    api: {},
    pluginId: {}
  },
  emits: ["close"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const emit = __emit;
    const items = ref([]);
    const loading = ref(false);
    const fromCache = ref(false);
    const updateTime = ref("");
    const detailOpen = ref(false);
    const detailLoading = ref(false);
    const detailError = ref("");
    const detail = ref(null);
    const selectedItem = ref(null);
    const cast = ref([]);
    const castLoading = ref(false);
    const subscribing = ref(/* @__PURE__ */ new Set());
    const snackbarShow = ref(false);
    const snackbarMsg = ref("");
    const failedPosters = ref(/* @__PURE__ */ new Set());
    function handlePosterError(key) {
      const s = new Set(failedPosters.value);
      s.add(key);
      failedPosters.value = s;
    }
    function toProxyUrl(url) {
      if (!url || !/^https?:\/\//i.test(url)) return url;
      const base = window.MoviePilotAPI?.defaults?.baseURL || "/api/v1/";
      const normalized = base.endsWith("/") ? base : `${base}/`;
      const abs = normalized.startsWith("/") ? normalized : `/${normalized}`;
      return `${abs}system/img/1?imgurl=${encodeURIComponent(url)}`;
    }
    function resolvePoster(poster, key) {
      if (!poster || failedPosters.value.has(key)) return POSTER_PLACEHOLDER;
      return toProxyUrl(poster);
    }
    function buildPluginUrl(path) {
      return props.pluginId ? `plugin/${props.pluginId}/${path}` : `plugin/MaoyanDianYing/${path}`;
    }
    function isSubscribing(tmdbid) {
      if (!tmdbid) return false;
      return subscribing.value.has(tmdbid);
    }
    function getStatusColor(item) {
      const status = item.status || "未添加订阅";
      if (status === "影片已入库") return "#4CAF50";
      if (status === "订阅已添加") return "#1976D2";
      return "#9E9E9E";
    }
    function getW500Image(posterPath) {
      if (!posterPath) return "";
      const base = posterPath.startsWith("http") ? "" : "https://image.tmdb.org/t/p/w500";
      return `${base}${posterPath}`;
    }
    function getGenresName(genres) {
      if (!Array.isArray(genres)) return "";
      return genres.map((genre) => typeof genre === "string" ? genre : genre.name).join("、");
    }
    async function loadCache() {
      const url = buildPluginUrl("get-cache");
      try {
        const result = await props.api?.get(url);
        if (result?.enabled === false) {
          items.value = [];
          fromCache.value = false;
          return "disabled";
        }
        const data = result?.data;
        if (data?.rows && Array.isArray(data.rows) && data.rows.length > 0) {
          items.value = data.rows.map((row) => ({ ...row, status: row.status || "未添加订阅" }));
          fromCache.value = true;
          updateTime.value = data.update_time ? `更新时间：${data.update_time}` : "";
          return true;
        }
        return false;
      } catch (e) {
        console.warn(componentTag, "获取缓存失败", e);
        return false;
      }
    }
    async function fetchData(forceRefresh = false) {
      if (!props.api) return;
      if (!forceRefresh) {
        const cacheHit = await loadCache();
        if (cacheHit === true) return;
        if (cacheHit === "disabled") return;
        loading.value = true;
        const poll = async (attempt) => {
          if (attempt > 10) {
            loading.value = false;
            return;
          }
          await new Promise((resolve) => window.setTimeout(resolve, 2e3));
          const cacheResult = await loadCache();
          if (cacheResult === true || cacheResult === "disabled") {
            loading.value = false;
            return;
          }
          await poll(attempt + 1);
        };
        await poll(1);
        return;
      }
      const url = buildPluginUrl("run-once");
      loading.value = true;
      try {
        const result = await props.api.post(url);
        const rows = result?.data?.rows;
        if (Array.isArray(rows)) {
          items.value = rows.map((row) => ({ ...row, status: row.status || "未添加订阅" }));
          fromCache.value = false;
        }
      } catch (e) {
        console.error(componentTag, "获取数据失败", e);
      } finally {
        loading.value = false;
      }
    }
    function refreshData() {
      void fetchData(true);
    }
    async function subscribe(item) {
      const url = buildPluginUrl("subscribe");
      if (!props.api) return;
      subscribing.value.add(item.tmdbid);
      try {
        const result = await props.api.post(url, { tmdbid: item.tmdbid, name: item.name });
        if (result?.success) {
          item.status = "订阅已添加";
          if (selectedItem.value?.tmdbid === item.tmdbid) {
            selectedItem.value = { ...selectedItem.value, status: "订阅已添加" };
          }
          snackbarMsg.value = result?.message || "订阅已添加";
          snackbarShow.value = true;
        } else {
          alert(result?.message || "订阅失败，请稍后重试");
        }
      } catch (e) {
        console.error(componentTag, "订阅失败", e);
        alert("订阅失败，请检查网络连接");
      }
      subscribing.value.delete(item.tmdbid);
      await loadCache();
      if (selectedItem.value?.tmdbid) {
        const updated = items.value.find((row) => row.tmdbid === selectedItem.value?.tmdbid);
        if (updated) {
          selectedItem.value = { ...selectedItem.value, status: updated.status };
        }
      }
    }
    async function openMediaDetail(item) {
      if (!item.tmdbid) return;
      selectedItem.value = item;
      detailOpen.value = true;
      detailLoading.value = true;
      detailError.value = "";
      detail.value = null;
      const url = `media/${encodeURIComponent(String(item.tmdbid))}`;
      try {
        const result = await props.api?.get(url, { params: { media_source: "themoviedb", type_name: "电视剧" } });
        if (result?.data && typeof result.data === "object" && !Array.isArray(result.data)) {
          detail.value = result.data;
        } else if (result && typeof result === "object") {
          detail.value = result;
        }
        if (detail.value?.tmdb_id) {
          await fetchCast(detail.value.tmdb_id);
        }
      } catch (error) {
        detailError.value = error?.message || "媒体详情加载失败";
      } finally {
        detailLoading.value = false;
      }
    }
    async function fetchCast(tmdbId) {
      castLoading.value = true;
      cast.value = [];
      try {
        const url = buildPluginUrl("get-cast");
        const result = await props.api?.get(url, { params: { tmdbid: tmdbId } });
        cast.value = result?.data || [];
      } catch (e) {
        console.warn(componentTag, "演员阵容加载失败", e);
      } finally {
        castLoading.value = false;
      }
    }
    function retryMediaDetail() {
      if (selectedItem.value) void openMediaDetail(selectedItem.value);
    }
    function closeMediaDetail() {
      detailOpen.value = false;
      detail.value = null;
      detailError.value = "";
      selectedItem.value = null;
    }
    function closePage() {
      if (detailOpen.value) {
        detailOpen.value = false;
        return;
      }
      emit("close");
    }
    function openSystemMediaDetail() {
      if (!selectedItem.value?.tmdbid) return;
      const url = `${window.location.origin}${window.location.pathname}#/media?media_source=themoviedb&media_id=${selectedItem.value.tmdbid}&title=${encodeURIComponent(selectedItem.value.name)}&type=电视剧`;
      window.open(url, "_blank", "noopener,noreferrer");
    }
    onMounted(() => {
      void fetchData(false);
    });
    return (_ctx, _cache) => {
      const _component_VIcon = _resolveComponent("VIcon");
      const _component_VChip = _resolveComponent("VChip");
      const _component_VSpacer = _resolveComponent("VSpacer");
      const _component_VBtn = _resolveComponent("VBtn");
      const _component_VCol = _resolveComponent("VCol");
      const _component_VRow = _resolveComponent("VRow");
      const _component_VProgressCircular = _resolveComponent("VProgressCircular");
      const _component_VAlert = _resolveComponent("VAlert");
      const _component_VImg = _resolveComponent("VImg");
      const _component_VCard = _resolveComponent("VCard");
      const _component_VCardTitle = _resolveComponent("VCardTitle");
      const _component_VSkeletonLoader = _resolveComponent("VSkeletonLoader");
      const _component_VRating = _resolveComponent("VRating");
      const _component_VCardText = _resolveComponent("VCardText");
      const _component_VDialog = _resolveComponent("VDialog");
      const _component_VSnackbar = _resolveComponent("VSnackbar");
      return _openBlock(), _createElementBlock("div", _hoisted_1, [
        _createVNode(_component_VRow, null, {
          default: _withCtx(() => [
            _createVNode(_component_VCol, { cols: "12" }, {
              default: _withCtx(() => [
                _createElementVNode("div", _hoisted_2, [
                  _createVNode(_component_VIcon, {
                    size: "x-small",
                    start: ""
                  }, {
                    default: _withCtx(() => [..._cache[4] || (_cache[4] = [
                      _createTextVNode("mdi-fire", -1)
                    ])]),
                    _: 1
                  }),
                  _cache[9] || (_cache[9] = _createElementVNode("span", { class: "text-h6 font-weight-bold" }, "猫眼网播热度榜", -1)),
                  _createVNode(_component_VChip, {
                    size: "small",
                    color: "error",
                    class: "ml-1"
                  }, {
                    default: _withCtx(() => [..._cache[5] || (_cache[5] = [
                      _createTextVNode("TOP30", -1)
                    ])]),
                    _: 1
                  }),
                  fromCache.value ? (_openBlock(), _createBlock(_component_VChip, {
                    key: 0,
                    size: "small",
                    color: "success",
                    variant: "tonal"
                  }, {
                    default: _withCtx(() => [..._cache[6] || (_cache[6] = [
                      _createTextVNode("缓存", -1)
                    ])]),
                    _: 1
                  })) : _createCommentVNode("", true),
                  updateTime.value ? (_openBlock(), _createElementBlock("span", _hoisted_3, _toDisplayString(updateTime.value), 1)) : _createCommentVNode("", true),
                  _createVNode(_component_VSpacer),
                  _createVNode(_component_VBtn, {
                    size: "small",
                    color: "primary",
                    loading: loading.value,
                    onClick: refreshData
                  }, {
                    default: _withCtx(() => [
                      _createVNode(_component_VIcon, { start: "" }, {
                        default: _withCtx(() => [..._cache[7] || (_cache[7] = [
                          _createTextVNode("mdi-refresh", -1)
                        ])]),
                        _: 1
                      }),
                      _cache[8] || (_cache[8] = _createTextVNode(" 刷新 ", -1))
                    ]),
                    _: 1
                  }, 8, ["loading"]),
                  _createVNode(_component_VBtn, {
                    size: "small",
                    variant: "text",
                    icon: "mdi-close",
                    onClick: closePage
                  })
                ])
              ]),
              _: 1
            })
          ]),
          _: 1
        }),
        loading.value && items.value.length === 0 ? (_openBlock(), _createBlock(_component_VRow, { key: 0 }, {
          default: _withCtx(() => [
            _createVNode(_component_VCol, {
              cols: "12",
              class: "text-center py-8"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_VProgressCircular, {
                  indeterminate: "",
                  color: "primary"
                }),
                _cache[10] || (_cache[10] = _createElementVNode("div", { class: "text-caption text-grey mt-2" }, "正在抓取猫眼热度数据...", -1))
              ]),
              _: 1
            })
          ]),
          _: 1
        })) : items.value.length === 0 ? (_openBlock(), _createBlock(_component_VRow, { key: 1 }, {
          default: _withCtx(() => [
            _createVNode(_component_VCol, {
              cols: "12",
              class: "text-center py-8"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_VAlert, {
                  type: "info",
                  variant: "tonal"
                }, {
                  default: _withCtx(() => [..._cache[11] || (_cache[11] = [
                    _createTextVNode('暂无数据，请点击"刷新"按钮获取', -1)
                  ])]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        })) : (_openBlock(), _createBlock(_component_VRow, { key: 2 }, {
          default: _withCtx(() => [
            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(items.value, (item) => {
              return _openBlock(), _createBlock(_component_VCol, {
                key: item.rank,
                cols: "12",
                md: "4"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VCard, {
                    variant: "outlined",
                    class: "mb-2",
                    rounded: "lg"
                  }, {
                    default: _withCtx(() => [
                      _createVNode(_component_VRow, {
                        "no-gutters": "",
                        align: "center"
                      }, {
                        default: _withCtx(() => [
                          _createVNode(_component_VCol, {
                            cols: "auto",
                            class: "pa-2"
                          }, {
                            default: _withCtx(() => [
                              _createElementVNode("div", _hoisted_4, [
                                _createVNode(_component_VImg, {
                                  src: resolvePoster(item.poster, "card-" + item.rank),
                                  width: "120",
                                  height: "160",
                                  cover: "",
                                  rounded: "sm",
                                  class: _normalizeClass(["bg-grey-lighten-3", { "cursor-pointer": item.tmdbid }]),
                                  onError: ($event) => handlePosterError("card-" + item.rank),
                                  onClick: ($event) => openMediaDetail(item)
                                }, null, 8, ["src", "class", "onError", "onClick"]),
                                _createElementVNode("div", {
                                  style: _normalizeStyle(`position: absolute; bottom: 0; left: 0; right: 0; background: ${getStatusColor(item)}; color: white; font-size: 10px; text-align: center; padding: 2px 0; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px;`)
                                }, _toDisplayString(item.status || "未添加订阅"), 5)
                              ])
                            ]),
                            _: 2
                          }, 1024),
                          _createVNode(_component_VCol, { class: "pa-2" }, {
                            default: _withCtx(() => [
                              _createElementVNode("div", _hoisted_5, [
                                _createVNode(_component_VChip, {
                                  size: "x-small",
                                  color: "primary",
                                  class: "mr-1"
                                }, {
                                  default: _withCtx(() => [
                                    _createTextVNode(_toDisplayString(item.rank), 1)
                                  ]),
                                  _: 2
                                }, 1024),
                                _createElementVNode("span", _hoisted_6, _toDisplayString(item.name), 1)
                              ]),
                              _createElementVNode("div", _hoisted_7, [
                                _createVNode(_component_VIcon, { size: "x-small" }, {
                                  default: _withCtx(() => [..._cache[12] || (_cache[12] = [
                                    _createTextVNode("mdi-television-classic", -1)
                                  ])]),
                                  _: 1
                                }),
                                _createTextVNode(" " + _toDisplayString(item.platform || "未知平台"), 1)
                              ]),
                              _createElementVNode("div", _hoisted_8, [
                                _createVNode(_component_VIcon, { size: "x-small" }, {
                                  default: _withCtx(() => [..._cache[13] || (_cache[13] = [
                                    _createTextVNode("mdi-clock-outline", -1)
                                  ])]),
                                  _: 1
                                }),
                                _createTextVNode(" " + _toDisplayString(item.days || "未知"), 1)
                              ]),
                              _createElementVNode("div", _hoisted_9, [
                                _createVNode(_component_VIcon, { size: "x-small" }, {
                                  default: _withCtx(() => [..._cache[14] || (_cache[14] = [
                                    _createTextVNode("mdi-fire", -1)
                                  ])]),
                                  _: 1
                                }),
                                _createTextVNode(" 热度: " + _toDisplayString(item.heat || 0), 1)
                              ]),
                              _createElementVNode("div", _hoisted_10, [
                                _createVNode(_component_VIcon, { size: "x-small" }, {
                                  default: _withCtx(() => [..._cache[15] || (_cache[15] = [
                                    _createTextVNode("mdi-play-circle-outline", -1)
                                  ])]),
                                  _: 1
                                }),
                                _createTextVNode(" " + _toDisplayString(item.plays || "未知"), 1)
                              ]),
                              item.actors ? (_openBlock(), _createElementBlock("div", _hoisted_11, [
                                _createVNode(_component_VIcon, { size: "x-small" }, {
                                  default: _withCtx(() => [..._cache[16] || (_cache[16] = [
                                    _createTextVNode("mdi-account-group", -1)
                                  ])]),
                                  _: 1
                                }),
                                _createTextVNode(" " + _toDisplayString(Array.isArray(item.actors) ? item.actors.join(" / ") : item.actors), 1)
                              ])) : _createCommentVNode("", true),
                              _createVNode(_component_VBtn, {
                                size: "x-small",
                                class: "mt-1",
                                color: (item.status || "未添加订阅") === "未添加订阅" ? "primary" : "grey",
                                variant: (item.status || "未添加订阅") === "未添加订阅" ? "elevated" : "tonal",
                                loading: isSubscribing(item.tmdbid),
                                disabled: (item.status || "未添加订阅") !== "未添加订阅",
                                onClick: ($event) => subscribe(item)
                              }, {
                                default: _withCtx(() => [
                                  _createTextVNode(_toDisplayString((item.status || "未添加订阅") === "未添加订阅" ? "订阅" : item.status), 1)
                                ]),
                                _: 2
                              }, 1032, ["color", "variant", "loading", "disabled", "onClick"])
                            ]),
                            _: 2
                          }, 1024)
                        ]),
                        _: 2
                      }, 1024)
                    ]),
                    _: 2
                  }, 1024)
                ]),
                _: 2
              }, 1024);
            }), 128))
          ]),
          _: 1
        })),
        _createVNode(_component_VDialog, {
          modelValue: detailOpen.value,
          "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => detailOpen.value = $event),
          "max-width": "1000",
          scrollable: "",
          persistent: ""
        }, {
          default: _withCtx(() => [
            _createVNode(_component_VCard, { class: "media-detail-card" }, {
              default: _withCtx(() => [
                _createVNode(_component_VCardTitle, { class: "d-flex align-center px-4 pt-4 pb-0" }, {
                  default: _withCtx(() => [
                    _createElementVNode("span", _hoisted_12, _toDisplayString((detail.value || selectedItem.value)?.title || selectedItem.value?.name || "媒体详情"), 1),
                    _createVNode(_component_VSpacer),
                    _createVNode(_component_VBtn, {
                      icon: "mdi-close",
                      variant: "text",
                      onClick: closeMediaDetail
                    })
                  ]),
                  _: 1
                }),
                _createVNode(_component_VCardText, { class: "px-4 pb-4" }, {
                  default: _withCtx(() => [
                    detailLoading.value ? (_openBlock(), _createElementBlock("div", _hoisted_13, [
                      _createVNode(_component_VProgressCircular, {
                        indeterminate: "",
                        color: "primary"
                      }),
                      _cache[17] || (_cache[17] = _createElementVNode("div", { class: "text-caption text-grey mt-3" }, "正在加载媒体详情...", -1))
                    ])) : detailError.value ? (_openBlock(), _createBlock(_component_VAlert, {
                      key: 1,
                      type: "error",
                      variant: "tonal",
                      class: "my-4"
                    }, {
                      append: _withCtx(() => [
                        _createVNode(_component_VBtn, {
                          size: "small",
                          variant: "tonal",
                          onClick: retryMediaDetail
                        }, {
                          default: _withCtx(() => [..._cache[18] || (_cache[18] = [
                            _createTextVNode("重试", -1)
                          ])]),
                          _: 1
                        })
                      ]),
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(detailError.value) + " ", 1)
                      ]),
                      _: 1
                    })) : detail.value ? (_openBlock(), _createElementBlock("div", _hoisted_14, [
                      _createElementVNode("div", _hoisted_15, [
                        _createElementVNode("div", _hoisted_16, [
                          _createVNode(_component_VImg, {
                            src: resolvePoster(getW500Image(detail.value.poster_path) || selectedItem.value?.poster, "detail-" + detail.value.tmdb_id),
                            cover: "",
                            class: "object-cover ring-1 ring-gray-500",
                            style: { "aspect-ratio": "2 / 3" },
                            onError: _cache[0] || (_cache[0] = ($event) => handlePosterError("detail-" + detail.value.tmdb_id))
                          }, {
                            placeholder: _withCtx(() => [
                              _createElementVNode("div", _hoisted_17, [
                                _createVNode(_component_VSkeletonLoader, {
                                  class: "object-cover",
                                  style: { "aspect-ratio": "2 / 3" }
                                })
                              ])
                            ]),
                            _: 1
                          }, 8, ["src"])
                        ]),
                        _createElementVNode("div", _hoisted_18, [
                          _createElementVNode("h1", _hoisted_19, [
                            _createElementVNode("span", null, _toDisplayString(detail.value.title || selectedItem.value?.name || "未知名称"), 1),
                            detail.value.year ? (_openBlock(), _createElementBlock("span", _hoisted_20, "（" + _toDisplayString(detail.value.year) + "）", 1)) : _createCommentVNode("", true)
                          ]),
                          _createElementVNode("span", _hoisted_21, [
                            detail.value.runtime || detail.value.episode_run_time?.[0] ? (_openBlock(), _createElementBlock("span", _hoisted_22, _toDisplayString(detail.value.runtime || detail.value.episode_run_time?.[0]) + "分钟 ", 1)) : _createCommentVNode("", true),
                            (detail.value.runtime || detail.value.episode_run_time?.[0]) && detail.value.genres?.length ? (_openBlock(), _createElementBlock("span", _hoisted_23, "|")) : _createCommentVNode("", true),
                            detail.value.genres?.length ? (_openBlock(), _createElementBlock("span", _hoisted_24, _toDisplayString(getGenresName(detail.value.genres)), 1)) : _createCommentVNode("", true)
                          ]),
                          _createElementVNode("div", _hoisted_25, [
                            detail.value.vote_average ? (_openBlock(), _createBlock(_component_VChip, {
                              key: 0,
                              size: "small",
                              color: "amber",
                              variant: "tonal",
                              class: "me-2 mb-1"
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_VIcon, {
                                  start: "",
                                  size: "small"
                                }, {
                                  default: _withCtx(() => [..._cache[19] || (_cache[19] = [
                                    _createTextVNode("mdi-star", -1)
                                  ])]),
                                  _: 1
                                }),
                                _createTextVNode(" " + _toDisplayString(detail.value.vote_average), 1)
                              ]),
                              _: 1
                            })) : _createCommentVNode("", true),
                            detail.value.status ? (_openBlock(), _createBlock(_component_VChip, {
                              key: 1,
                              size: "small",
                              variant: "tonal",
                              class: "me-2 mb-1"
                            }, {
                              default: _withCtx(() => [
                                _createTextVNode(_toDisplayString(detail.value.status), 1)
                              ]),
                              _: 1
                            })) : _createCommentVNode("", true)
                          ]),
                          _createElementVNode("div", _hoisted_26, [
                            _createVNode(_component_VBtn, {
                              size: "small",
                              color: "primary",
                              variant: "tonal",
                              onClick: openSystemMediaDetail
                            }, {
                              default: _withCtx(() => [
                                _createVNode(_component_VIcon, {
                                  start: "",
                                  size: "small"
                                }, {
                                  default: _withCtx(() => [..._cache[20] || (_cache[20] = [
                                    _createTextVNode("mdi-open-in-new", -1)
                                  ])]),
                                  _: 1
                                }),
                                _cache[21] || (_cache[21] = _createTextVNode(" 系统详情 ", -1))
                              ]),
                              _: 1
                            }),
                            selectedItem.value?.tmdbid ? (_openBlock(), _createBlock(_component_VBtn, {
                              key: 0,
                              size: "small",
                              class: "ms-2",
                              color: (selectedItem.value?.status || "未添加订阅") === "未添加订阅" ? "success" : "grey",
                              variant: (selectedItem.value?.status || "未添加订阅") === "未添加订阅" ? "elevated" : "tonal",
                              loading: isSubscribing(selectedItem.value?.tmdbid),
                              disabled: (selectedItem.value?.status || "未添加订阅") !== "未添加订阅",
                              onClick: _cache[1] || (_cache[1] = ($event) => subscribe(selectedItem.value))
                            }, {
                              default: _withCtx(() => [
                                _createTextVNode(_toDisplayString((selectedItem.value?.status || "未添加订阅") === "未添加订阅" ? "订阅" : selectedItem.value?.status), 1)
                              ]),
                              _: 1
                            }, 8, ["color", "variant", "loading", "disabled"])) : _createCommentVNode("", true)
                          ])
                        ])
                      ]),
                      _createElementVNode("div", _hoisted_27, [
                        _createElementVNode("div", _hoisted_28, [
                          detail.value.tagline ? (_openBlock(), _createElementBlock("div", _hoisted_29, _toDisplayString(detail.value.tagline), 1)) : _createCommentVNode("", true),
                          detail.value.overview ? (_openBlock(), _createElementBlock("h2", _hoisted_30, "简介")) : _createCommentVNode("", true),
                          detail.value.overview ? (_openBlock(), _createElementBlock("p", _hoisted_31, _toDisplayString(detail.value.overview), 1)) : (_openBlock(), _createElementBlock("p", _hoisted_32, "暂无简介")),
                          detail.value.directors?.length ? (_openBlock(), _createElementBlock("ul", _hoisted_33, [
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(detail.value.directors, (director) => {
                              return _openBlock(), _createElementBlock("li", {
                                key: director.id
                              }, [
                                _createElementVNode("span", null, _toDisplayString(director.job), 1),
                                _createElementVNode("span", _hoisted_34, _toDisplayString(director.name), 1)
                              ]);
                            }), 128))
                          ])) : _createCommentVNode("", true),
                          detail.value.tmdb_id ? (_openBlock(), _createElementBlock("div", _hoisted_35, [
                            _cache[23] || (_cache[23] = _createElementVNode("h2", { class: "cast-title" }, "演员阵容", -1)),
                            castLoading.value ? (_openBlock(), _createElementBlock("div", _hoisted_36, [
                              _createVNode(_component_VProgressCircular, {
                                indeterminate: "",
                                color: "primary",
                                size: "small"
                              }),
                              _cache[22] || (_cache[22] = _createElementVNode("div", { class: "text-caption text-grey mt-2" }, "加载演员信息...", -1))
                            ])) : cast.value.length ? (_openBlock(), _createElementBlock("div", _hoisted_37, [
                              (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(cast.value, (person) => {
                                return _openBlock(), _createElementBlock("div", {
                                  key: person.id,
                                  class: "cast-card"
                                }, [
                                  _createVNode(_component_VImg, {
                                    src: resolvePoster(getW500Image(person.profile_path), "cast-" + person.id),
                                    cover: "",
                                    class: "cast-photo",
                                    "aspect-ratio": 2 / 3,
                                    loading: "lazy",
                                    onError: ($event) => handlePosterError("cast-" + person.id)
                                  }, null, 8, ["src", "onError"]),
                                  _createElementVNode("div", _hoisted_38, _toDisplayString(person.name), 1),
                                  _createElementVNode("div", _hoisted_39, _toDisplayString(person.character), 1)
                                ]);
                              }), 128))
                            ])) : (_openBlock(), _createElementBlock("div", _hoisted_40, "暂无演员信息"))
                          ])) : _createCommentVNode("", true),
                          _createElementVNode("div", _hoisted_41, [
                            detail.value.tmdb_id ? (_openBlock(), _createElementBlock("a", {
                              key: 0,
                              href: `https://www.themoviedb.org/tv/${detail.value.tmdb_id}`,
                              target: "_blank",
                              class: "me-2"
                            }, [
                              _createElementVNode("div", _hoisted_43, [
                                _createVNode(_component_VIcon, {
                                  icon: "mdi-link",
                                  size: "small"
                                }),
                                _cache[24] || (_cache[24] = _createElementVNode("span", { class: "ms-1" }, "TheMovieDb", -1))
                              ])
                            ], 8, _hoisted_42)) : _createCommentVNode("", true),
                            detail.value.douban_id ? (_openBlock(), _createElementBlock("a", {
                              key: 1,
                              href: `https://movie.douban.com/subject/${detail.value.douban_id}`,
                              target: "_blank",
                              class: "me-2"
                            }, [
                              _createElementVNode("div", _hoisted_45, [
                                _createVNode(_component_VIcon, {
                                  icon: "mdi-link",
                                  size: "small"
                                }),
                                _cache[25] || (_cache[25] = _createElementVNode("span", { class: "ms-1" }, "豆瓣", -1))
                              ])
                            ], 8, _hoisted_44)) : _createCommentVNode("", true),
                            detail.value.imdb_id ? (_openBlock(), _createElementBlock("a", {
                              key: 2,
                              href: `https://www.imdb.com/title/${detail.value.imdb_id}`,
                              target: "_blank",
                              class: "me-2"
                            }, [
                              _createElementVNode("div", _hoisted_47, [
                                _createVNode(_component_VIcon, {
                                  icon: "mdi-link",
                                  size: "small"
                                }),
                                _cache[26] || (_cache[26] = _createElementVNode("span", { class: "ms-1" }, "IMDb", -1))
                              ])
                            ], 8, _hoisted_46)) : _createCommentVNode("", true)
                          ])
                        ]),
                        _createElementVNode("div", _hoisted_48, [
                          _createElementVNode("div", _hoisted_49, [
                            detail.value.vote_average ? (_openBlock(), _createElementBlock("div", _hoisted_50, [
                              _createVNode(_component_VRating, {
                                "model-value": detail.value.vote_average,
                                density: "compact",
                                length: "10",
                                readonly: "",
                                class: "ma-2"
                              }, null, 8, ["model-value"])
                            ])) : _createCommentVNode("", true),
                            detail.value.tmdb_id ? (_openBlock(), _createElementBlock("div", _hoisted_51, [
                              _cache[27] || (_cache[27] = _createElementVNode("span", null, "ID", -1)),
                              _createElementVNode("span", _hoisted_52, _toDisplayString(detail.value.tmdb_id), 1)
                            ])) : _createCommentVNode("", true),
                            detail.value.original_title || detail.value.original_name ? (_openBlock(), _createElementBlock("div", _hoisted_53, [
                              _cache[28] || (_cache[28] = _createElementVNode("span", null, "原始标题", -1)),
                              _createElementVNode("span", _hoisted_54, _toDisplayString(detail.value.original_title || detail.value.original_name), 1)
                            ])) : _createCommentVNode("", true),
                            detail.value.status ? (_openBlock(), _createElementBlock("div", _hoisted_55, [
                              _cache[29] || (_cache[29] = _createElementVNode("span", null, "状态", -1)),
                              _createElementVNode("span", _hoisted_56, _toDisplayString(detail.value.status), 1)
                            ])) : _createCommentVNode("", true),
                            detail.value.release_date || detail.value.first_air_date ? (_openBlock(), _createElementBlock("div", _hoisted_57, [
                              _cache[30] || (_cache[30] = _createElementVNode("span", null, "发布日期", -1)),
                              _createElementVNode("span", _hoisted_58, _toDisplayString(detail.value.release_date || detail.value.first_air_date), 1)
                            ])) : _createCommentVNode("", true)
                          ])
                        ])
                      ])
                    ])) : _createCommentVNode("", true)
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        }, 8, ["modelValue"]),
        _createVNode(_component_VSnackbar, {
          modelValue: snackbarShow.value,
          "onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => snackbarShow.value = $event),
          color: "success",
          timeout: "3000",
          location: "top"
        }, {
          default: _withCtx(() => [
            _createTextVNode(_toDisplayString(snackbarMsg.value), 1)
          ]),
          _: 1
        }, 8, ["modelValue"])
      ]);
    };
  }
});

const HeatList = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-f7b33cb6"]]);

export { HeatList as default };
