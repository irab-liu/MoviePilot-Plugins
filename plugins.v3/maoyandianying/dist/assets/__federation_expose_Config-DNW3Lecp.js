import { importShared } from './__federation_fn_import-JrT3xvdd.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,withCtx:_withCtx,createTextVNode:_createTextVNode,unref:_unref,openBlock:_openBlock,createBlock:_createBlock} = await importShared('vue');

const _hoisted_1 = { class: "d-flex flex-wrap gap-3 mb-3" };
const _hoisted_2 = { class: "d-flex flex-wrap gap-3 mb-3" };
const _hoisted_3 = { class: "d-flex flex-wrap gap-3" };
const {reactive,ref,watch} = await importShared('vue');

const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "Config",
  props: {
    initialConfig: {},
    api: {},
    pluginId: {}
  },
  emits: ["save", "close"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const emit = __emit;
    const intervalItems = [
      { title: "1小时", value: 1 },
      { title: "2小时", value: 2 },
      { title: "3小时", value: 3 },
      { title: "6小时", value: 6 },
      { title: "12小时", value: 12 },
      { title: "24小时", value: 24 }
    ];
    const hourItems = Array.from({ length: 24 }, (_, h) => ({
      title: `${h}时`,
      value: String(h)
    }));
    const msgtypeItems = [
      { title: "资源下载", value: "Download" },
      { title: "整理入库", value: "Organize" },
      { title: "订阅", value: "Subscribe" },
      { title: "站点", value: "SiteMessage" },
      { title: "媒体服务器", value: "MediaServer" },
      { title: "手动处理", value: "Manual" },
      { title: "插件", value: "Plugin" },
      { title: "智能体", value: "Agent" },
      { title: "其它", value: "Other" }
    ];
    const form = reactive({
      enabled: false,
      refresh_interval: 6,
      reminder_enabled: false,
      reminder_time: "9",
      reminder_msgtype: "Plugin",
      run_remind: false
    });
    const saving = ref(false);
    const clearingCache = ref(false);
    function buildPluginUrl(path) {
      return props.pluginId ? `plugin/${props.pluginId}/${path}` : `plugin/MaoyanDianYing/${path}`;
    }
    async function clearCache() {
      if (!props.api) {
        alert("API 未就绪，请刷新页面重试");
        return;
      }
      if (!confirm("确定要清理所有缓存数据吗？（保留提醒数据）并重新抓取新数据。")) {
        return;
      }
      clearingCache.value = true;
      try {
        const url = buildPluginUrl("clear-cache");
        const data = await props.api.post(url);
        if (data?.success) {
          alert(data?.message || "缓存已清理");
        } else {
          alert(data?.message || "清理失败");
        }
      } catch (e) {
        alert("请求失败：" + e);
      } finally {
        clearingCache.value = false;
      }
    }
    watch(
      () => props.initialConfig,
      (config) => {
        if (!config) return;
        form.enabled = Boolean(config.enabled);
        form.refresh_interval = Number(config.refresh_interval) || 6;
        form.reminder_enabled = Boolean(config.reminder_enabled);
        form.reminder_time = config.reminder_time !== void 0 && config.reminder_time !== null && config.reminder_time !== "" ? String(config.reminder_time) : "9";
        form.reminder_msgtype = config.reminder_msgtype ? String(config.reminder_msgtype) : "Plugin";
        form.run_remind = Boolean(config.run_remind);
      },
      { immediate: true, deep: true }
    );
    function save() {
      saving.value = true;
      emit("save", { ...form });
      saving.value = false;
    }
    return (_ctx, _cache) => {
      const _component_VIcon = _resolveComponent("VIcon");
      const _component_VSpacer = _resolveComponent("VSpacer");
      const _component_VBtn = _resolveComponent("VBtn");
      const _component_VCardTitle = _resolveComponent("VCardTitle");
      const _component_VDivider = _resolveComponent("VDivider");
      const _component_VSwitch = _resolveComponent("VSwitch");
      const _component_VSelect = _resolveComponent("VSelect");
      const _component_VCardText = _resolveComponent("VCardText");
      const _component_VCardActions = _resolveComponent("VCardActions");
      const _component_VCard = _resolveComponent("VCard");
      return _openBlock(), _createBlock(_component_VCard, {
        flat: "",
        class: "maoyan-config"
      }, {
        default: _withCtx(() => [
          _createVNode(_component_VCardTitle, { class: "d-flex align-center py-3 px-4" }, {
            default: _withCtx(() => [
              _createVNode(_component_VIcon, {
                icon: "mdi-trending-up",
                class: "mr-2",
                color: "primary"
              }),
              _cache[7] || (_cache[7] = _createElementVNode("span", null, "猫眼热度榜设置", -1)),
              _createVNode(_component_VSpacer),
              _createVNode(_component_VBtn, {
                icon: "mdi-close",
                variant: "text",
                size: "small",
                onClick: _cache[0] || (_cache[0] = ($event) => emit("close"))
              })
            ]),
            _: 1
          }),
          _createVNode(_component_VDivider),
          _createVNode(_component_VCardText, { class: "py-4" }, {
            default: _withCtx(() => [
              _cache[10] || (_cache[10] = _createElementVNode("div", { class: "text-subtitle-2 mb-3 grey--text" }, "基础设置", -1)),
              _createElementVNode("div", _hoisted_1, [
                _createVNode(_component_VSwitch, {
                  modelValue: form.enabled,
                  "onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => form.enabled = $event),
                  label: "启用插件",
                  color: "primary",
                  "hide-details": "",
                  density: "compact"
                }, null, 8, ["modelValue"]),
                _createVNode(_component_VBtn, {
                  variant: "tonal",
                  color: "error",
                  loading: clearingCache.value,
                  size: "small",
                  onClick: clearCache
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_VIcon, {
                      start: "",
                      size: "small"
                    }, {
                      default: _withCtx(() => [..._cache[8] || (_cache[8] = [
                        _createTextVNode("mdi-delete-sweep", -1)
                      ])]),
                      _: 1
                    }),
                    _cache[9] || (_cache[9] = _createTextVNode(" 清理缓存 ", -1))
                  ]),
                  _: 1
                }, 8, ["loading"])
              ]),
              _createVNode(_component_VSelect, {
                modelValue: form.refresh_interval,
                "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => form.refresh_interval = $event),
                items: intervalItems,
                "item-title": "title",
                "item-value": "value",
                label: "自动刷新间隔",
                variant: "outlined",
                density: "compact",
                "hide-details": "",
                style: { "max-width": "160px" }
              }, null, 8, ["modelValue"])
            ]),
            _: 1
          }),
          _createVNode(_component_VDivider),
          _createVNode(_component_VCardText, { class: "py-4" }, {
            default: _withCtx(() => [
              _cache[11] || (_cache[11] = _createElementVNode("div", { class: "text-subtitle-2 mb-3 grey--text" }, "提醒设置", -1)),
              _createElementVNode("div", _hoisted_2, [
                _createVNode(_component_VSwitch, {
                  modelValue: form.reminder_enabled,
                  "onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => form.reminder_enabled = $event),
                  label: "今日上新提醒",
                  color: "primary",
                  "hide-details": "",
                  density: "compact"
                }, null, 8, ["modelValue"]),
                _createVNode(_component_VSwitch, {
                  modelValue: form.run_remind,
                  "onUpdate:modelValue": _cache[4] || (_cache[4] = ($event) => form.run_remind = $event),
                  label: "立即运行一次提醒",
                  color: "secondary",
                  "hide-details": "",
                  density: "compact"
                }, null, 8, ["modelValue"])
              ]),
              _createElementVNode("div", _hoisted_3, [
                _createVNode(_component_VSelect, {
                  modelValue: form.reminder_time,
                  "onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => form.reminder_time = $event),
                  items: _unref(hourItems),
                  label: "提醒时间",
                  variant: "outlined",
                  density: "compact",
                  "hide-details": "",
                  style: { "max-width": "160px" }
                }, null, 8, ["modelValue", "items"]),
                _createVNode(_component_VSelect, {
                  modelValue: form.reminder_msgtype,
                  "onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => form.reminder_msgtype = $event),
                  items: msgtypeItems,
                  label: "消息类型",
                  variant: "outlined",
                  density: "compact",
                  "hide-details": "",
                  style: { "max-width": "160px" }
                }, null, 8, ["modelValue"])
              ])
            ]),
            _: 1
          }),
          _createVNode(_component_VDivider),
          _createVNode(_component_VCardActions, { class: "px-4 py-3" }, {
            default: _withCtx(() => [
              _createVNode(_component_VSpacer),
              _createVNode(_component_VBtn, {
                color: "primary",
                loading: saving.value,
                onClick: save
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VIcon, { start: "" }, {
                    default: _withCtx(() => [..._cache[12] || (_cache[12] = [
                      _createTextVNode("mdi-content-save", -1)
                    ])]),
                    _: 1
                  }),
                  _cache[13] || (_cache[13] = _createTextVNode(" 保存 ", -1))
                ]),
                _: 1
              }, 8, ["loading"])
            ]),
            _: 1
          })
        ]),
        _: 1
      });
    };
  }
});

export { _sfc_main as default };
