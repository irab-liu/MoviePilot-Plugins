import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-pcqpp-6-.js';

const {defineComponent:_defineComponent$1} = await importShared('vue');

const {toDisplayString:_toDisplayString$1,createElementVNode:_createElementVNode$1,resolveComponent:_resolveComponent$1,createVNode:_createVNode$1,withCtx:_withCtx$1,openBlock:_openBlock$1,createElementBlock:_createElementBlock$1,createCommentVNode:_createCommentVNode$1,createTextVNode:_createTextVNode$1,createBlock:_createBlock$1,renderList:_renderList$1,Fragment:_Fragment$1} = await importShared('vue');

const _hoisted_1$1 = { class: "text-h6" };
const _hoisted_2$1 = {
  key: 0,
  class: "text-center py-12"
};
const _hoisted_3$1 = {
  key: 2,
  class: "media-page"
};
const _hoisted_4$1 = { class: "media-header" };
const _hoisted_5$1 = { class: "media-poster" };
const _hoisted_6$1 = { class: "w-full h-full" };
const _hoisted_7$1 = { class: "media-title" };
const _hoisted_8$1 = { class: "d-flex flex-column flex-lg-row align-items-center align-items-lg-baseline" };
const _hoisted_9$1 = {
  key: 0,
  class: "text-lg ms-1"
};
const _hoisted_10$1 = { class: "media-attributes" };
const _hoisted_11$1 = { key: 0 };
const _hoisted_12$1 = {
  key: 1,
  class: "mx-1"
};
const _hoisted_13 = { key: 2 };
const _hoisted_14 = { class: "mt-2" };
const _hoisted_15 = { class: "media-actions" };
const _hoisted_16 = { class: "media-overview" };
const _hoisted_17 = { class: "media-overview-left" };
const _hoisted_18 = {
  key: 0,
  class: "tagline"
};
const _hoisted_19 = {
  key: 1,
  class: "mt-3"
};
const _hoisted_20 = { key: 2 };
const _hoisted_21 = {
  key: 3,
  class: "text-grey text-body-2"
};
const _hoisted_22 = {
  key: 4,
  class: "media-crew mt-4"
};
const _hoisted_23 = { class: "crew-name" };
const _hoisted_24 = {
  key: 5,
  class: "cast-section mt-6"
};
const _hoisted_25 = {
  key: 0,
  class: "text-center py-4"
};
const _hoisted_26 = {
  key: 1,
  class: "cast-list"
};
const _hoisted_27 = { class: "cast-name" };
const _hoisted_28 = { class: "cast-character" };
const _hoisted_29 = {
  key: 2,
  class: "text-grey text-body-2"
};
const _hoisted_30 = { class: "mt-4" };
const _hoisted_31 = ["href"];
const _hoisted_32 = { class: "inline-flex cursor-pointer items-center rounded-full bg-gray-600 px-2 py-1 text-sm text-gray-200 ring-1 ring-gray-500 hover:bg-gray-700" };
const _hoisted_33 = ["href"];
const _hoisted_34 = { class: "inline-flex cursor-pointer items-center rounded-full bg-gray-600 px-2 py-1 text-sm text-gray-200 ring-1 ring-gray-500 hover:bg-gray-700" };
const _hoisted_35 = ["href"];
const _hoisted_36 = { class: "inline-flex cursor-pointer items-center rounded-full bg-gray-600 px-2 py-1 text-sm text-gray-200 ring-1 ring-gray-500 hover:bg-gray-700" };
const _hoisted_37 = { class: "media-overview-right" };
const _hoisted_38 = { class: "media-facts" };
const _hoisted_39 = {
  key: 0,
  class: "media-ratings"
};
const _hoisted_40 = {
  key: 1,
  class: "media-fact"
};
const _hoisted_41 = { class: "media-fact-value" };
const _hoisted_42 = {
  key: 2,
  class: "media-fact"
};
const _hoisted_43 = { class: "media-fact-value" };
const _hoisted_44 = {
  key: 3,
  class: "media-fact"
};
const _hoisted_45 = { class: "media-fact-value" };
const _hoisted_46 = {
  key: 4,
  class: "media-fact"
};
const _hoisted_47 = { class: "media-fact-value" };
const _hoisted_48 = {
  key: 5,
  class: "media-fact"
};
const _hoisted_49 = { class: "media-fact-value" };
const _hoisted_50 = {
  key: 6,
  class: "media-fact"
};
const _hoisted_51 = { class: "media-fact-value" };
const {computed: computed$1,ref: ref$1} = await importShared('vue');

const POSTER_PLACEHOLDER$1 = "data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22500%22%20height%3D%22750%22%20viewBox%3D%220%200%20500%20750%22%3E%3Crect%20width%3D%22500%22%20height%3D%22750%22%20fill%3D%22%231e1e2e%22%2F%3E%3Crect%20x%3D%22180%22%20y%3D%22270%22%20width%3D%22140%22%20height%3D%22110%22%20rx%3D%2210%22%20fill%3D%22none%22%20stroke%3D%22%23444%22%20stroke-width%3D%223%22%2F%3E%3Ccircle%20cx%3D%22210%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22250%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22290%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22210%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22250%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22290%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ctext%20x%3D%22250%22%20y%3D%22440%22%20text-anchor%3D%22middle%22%20fill%3D%22%23555%22%20font-size%3D%2228%22%20font-family%3D%22system-ui%2Csans-serif%22%3E%E6%9A%82%E6%97%A0%E6%B5%B7%E6%8A%A5%3C%2Ftext%3E%3C%2Fsvg%3E";
const _sfc_main$1 = /* @__PURE__ */ _defineComponent$1({
  __name: "MediaDetailDialog",
  props: {
    modelValue: { type: Boolean },
    detail: {},
    loading: { type: Boolean },
    error: {},
    selectedItem: {},
    cast: {},
    castLoading: { type: Boolean },
    subscribingIds: {},
    imageDomain: {}
  },
  emits: ["update:modelValue", "close", "retry", "system-detail", "subscribe"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const emit = __emit;
    const title = computed$1(
      () => props.detail?.title || props.selectedItem?.name || "媒体详情"
    );
    const failedPosters = ref$1(/* @__PURE__ */ new Set());
    function onModelUpdate(value) {
      emit("update:modelValue", value);
      if (!value) emit("close");
    }
    function onClose() {
      emit("update:modelValue", false);
      emit("close");
    }
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
      if (!poster || failedPosters.value.has(key)) return POSTER_PLACEHOLDER$1;
      return toProxyUrl(poster);
    }
    function getW500Image(posterPath) {
      if (!posterPath) return "";
      const base = posterPath.startsWith("http") ? "" : `https://${props.imageDomain}/t/p/w500`;
      return `${base}${posterPath}`;
    }
    function getGenresName(genres) {
      if (!Array.isArray(genres)) return "";
      return genres.map((genre) => typeof genre === "string" ? genre : genre.name).join("、");
    }
    function isSubscribing(tmdbid) {
      if (!tmdbid) return false;
      return props.subscribingIds.includes(tmdbid);
    }
    return (_ctx, _cache) => {
      const _component_VSpacer = _resolveComponent$1("VSpacer");
      const _component_VBtn = _resolveComponent$1("VBtn");
      const _component_VCardTitle = _resolveComponent$1("VCardTitle");
      const _component_VProgressCircular = _resolveComponent$1("VProgressCircular");
      const _component_VAlert = _resolveComponent$1("VAlert");
      const _component_VSkeletonLoader = _resolveComponent$1("VSkeletonLoader");
      const _component_VImg = _resolveComponent$1("VImg");
      const _component_VChip = _resolveComponent$1("VChip");
      const _component_VIcon = _resolveComponent$1("VIcon");
      const _component_VRating = _resolveComponent$1("VRating");
      const _component_VCardText = _resolveComponent$1("VCardText");
      const _component_VCard = _resolveComponent$1("VCard");
      const _component_VDialog = _resolveComponent$1("VDialog");
      return _openBlock$1(), _createBlock$1(_component_VDialog, {
        "model-value": __props.modelValue,
        "max-width": "1000",
        scrollable: "",
        "onUpdate:modelValue": onModelUpdate
      }, {
        default: _withCtx$1(() => [
          _createVNode$1(_component_VCard, { class: "media-detail-card" }, {
            default: _withCtx$1(() => [
              _createVNode$1(_component_VCardTitle, { class: "d-flex align-center px-4 pt-4 pb-0" }, {
                default: _withCtx$1(() => [
                  _createElementVNode$1("span", _hoisted_1$1, _toDisplayString$1(title.value), 1),
                  _createVNode$1(_component_VSpacer),
                  _createVNode$1(_component_VBtn, {
                    icon: "mdi-close",
                    variant: "text",
                    "data-native-dialog-close": "",
                    onClick: onClose
                  })
                ]),
                _: 1
              }),
              _createVNode$1(_component_VCardText, { class: "px-4 pb-4" }, {
                default: _withCtx$1(() => [
                  __props.loading ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_2$1, [
                    _createVNode$1(_component_VProgressCircular, {
                      indeterminate: "",
                      color: "primary"
                    }),
                    _cache[4] || (_cache[4] = _createElementVNode$1("div", { class: "text-caption text-grey mt-3" }, "正在加载媒体详情...", -1))
                  ])) : __props.error ? (_openBlock$1(), _createBlock$1(_component_VAlert, {
                    key: 1,
                    type: "error",
                    variant: "tonal",
                    class: "my-4"
                  }, {
                    append: _withCtx$1(() => [
                      _createVNode$1(_component_VBtn, {
                        size: "small",
                        variant: "tonal",
                        onClick: _cache[0] || (_cache[0] = ($event) => _ctx.$emit("retry"))
                      }, {
                        default: _withCtx$1(() => [..._cache[5] || (_cache[5] = [
                          _createTextVNode$1("重试", -1)
                        ])]),
                        _: 1
                      })
                    ]),
                    default: _withCtx$1(() => [
                      _createTextVNode$1(_toDisplayString$1(__props.error) + " ", 1)
                    ]),
                    _: 1
                  })) : __props.detail ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_3$1, [
                    _createElementVNode$1("div", _hoisted_4$1, [
                      _createElementVNode$1("div", _hoisted_5$1, [
                        _createVNode$1(_component_VImg, {
                          src: resolvePoster(getW500Image(__props.detail.poster_path) || __props.selectedItem?.poster, "detail-" + __props.detail.tmdb_id),
                          cover: "",
                          class: "object-cover ring-1 ring-gray-500",
                          style: { "aspect-ratio": "2 / 3" },
                          onError: _cache[1] || (_cache[1] = ($event) => handlePosterError("detail-" + __props.detail.tmdb_id))
                        }, {
                          placeholder: _withCtx$1(() => [
                            _createElementVNode$1("div", _hoisted_6$1, [
                              _createVNode$1(_component_VSkeletonLoader, {
                                class: "object-cover",
                                style: { "aspect-ratio": "2 / 3" }
                              })
                            ])
                          ]),
                          _: 1
                        }, 8, ["src"])
                      ]),
                      _createElementVNode$1("div", _hoisted_7$1, [
                        _createElementVNode$1("h1", _hoisted_8$1, [
                          _createElementVNode$1("span", null, _toDisplayString$1(__props.detail.title || __props.selectedItem?.name || "未知名称"), 1),
                          __props.detail.year ? (_openBlock$1(), _createElementBlock$1("span", _hoisted_9$1, "（" + _toDisplayString$1(__props.detail.year) + "）", 1)) : _createCommentVNode$1("", true),
                          __props.detail.season_number ? (_openBlock$1(), _createBlock$1(_component_VChip, {
                            key: 1,
                            size: "small",
                            color: "primary",
                            variant: "tonal",
                            class: "ms-2"
                          }, {
                            default: _withCtx$1(() => [
                              _createTextVNode$1("第 " + _toDisplayString$1(__props.detail.season_number) + " 季", 1)
                            ]),
                            _: 1
                          })) : _createCommentVNode$1("", true)
                        ]),
                        _createElementVNode$1("span", _hoisted_10$1, [
                          __props.detail.runtime || __props.detail.episode_run_time?.[0] ? (_openBlock$1(), _createElementBlock$1("span", _hoisted_11$1, _toDisplayString$1(__props.detail.runtime || __props.detail.episode_run_time?.[0]) + "分钟 ", 1)) : _createCommentVNode$1("", true),
                          (__props.detail.runtime || __props.detail.episode_run_time?.[0]) && __props.detail.genres?.length ? (_openBlock$1(), _createElementBlock$1("span", _hoisted_12$1, "|")) : _createCommentVNode$1("", true),
                          __props.detail.genres?.length ? (_openBlock$1(), _createElementBlock$1("span", _hoisted_13, _toDisplayString$1(getGenresName(__props.detail.genres)), 1)) : _createCommentVNode$1("", true)
                        ]),
                        _createElementVNode$1("div", _hoisted_14, [
                          __props.detail.vote_average ? (_openBlock$1(), _createBlock$1(_component_VChip, {
                            key: 0,
                            size: "small",
                            color: "amber",
                            variant: "tonal",
                            class: "me-2 mb-1"
                          }, {
                            default: _withCtx$1(() => [
                              _createVNode$1(_component_VIcon, {
                                start: "",
                                size: "small"
                              }, {
                                default: _withCtx$1(() => [..._cache[6] || (_cache[6] = [
                                  _createTextVNode$1("mdi-star", -1)
                                ])]),
                                _: 1
                              }),
                              _createTextVNode$1(" " + _toDisplayString$1(__props.detail.vote_average), 1)
                            ]),
                            _: 1
                          })) : _createCommentVNode$1("", true),
                          __props.detail.status ? (_openBlock$1(), _createBlock$1(_component_VChip, {
                            key: 1,
                            size: "small",
                            variant: "tonal",
                            class: "me-2 mb-1"
                          }, {
                            default: _withCtx$1(() => [
                              _createTextVNode$1(_toDisplayString$1(__props.detail.status), 1)
                            ]),
                            _: 1
                          })) : _createCommentVNode$1("", true)
                        ]),
                        _createElementVNode$1("div", _hoisted_15, [
                          _createVNode$1(_component_VBtn, {
                            size: "small",
                            color: "primary",
                            variant: "tonal",
                            onClick: _cache[2] || (_cache[2] = ($event) => _ctx.$emit("system-detail"))
                          }, {
                            default: _withCtx$1(() => [
                              _createVNode$1(_component_VIcon, {
                                start: "",
                                size: "small"
                              }, {
                                default: _withCtx$1(() => [..._cache[7] || (_cache[7] = [
                                  _createTextVNode$1("mdi-open-in-new", -1)
                                ])]),
                                _: 1
                              }),
                              _cache[8] || (_cache[8] = _createTextVNode$1(" 系统详情 ", -1))
                            ]),
                            _: 1
                          }),
                          __props.selectedItem?.tmdbid ? (_openBlock$1(), _createBlock$1(_component_VBtn, {
                            key: 0,
                            size: "small",
                            class: "ms-2",
                            color: (__props.selectedItem?.status || "未添加订阅") === "未添加订阅" ? "success" : "grey",
                            variant: (__props.selectedItem?.status || "未添加订阅") === "未添加订阅" ? "elevated" : "tonal",
                            loading: isSubscribing(__props.selectedItem?.tmdbid),
                            disabled: (__props.selectedItem?.status || "未添加订阅") !== "未添加订阅",
                            onClick: _cache[3] || (_cache[3] = ($event) => _ctx.$emit("subscribe"))
                          }, {
                            default: _withCtx$1(() => [
                              _createTextVNode$1(_toDisplayString$1((__props.selectedItem?.status || "未添加订阅") === "未添加订阅" ? "订阅" : __props.selectedItem?.status), 1)
                            ]),
                            _: 1
                          }, 8, ["color", "variant", "loading", "disabled"])) : _createCommentVNode$1("", true)
                        ])
                      ])
                    ]),
                    _createElementVNode$1("div", _hoisted_16, [
                      _createElementVNode$1("div", _hoisted_17, [
                        __props.detail.tagline ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_18, _toDisplayString$1(__props.detail.tagline), 1)) : _createCommentVNode$1("", true),
                        __props.detail.overview ? (_openBlock$1(), _createElementBlock$1("h2", _hoisted_19, "简介")) : _createCommentVNode$1("", true),
                        __props.detail.overview ? (_openBlock$1(), _createElementBlock$1("p", _hoisted_20, _toDisplayString$1(__props.detail.overview), 1)) : (_openBlock$1(), _createElementBlock$1("p", _hoisted_21, "暂无简介")),
                        __props.detail.directors?.length ? (_openBlock$1(), _createElementBlock$1("ul", _hoisted_22, [
                          (_openBlock$1(true), _createElementBlock$1(_Fragment$1, null, _renderList$1(__props.detail.directors, (director) => {
                            return _openBlock$1(), _createElementBlock$1("li", {
                              key: director.id
                            }, [
                              _createElementVNode$1("span", null, _toDisplayString$1(director.job), 1),
                              _createElementVNode$1("span", _hoisted_23, _toDisplayString$1(director.name), 1)
                            ]);
                          }), 128))
                        ])) : _createCommentVNode$1("", true),
                        __props.detail.tmdb_id ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_24, [
                          _cache[10] || (_cache[10] = _createElementVNode$1("h2", { class: "cast-title" }, "演员阵容", -1)),
                          __props.castLoading ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_25, [
                            _createVNode$1(_component_VProgressCircular, {
                              indeterminate: "",
                              color: "primary",
                              size: "small"
                            }),
                            _cache[9] || (_cache[9] = _createElementVNode$1("div", { class: "text-caption text-grey mt-2" }, "加载演员信息...", -1))
                          ])) : __props.cast.length ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_26, [
                            (_openBlock$1(true), _createElementBlock$1(_Fragment$1, null, _renderList$1(__props.cast, (person) => {
                              return _openBlock$1(), _createElementBlock$1("div", {
                                key: person.id,
                                class: "cast-card"
                              }, [
                                _createVNode$1(_component_VImg, {
                                  src: resolvePoster(getW500Image(person.profile_path), "cast-" + person.id),
                                  cover: "",
                                  class: "cast-photo",
                                  "aspect-ratio": 2 / 3,
                                  loading: "lazy",
                                  onError: ($event) => handlePosterError("cast-" + person.id)
                                }, null, 8, ["src", "onError"]),
                                _createElementVNode$1("div", _hoisted_27, _toDisplayString$1(person.name), 1),
                                _createElementVNode$1("div", _hoisted_28, _toDisplayString$1(person.character), 1)
                              ]);
                            }), 128))
                          ])) : (_openBlock$1(), _createElementBlock$1("div", _hoisted_29, "暂无演员信息"))
                        ])) : _createCommentVNode$1("", true),
                        _createElementVNode$1("div", _hoisted_30, [
                          __props.detail.tmdb_id ? (_openBlock$1(), _createElementBlock$1("a", {
                            key: 0,
                            href: `https://www.themoviedb.org/tv/${__props.detail.tmdb_id}`,
                            target: "_blank",
                            class: "me-2"
                          }, [
                            _createElementVNode$1("div", _hoisted_32, [
                              _createVNode$1(_component_VIcon, {
                                icon: "mdi-link",
                                size: "small"
                              }),
                              _cache[11] || (_cache[11] = _createElementVNode$1("span", { class: "ms-1" }, "TheMovieDb", -1))
                            ])
                          ], 8, _hoisted_31)) : _createCommentVNode$1("", true),
                          __props.detail.douban_id ? (_openBlock$1(), _createElementBlock$1("a", {
                            key: 1,
                            href: `https://movie.douban.com/subject/${__props.detail.douban_id}`,
                            target: "_blank",
                            class: "me-2"
                          }, [
                            _createElementVNode$1("div", _hoisted_34, [
                              _createVNode$1(_component_VIcon, {
                                icon: "mdi-link",
                                size: "small"
                              }),
                              _cache[12] || (_cache[12] = _createElementVNode$1("span", { class: "ms-1" }, "豆瓣", -1))
                            ])
                          ], 8, _hoisted_33)) : _createCommentVNode$1("", true),
                          __props.detail.imdb_id ? (_openBlock$1(), _createElementBlock$1("a", {
                            key: 2,
                            href: `https://www.imdb.com/title/${__props.detail.imdb_id}`,
                            target: "_blank",
                            class: "me-2"
                          }, [
                            _createElementVNode$1("div", _hoisted_36, [
                              _createVNode$1(_component_VIcon, {
                                icon: "mdi-link",
                                size: "small"
                              }),
                              _cache[13] || (_cache[13] = _createElementVNode$1("span", { class: "ms-1" }, "IMDb", -1))
                            ])
                          ], 8, _hoisted_35)) : _createCommentVNode$1("", true)
                        ])
                      ]),
                      _createElementVNode$1("div", _hoisted_37, [
                        _createElementVNode$1("div", _hoisted_38, [
                          __props.detail.vote_average ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_39, [
                            _createVNode$1(_component_VRating, {
                              "model-value": __props.detail.vote_average,
                              density: "compact",
                              length: "10",
                              readonly: "",
                              class: "ma-2"
                            }, null, 8, ["model-value"])
                          ])) : _createCommentVNode$1("", true),
                          __props.detail.tmdb_id ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_40, [
                            _cache[14] || (_cache[14] = _createElementVNode$1("span", null, "ID", -1)),
                            _createElementVNode$1("span", _hoisted_41, _toDisplayString$1(__props.detail.tmdb_id), 1)
                          ])) : _createCommentVNode$1("", true),
                          __props.detail.original_title || __props.detail.original_name ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_42, [
                            _cache[15] || (_cache[15] = _createElementVNode$1("span", null, "原始标题", -1)),
                            _createElementVNode$1("span", _hoisted_43, _toDisplayString$1(__props.detail.original_title || __props.detail.original_name), 1)
                          ])) : _createCommentVNode$1("", true),
                          __props.detail.status ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_44, [
                            _cache[16] || (_cache[16] = _createElementVNode$1("span", null, "状态", -1)),
                            _createElementVNode$1("span", _hoisted_45, _toDisplayString$1(__props.detail.status), 1)
                          ])) : _createCommentVNode$1("", true),
                          __props.detail.release_date || __props.detail.first_air_date ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_46, [
                            _createElementVNode$1("span", null, _toDisplayString$1(__props.detail.season_number ? "本季首播" : "发布日期"), 1),
                            _createElementVNode$1("span", _hoisted_47, _toDisplayString$1(__props.detail.season_number ? __props.detail.first_air_date || __props.detail.release_date : __props.detail.release_date || __props.detail.first_air_date), 1)
                          ])) : _createCommentVNode$1("", true),
                          __props.detail.season_number && __props.detail.number_of_episodes ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_48, [
                            _cache[17] || (_cache[17] = _createElementVNode$1("span", null, "集数", -1)),
                            _createElementVNode$1("span", _hoisted_49, "第 " + _toDisplayString$1(__props.detail.season_number) + " 季 共 " + _toDisplayString$1(__props.detail.number_of_episodes) + " 集", 1)
                          ])) : __props.detail.number_of_episodes ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_50, [
                            _cache[18] || (_cache[18] = _createElementVNode$1("span", null, "集数", -1)),
                            _createElementVNode$1("span", _hoisted_51, _toDisplayString$1(__props.detail.number_of_episodes) + " 集", 1)
                          ])) : _createCommentVNode$1("", true)
                        ])
                      ])
                    ])
                  ])) : _createCommentVNode$1("", true)
                ]),
                _: 1
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      }, 8, ["model-value"]);
    };
  }
});

const MediaDetailDialog = /* @__PURE__ */ _export_sfc(_sfc_main$1, [["__scopeId", "data-v-6e90af55"]]);

const {defineComponent:_defineComponent} = await importShared('vue');

const {createTextVNode:_createTextVNode,resolveComponent:_resolveComponent,withCtx:_withCtx,createVNode:_createVNode,createElementVNode:_createElementVNode,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,toDisplayString:_toDisplayString,createElementBlock:_createElementBlock,renderList:_renderList,Fragment:_Fragment,normalizeClass:_normalizeClass,normalizeStyle:_normalizeStyle} = await importShared('vue');

const _hoisted_1 = { class: "maoyan-heat-list" };
const _hoisted_2 = { class: "d-flex align-center mb-4 flex-wrap gap-2" };
const _hoisted_3 = {
  key: 1,
  class: "text-caption text-grey ml-1"
};
const _hoisted_4 = {
  key: 2,
  class: "maoyan-cards-grid"
};
const _hoisted_5 = { style: { "position": "relative" } };
const _hoisted_6 = { class: "d-flex align-center mb-1" };
const _hoisted_7 = { style: { "font-size": "14px", "font-weight": "bold", "line-height": "1.3" } };
const _hoisted_8 = {
  class: "text-grey mb-1",
  style: { "font-size": "12px" }
};
const _hoisted_9 = {
  class: "text-grey mb-1",
  style: { "font-size": "12px" }
};
const _hoisted_10 = {
  class: "text-grey mb-1",
  style: { "font-size": "12px" }
};
const _hoisted_11 = {
  class: "text-grey mb-1",
  style: { "font-size": "12px" }
};
const _hoisted_12 = {
  key: 0,
  class: "text-grey mb-1",
  style: { "font-size": "12px" }
};
const {computed,onMounted,ref} = await importShared('vue');
const componentTag = "[MaoyanDianYing/Page]";
const POSTER_PLACEHOLDER = "data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22500%22%20height%3D%22750%22%20viewBox%3D%220%200%20500%20750%22%3E%3Crect%20width%3D%22500%22%20height%3D%22750%22%20fill%3D%22%231e1e2e%22%2F%3E%3Crect%20x%3D%22180%22%20y%3D%22270%22%20width%3D%22140%22%20height%3D%22110%22%20rx%3D%2210%22%20fill%3D%22none%22%20stroke%3D%22%23444%22%20stroke-width%3D%223%22%2F%3E%3Ccircle%20cx%3D%22210%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22250%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22290%22%20cy%3D%22300%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22210%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22250%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ccircle%20cx%3D%22290%22%20cy%3D%22350%22%20r%3D%228%22%20fill%3D%22%23444%22%2F%3E%3Ctext%20x%3D%22250%22%20y%3D%22440%22%20text-anchor%3D%22middle%22%20fill%3D%22%23555%22%20font-size%3D%2228%22%20font-family%3D%22system-ui%2Csans-serif%22%3E%E6%9A%82%E6%97%A0%E6%B5%B7%E6%8A%A5%3C%2Ftext%3E%3C%2Fsvg%3E";
const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "HeatList",
  props: {
    api: {},
    pluginId: {},
    hostSdk: {}
  },
  emits: ["close"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const emit = __emit;
    const items = ref([]);
    const loading = ref(false);
    const fromCache = ref(false);
    const updateTime = ref("");
    const imageDomain = ref("image.tmdb.org");
    const detailOpenLocal = ref(false);
    const detailController = ref(null);
    const hostDialogAvailable = computed(() => Boolean(props.hostSdk?.ui?.dialog));
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
    async function loadCache() {
      const url = buildPluginUrl("get-cache");
      try {
        const result = await props.api?.get(url);
        if (result?.enabled === false) {
          items.value = [];
          fromCache.value = false;
          return "disabled";
        }
        if (typeof result?.image_domain === "string" && result.image_domain) {
          imageDomain.value = result.image_domain;
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
      syncDetailDialog();
      try {
        const result = await props.api.post(url, {
          tmdbid: item.tmdbid,
          name: item.name,
          season: item.season || 0
        });
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
      syncDetailDialog();
      await loadCache();
      if (selectedItem.value?.tmdbid) {
        const updated = items.value.find((row) => row.tmdbid === selectedItem.value?.tmdbid);
        if (updated) {
          selectedItem.value = { ...selectedItem.value, status: updated.status };
        }
      }
      syncDetailDialog();
    }
    function detailSnapshot() {
      return {
        detail: detail.value,
        loading: detailLoading.value,
        error: detailError.value,
        selectedItem: selectedItem.value,
        cast: cast.value,
        castLoading: castLoading.value,
        subscribingIds: Array.from(subscribing.value),
        imageDomain: imageDomain.value
      };
    }
    function syncDetailDialog() {
      detailController.value?.updateProps(detailSnapshot());
    }
    function showDetailDialog() {
      if (hostDialogAvailable.value) {
        if (detailController.value) {
          syncDetailDialog();
          return;
        }
        detailController.value = props.hostSdk.ui.dialog(
          MediaDetailDialog,
          detailSnapshot(),
          {
            close: handleDetailClosedByDialog,
            retry: retryMediaDetail,
            "system-detail": openSystemMediaDetail,
            subscribe: handleDetailSubscribe
          },
          { closeOn: ["close"] }
        );
        return;
      }
      detailOpenLocal.value = true;
    }
    function closeDetailDialog() {
      detailController.value?.close();
      detailController.value = null;
      detailOpenLocal.value = false;
      resetDetailState();
    }
    function handleDetailClosedByDialog() {
      detailController.value = null;
      detailOpenLocal.value = false;
      resetDetailState();
    }
    function resetDetailState() {
      detailLoading.value = false;
      detailError.value = "";
      detail.value = null;
      selectedItem.value = null;
      cast.value = [];
      castLoading.value = false;
    }
    function handleDetailSubscribe() {
      if (selectedItem.value) void subscribe(selectedItem.value);
    }
    async function openMediaDetail(item) {
      if (!item.tmdbid) return;
      selectedItem.value = item;
      detailLoading.value = true;
      detailError.value = "";
      detail.value = null;
      cast.value = [];
      castLoading.value = false;
      showDetailDialog();
      syncDetailDialog();
      const url = `media/${encodeURIComponent(String(item.tmdbid))}`;
      try {
        const result = await props.api?.get(url, { params: { media_source: "themoviedb", type_name: "电视剧" } });
        if (result?.data && typeof result.data === "object" && !Array.isArray(result.data)) {
          detail.value = result.data;
        } else if (result && typeof result === "object") {
          detail.value = result;
        }
        syncDetailDialog();
        const seasonCastReady = item.season ? await applySeasonDetail(item) : false;
        if (detail.value?.tmdb_id && !seasonCastReady) {
          await fetchCast(detail.value.tmdb_id);
        }
      } catch (error) {
        detailError.value = error?.message || "媒体详情加载失败";
        syncDetailDialog();
      } finally {
        detailLoading.value = false;
        syncDetailDialog();
      }
    }
    async function applySeasonDetail(item) {
      if (!item.season || !detail.value) return false;
      try {
        const url = buildPluginUrl("get-season");
        const result = await props.api?.get(url, { params: { tmdbid: item.tmdbid, season: item.season } });
        const seasonData = result?.data;
        if (!seasonData) return false;
        if (seasonData.overview) detail.value.overview = seasonData.overview;
        if (seasonData.air_date) detail.value.first_air_date = seasonData.air_date;
        if (seasonData.poster_path) detail.value.poster_path = seasonData.poster_path;
        if (seasonData.vote_average) detail.value.vote_average = seasonData.vote_average;
        if (seasonData.episode_count) detail.value.number_of_episodes = seasonData.episode_count;
        detail.value.season_number = seasonData.season_number;
        if (seasonData.cast?.length) {
          cast.value = seasonData.cast;
          syncDetailDialog();
          return true;
        }
        syncDetailDialog();
      } catch (e) {
        console.warn(componentTag, "季详情加载失败", e);
      }
      return false;
    }
    async function fetchCast(tmdbId) {
      castLoading.value = true;
      cast.value = [];
      syncDetailDialog();
      try {
        const url = buildPluginUrl("get-cast");
        const result = await props.api?.get(url, { params: { tmdbid: tmdbId } });
        cast.value = result?.data || [];
      } catch (e) {
        console.warn(componentTag, "演员阵容加载失败", e);
      } finally {
        castLoading.value = false;
        syncDetailDialog();
      }
    }
    function retryMediaDetail() {
      if (selectedItem.value) void openMediaDetail(selectedItem.value);
    }
    function closePage() {
      if (detailController.value || detailOpenLocal.value) {
        closeDetailDialog();
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
                    default: _withCtx(() => [..._cache[2] || (_cache[2] = [
                      _createTextVNode("mdi-fire", -1)
                    ])]),
                    _: 1
                  }),
                  _cache[7] || (_cache[7] = _createElementVNode("span", { class: "text-h6 font-weight-bold" }, "猫眼发现", -1)),
                  _createVNode(_component_VChip, {
                    size: "small",
                    color: "error",
                    class: "ml-1"
                  }, {
                    default: _withCtx(() => [..._cache[3] || (_cache[3] = [
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
                    default: _withCtx(() => [..._cache[4] || (_cache[4] = [
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
                        default: _withCtx(() => [..._cache[5] || (_cache[5] = [
                          _createTextVNode("mdi-refresh", -1)
                        ])]),
                        _: 1
                      }),
                      _cache[6] || (_cache[6] = _createTextVNode(" 刷新 ", -1))
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
                _cache[8] || (_cache[8] = _createElementVNode("div", { class: "text-caption text-grey mt-2" }, "正在抓取猫眼发现数据...", -1))
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
                  default: _withCtx(() => [..._cache[9] || (_cache[9] = [
                    _createTextVNode('暂无数据，请点击"刷新"按钮获取', -1)
                  ])]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        })) : (_openBlock(), _createElementBlock("div", _hoisted_4, [
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(items.value, (item) => {
            return _openBlock(), _createElementBlock("div", {
              key: item.rank,
              class: "maoyan-card-wrapper"
            }, [
              _createVNode(_component_VCard, {
                variant: "outlined",
                rounded: "lg",
                class: "h-100"
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
                          _createElementVNode("div", _hoisted_5, [
                            _createVNode(_component_VImg, {
                              src: resolvePoster(item.poster, "card-" + item.rank),
                              width: "133",
                              height: "200",
                              cover: "",
                              rounded: "sm",
                              class: _normalizeClass(["bg-grey-lighten-3", { "cursor-pointer": item.tmdbid }]),
                              onError: ($event) => handlePosterError("card-" + item.rank),
                              onClick: ($event) => openMediaDetail(item)
                            }, null, 8, ["src", "class", "onError", "onClick"]),
                            _createElementVNode("div", {
                              style: _normalizeStyle(`position: absolute; bottom: 0; left: 0; right: 0; background: ${getStatusColor(item)}; color: white; font-size: 12px; text-align: center; padding: 3px 0; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px;`)
                            }, _toDisplayString(item.status || "未添加订阅"), 5)
                          ])
                        ]),
                        _: 2
                      }, 1024),
                      _createVNode(_component_VCol, {
                        class: "pa-2 d-flex flex-column justify-space-between",
                        style: { "min-height": "200px" }
                      }, {
                        default: _withCtx(() => [
                          _createElementVNode("div", null, [
                            _createElementVNode("div", _hoisted_6, [
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
                              _createElementVNode("span", _hoisted_7, _toDisplayString(item.name), 1)
                            ]),
                            _createElementVNode("div", _hoisted_8, [
                              _createVNode(_component_VIcon, {
                                size: "small",
                                class: "mr-1"
                              }, {
                                default: _withCtx(() => [..._cache[10] || (_cache[10] = [
                                  _createTextVNode("mdi-television-classic", -1)
                                ])]),
                                _: 1
                              }),
                              _createTextVNode(" " + _toDisplayString(item.platform || "未知平台"), 1)
                            ]),
                            _createElementVNode("div", _hoisted_9, [
                              _createVNode(_component_VIcon, {
                                size: "small",
                                class: "mr-1"
                              }, {
                                default: _withCtx(() => [..._cache[11] || (_cache[11] = [
                                  _createTextVNode("mdi-clock-outline", -1)
                                ])]),
                                _: 1
                              }),
                              _createTextVNode(" " + _toDisplayString(item.days || "未知"), 1)
                            ]),
                            _createElementVNode("div", _hoisted_10, [
                              _createVNode(_component_VIcon, {
                                size: "small",
                                color: "error",
                                class: "mr-1"
                              }, {
                                default: _withCtx(() => [..._cache[12] || (_cache[12] = [
                                  _createTextVNode("mdi-fire", -1)
                                ])]),
                                _: 1
                              }),
                              _createTextVNode(" 热度: " + _toDisplayString(item.heat || 0), 1)
                            ]),
                            _createElementVNode("div", _hoisted_11, [
                              _createVNode(_component_VIcon, {
                                size: "small",
                                class: "mr-1"
                              }, {
                                default: _withCtx(() => [..._cache[13] || (_cache[13] = [
                                  _createTextVNode("mdi-play-circle-outline", -1)
                                ])]),
                                _: 1
                              }),
                              _createTextVNode(" " + _toDisplayString(item.plays || "未知"), 1)
                            ]),
                            item.actors ? (_openBlock(), _createElementBlock("div", _hoisted_12, [
                              _createVNode(_component_VIcon, {
                                size: "small",
                                class: "mr-1"
                              }, {
                                default: _withCtx(() => [..._cache[14] || (_cache[14] = [
                                  _createTextVNode("mdi-account-group", -1)
                                ])]),
                                _: 1
                              }),
                              _createTextVNode(" " + _toDisplayString(Array.isArray(item.actors) ? item.actors.join(" / ") : item.actors), 1)
                            ])) : _createCommentVNode("", true)
                          ]),
                          _createElementVNode("div", null, [
                            _createVNode(_component_VBtn, {
                              size: "small",
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
                          ])
                        ]),
                        _: 2
                      }, 1024)
                    ]),
                    _: 2
                  }, 1024)
                ]),
                _: 2
              }, 1024)
            ]);
          }), 128))
        ])),
        !hostDialogAvailable.value ? (_openBlock(), _createBlock(MediaDetailDialog, {
          key: 3,
          modelValue: detailOpenLocal.value,
          "onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => detailOpenLocal.value = $event),
          detail: detail.value,
          loading: detailLoading.value,
          error: detailError.value,
          "selected-item": selectedItem.value,
          cast: cast.value,
          "cast-loading": castLoading.value,
          "subscribing-ids": Array.from(subscribing.value),
          "image-domain": imageDomain.value,
          onRetry: retryMediaDetail,
          onSystemDetail: openSystemMediaDetail,
          onSubscribe: handleDetailSubscribe,
          onClose: handleDetailClosedByDialog
        }, null, 8, ["modelValue", "detail", "loading", "error", "selected-item", "cast", "cast-loading", "subscribing-ids", "image-domain"])) : _createCommentVNode("", true),
        _createVNode(_component_VSnackbar, {
          modelValue: snackbarShow.value,
          "onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => snackbarShow.value = $event),
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

const HeatList = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-075e03fd"]]);

export { HeatList as default };
