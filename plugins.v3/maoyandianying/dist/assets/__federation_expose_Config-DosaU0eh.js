import { importShared } from './__federation_fn_import-JrT3xvdd.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {createElementVNode:_createElementVNode,resolveComponent:_resolveComponent,createVNode:_createVNode,createTextVNode:_createTextVNode,withCtx:_withCtx,openBlock:_openBlock,createElementBlock:_createElementBlock} = await importShared('vue');

const _hoisted_1 = { class: "maoyan-config pa-4" };
const _hoisted_2 = { class: "d-flex justify-end mt-4" };
const {reactive,ref,watch} = await importShared('vue');

const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "Config",
  props: {
    initialConfig: {}
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
    const form = reactive({
      enabled: false,
      refresh_interval: 6
    });
    const saving = ref(false);
    watch(
      () => props.initialConfig,
      (config) => {
        if (!config) return;
        form.enabled = Boolean(config.enabled);
        form.refresh_interval = Number(config.refresh_interval) || 6;
      },
      { immediate: true, deep: true }
    );
    function save() {
      saving.value = true;
      emit("save", { ...form });
      saving.value = false;
    }
    return (_ctx, _cache) => {
      const _component_VSwitch = _resolveComponent("VSwitch");
      const _component_VSelect = _resolveComponent("VSelect");
      const _component_VIcon = _resolveComponent("VIcon");
      const _component_VBtn = _resolveComponent("VBtn");
      return _openBlock(), _createElementBlock("div", _hoisted_1, [
        _cache[4] || (_cache[4] = _createElementVNode("div", { class: "text-h6 mb-4" }, "猫眼热度榜设置", -1)),
        _createVNode(_component_VSwitch, {
          modelValue: form.enabled,
          "onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => form.enabled = $event),
          label: "启用插件",
          color: "primary"
        }, null, 8, ["modelValue"]),
        _createVNode(_component_VSelect, {
          modelValue: form.refresh_interval,
          "onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => form.refresh_interval = $event),
          items: intervalItems,
          "item-title": "title",
          "item-value": "value",
          label: "自动刷新间隔（小时）",
          class: "mt-3"
        }, null, 8, ["modelValue"]),
        _createElementVNode("div", _hoisted_2, [
          _createVNode(_component_VBtn, {
            color: "primary",
            loading: saving.value,
            onClick: save
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VIcon, { start: "" }, {
                default: _withCtx(() => [..._cache[2] || (_cache[2] = [
                  _createTextVNode("mdi-content-save", -1)
                ])]),
                _: 1
              }),
              _cache[3] || (_cache[3] = _createTextVNode(" 保存 ", -1))
            ]),
            _: 1
          }, 8, ["loading"])
        ])
      ]);
    };
  }
});

export { _sfc_main as default };
