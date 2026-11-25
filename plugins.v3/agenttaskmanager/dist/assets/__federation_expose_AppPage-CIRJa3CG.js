import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import Page from './__federation_expose_Page-Dc0PGnOZ.js';

const {normalizeProps:_normalizeProps,guardReactiveProps:_guardReactiveProps,openBlock:_openBlock,createBlock:_createBlock} = await importShared('vue');


const _sfc_main = /*@__PURE__*/Object.assign({ inheritAttrs: false }, {
  __name: 'AppPage',
  setup(__props) {

/**
 * Agent 定时任务管理全页入口包装组件。
 *
 * 宿主侧栏全页优先加载 AppPage；这里直接转发给 Page，保持单一实现。
 */


return (_ctx, _cache) => {
  return (_openBlock(), _createBlock(Page, _normalizeProps(_guardReactiveProps(_ctx.$attrs)), null, 16))
}
}

});

export { _sfc_main as default };
