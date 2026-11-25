import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc, p as pluginRequest, e as errorMessage } from './_plugin-vue_export-helper-ClNIXR6t.js';

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createTextVNode:_createTextVNode,withCtx:_withCtx,createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,Transition:_Transition,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "atm-config" };
const _hoisted_2 = { class: "d-flex align-center mb-4" };

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
 * 在宿主插件设置中渲染，使用宿主全局注册的 Vuetify 组件；
 * 仅提供插件启用开关，任务管理功能在侧栏全页中完成。
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
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_card_title = _resolveComponent("v-card-title");
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_v_switch = _resolveComponent("v-switch");
  const _component_v_card_text = _resolveComponent("v-card-text");
  const _component_v_card_actions = _resolveComponent("v-card-actions");
  const _component_v_card = _resolveComponent("v-card");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createVNode(_component_v_card, {
      variant: "outlined",
      rounded: "lg"
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_card_title, { class: "d-flex align-center" }, {
          default: _withCtx(() => [
            _cache[2] || (_cache[2] = _createTextVNode(" Agent 定时任务管理 ", -1)),
            _createVNode(_component_v_spacer),
            _createVNode(_component_v_btn, {
              size: "small",
              variant: "text",
              icon: "mdi-close",
              onClick: _cache[0] || (_cache[0] = $event => (emit('close')))
            })
          ]),
          _: 1
        }),
        _createVNode(_component_v_card_text, null, {
          default: _withCtx(() => [
            _createVNode(_component_v_alert, {
              type: "info",
              variant: "tonal",
              class: "mb-4",
              density: "compact"
            }, {
              default: _withCtx(() => [...(_cache[3] || (_cache[3] = [
                _createTextVNode(" 本插件只提供 Agent 自主定时任务的管理界面，不新建调度器。启用后可在左侧「系统」分组找到入口。 ", -1)
              ]))]),
              _: 1
            }),
            _createElementVNode("div", _hoisted_2, [
              _createVNode(_component_v_switch, {
                modelValue: form.enabled,
                "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((form.enabled) = $event)),
                color: "primary",
                density: "compact",
                "hide-details": "",
                label: "启用插件",
                class: "mr-4"
              }, null, 8, ["modelValue"])
            ]),
            _createVNode(_Transition, { name: "fade" }, {
              default: _withCtx(() => [
                (message.show)
                  ? (_openBlock(), _createBlock(_component_v_alert, {
                      key: 0,
                      type: message.type,
                      variant: "tonal",
                      density: "compact"
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(message.text), 1)
                      ]),
                      _: 1
                    }, 8, ["type"]))
                  : _createCommentVNode("", true)
              ]),
              _: 1
            })
          ]),
          _: 1
        }),
        _createVNode(_component_v_card_actions, { class: "px-4 pb-4" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_spacer),
            _createVNode(_component_v_btn, {
              color: "primary",
              loading: saving.value,
              onClick: saveConfig
            }, {
              default: _withCtx(() => [...(_cache[4] || (_cache[4] = [
                _createTextVNode("保存", -1)
              ]))]),
              _: 1
            }, 8, ["loading"])
          ]),
          _: 1
        })
      ]),
      _: 1
    })
  ]))
}
}

};
const Config = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-1f6f1198"]]);

export { Config as default };
