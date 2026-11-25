import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc, p as pluginRequest, e as errorMessage } from './_plugin-vue_export-helper-ClNIXR6t.js';

const {createElementVNode:_createElementVNode,vModelCheckbox:_vModelCheckbox,withDirectives:_withDirectives,toDisplayString:_toDisplayString,normalizeClass:_normalizeClass,openBlock:_openBlock,createElementBlock:_createElementBlock,createCommentVNode:_createCommentVNode} = await importShared('vue');


const _hoisted_1 = { class: "atm-config" };
const _hoisted_2 = { class: "atm-config-card" };
const _hoisted_3 = { class: "atm-config-head" };
const _hoisted_4 = { class: "atm-config-body" };
const _hoisted_5 = { class: "atm-config-switch" };
const _hoisted_6 = { class: "atm-config-foot" };
const _hoisted_7 = ["disabled"];

const {onBeforeUnmount,reactive,ref} = await importShared('vue');


const _sfc_main = {
  __name: 'Config',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  initialConfig: { type: Object, default: () => ({}) },
},
  emits: ['close'],
  setup(__props, { emit: __emit }) {

/**
 * Agent 定时任务管理插件配置页。
 *
 * 纯 HTML/CSS 实现，在宿主插件设置中渲染，仅提供插件启用开关；
 * 任务管理功能在侧栏全页中完成。
 */
const props = __props;
const emit = __emit;

const saving = ref(false);
const message = reactive({ show: false, type: 'info', text: '' });
const form = reactive({
  enabled: true,
  ...(props.initialConfig || {}),
});
let messageTimer = null;

/** 显示一条自动消失的提示。 */
function showMessage(text, type = 'info') {
  if (messageTimer) clearTimeout(messageTimer);
  message.text = text;
  message.type = type;
  message.show = true;
  messageTimer = setTimeout(() => {
    message.show = false;
    messageTimer = null;
  }, 4000);
}

/** 保存插件配置。 */
async function saveConfig() {
  saving.value = true;
  try {
    const result = await pluginRequest(props.api, props.pluginId, '/config', {
      method: 'POST',
      body: { enabled: !!form.enabled },
    });
    if (!result?.success) {
      throw new Error(result?.message || '保存失败')
    }
    showMessage('配置已保存', 'success');
  } catch (error) {
    showMessage(errorMessage(error, '保存失败'), 'error');
  } finally {
    saving.value = false;
  }
}

onBeforeUnmount(() => {
  if (messageTimer) clearTimeout(messageTimer);
});

return (_ctx, _cache) => {
  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("div", _hoisted_2, [
      _createElementVNode("div", _hoisted_3, [
        _cache[2] || (_cache[2] = _createElementVNode("div", null, [
          _createElementVNode("div", { class: "atm-config-title" }, "Agent 定时任务管理"),
          _createElementVNode("div", { class: "atm-config-sub" }, "仅提供管理界面，不新建调度器")
        ], -1)),
        _createElementVNode("button", {
          class: "atm-config-close",
          onClick: _cache[0] || (_cache[0] = $event => (emit('close')))
        }, "×")
      ]),
      _createElementVNode("div", _hoisted_4, [
        _cache[4] || (_cache[4] = _createElementVNode("div", { class: "atm-config-tip" }, " 启用后可在左侧「系统」分组找到「Agent 定时任务」入口。新建任务仍通过对话让 Agent 使用 agent_task 工具创建。 ", -1)),
        _createElementVNode("label", _hoisted_5, [
          _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((form.enabled) = $event)),
            type: "checkbox"
          }, null, 512), [
            [_vModelCheckbox, form.enabled]
          ]),
          _cache[3] || (_cache[3] = _createElementVNode("span", null, "启用插件", -1))
        ]),
        (message.show)
          ? (_openBlock(), _createElementBlock("div", {
              key: 0,
              class: _normalizeClass(["atm-config-msg", `atm-config-msg--${message.type}`])
            }, _toDisplayString(message.text), 3))
          : _createCommentVNode("", true)
      ]),
      _createElementVNode("div", _hoisted_6, [
        _createElementVNode("button", {
          class: "atm-config-btn atm-config-btn--primary",
          disabled: saving.value,
          onClick: saveConfig
        }, _toDisplayString(saving.value ? '保存中…' : '保存'), 9, _hoisted_7)
      ])
    ])
  ]))
}
}

};
const Config = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-8f64f78f"]]);

export { Config as default };
