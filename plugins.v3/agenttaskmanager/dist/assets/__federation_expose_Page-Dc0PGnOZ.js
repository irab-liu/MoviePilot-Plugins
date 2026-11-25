import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc, t as triggerTypeLabel, a as triggerText, s as statusMeta, p as pluginRequest, e as errorMessage } from './_plugin-vue_export-helper-ClNIXR6t.js';

const {createTextVNode:_createTextVNode,resolveComponent:_resolveComponent,withCtx:_withCtx,createVNode:_createVNode,createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,createElementBlock:_createElementBlock,renderList:_renderList,Fragment:_Fragment,unref:_unref} = await importShared('vue');


const _hoisted_1 = { class: "atm-page" };
const _hoisted_2 = { class: "d-flex align-center flex-wrap gap-2 mb-4" };
const _hoisted_3 = { class: "d-flex align-center mb-3" };
const _hoisted_4 = {
  key: 0,
  class: "text-center py-8"
};
const _hoisted_5 = {
  key: 2,
  class: "atm-table-wrap"
};
const _hoisted_6 = { class: "atm-table" };
const _hoisted_7 = { class: "font-weight-medium" };
const _hoisted_8 = {
  key: 0,
  class: "text-caption text-grey"
};
const _hoisted_9 = { class: "text-caption text-grey" };
const _hoisted_10 = { class: "text-caption atm-mono" };
const _hoisted_11 = { class: "text-caption" };
const _hoisted_12 = { class: "text-caption" };
const _hoisted_13 = { class: "text-caption atm-mono" };
const _hoisted_14 = { class: "text-right" };
const _hoisted_15 = { class: "d-inline-flex flex-wrap justify-end gap-1" };
const _hoisted_16 = { class: "d-flex gap-2 mb-3" };
const _hoisted_17 = { class: "text-caption text-grey mb-3" };
const _hoisted_18 = {
  key: 0,
  class: "text-center py-8"
};
const _hoisted_19 = {
  key: 2,
  class: "atm-table-wrap"
};
const _hoisted_20 = { class: "atm-table" };
const _hoisted_21 = { class: "text-caption atm-mono" };
const _hoisted_22 = { class: "text-caption" };
const _hoisted_23 = { class: "text-caption" };
const _hoisted_24 = { class: "text-caption" };
const _hoisted_25 = { class: "text-caption atm-result-cell" };
const _hoisted_26 = { key: 0 };
const _hoisted_27 = { class: "atm-result" };

const {computed,onMounted,reactive,ref} = await importShared('vue');


const _sfc_main = {
  __name: 'Page',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  navKey: { type: String, default: 'main' },
},
  setup(__props) {

/**
 * Agent 定时任务管理主页面。
 *
 * 使用宿主全局注册的 Vuetify 组件渲染；按钮不因 running/停用状态被禁用，
 * 不可执行时由后端返回明确提示，避免出现按钮全灰无法点击的问题。
 */
const props = __props;

const loading = ref(false);
const tasks = ref([]);
const total = ref(0);
const aiAgentEnable = ref(true);
const filterEnabled = ref(null);
const busyIds = ref(new Set());
const snackbar = reactive({ show: false, text: '', color: 'info' });

const filterOptions = [
  { title: '全部', value: null },
  { title: '已启用', value: true },
  { title: '已停用', value: false },
];

const editDialog = ref(false);
const editSaving = ref(false);
const editForm = reactive({
  id: null,
  name: '',
  content: '',
  trigger_type: 'cron',
  cron_expression: '',
  run_at: '',
});

const historyDialog = ref(false);
const historyLoading = ref(false);
const historyTask = ref(null);
const historyRuns = ref([]);

const deleteDialog = ref(false);
const deleteTarget = ref(null);
const deleteLoading = ref(false);

const hasTasks = computed(() => tasks.value.length > 0);

/** 显示一条顶部提示。 */
function showSnackbar(text, color = 'info') {
  snackbar.text = text;
  snackbar.color = color;
  snackbar.show = true;
}

/** 标记某行正在操作。 */
function setBusy(id, busy) {
  const next = new Set(busyIds.value);
  if (busy) next.add(id);
  else next.delete(id);
  busyIds.value = next;
}

/** 拉取任务列表。 */
async function loadTasks() {
  loading.value = true;
  try {
    const params = {};
    if (filterEnabled.value !== null) params.enabled = filterEnabled.value ? 'true' : 'false';
    const result = await pluginRequest(props.api, props.pluginId, '/tasks', {
      method: 'GET',
      params,
    });
    tasks.value = result?.tasks || [];
    total.value = result?.total || 0;
    aiAgentEnable.value = result?.ai_agent_enable !== false;
  } catch (error) {
    showSnackbar(errorMessage(error, '加载任务列表失败'), 'error');
  } finally {
    loading.value = false;
  }
}

/** 切换启停状态。 */
async function onToggle(row, value) {
  setBusy(row.id, true);
  try {
    const result = await pluginRequest(
      props.api,
      props.pluginId,
      `/tasks/${row.id}/toggle`,
      { method: 'POST', body: { enabled: value } },
    );
    if (result?.task) {
      const index = tasks.value.findIndex((item) => item.id === row.id);
      if (index >= 0) tasks.value[index] = result.task;
    } else {
      row.enabled = value;
    }
    showSnackbar(result?.message || (value ? '任务已启用' : '任务已停用'), 'success');
  } catch (error) {
    showSnackbar(errorMessage(error, '启停任务失败'), 'error');
    await loadTasks();
  } finally {
    setBusy(row.id, false);
  }
}

/** 立即执行任务。 */
async function onRun(row) {
  setBusy(row.id, true);
  try {
    const result = await pluginRequest(
      props.api,
      props.pluginId,
      `/tasks/${row.id}/run`,
      { method: 'POST' },
    );
    showSnackbar(result?.message || '已提交立即执行', 'success');
    await loadTasks();
  } catch (error) {
    showSnackbar(errorMessage(error, '立即执行失败'), 'error');
  } finally {
    setBusy(row.id, false);
  }
}

/** 打开编辑弹窗并填充表单。 */
function openEdit(row) {
  editForm.id = row.id;
  editForm.name = row.name || '';
  editForm.content = row.content || '';
  editForm.trigger_type = row.trigger_type === 'date' ? 'date' : 'cron';
  editForm.cron_expression = row.cron_expression || '';
  editForm.run_at = row.run_at || '';
  editDialog.value = true;
}

/** 保存编辑。 */
async function saveEdit() {
  if (!editForm.name.trim()) {
    showSnackbar('任务名称不能为空', 'error');
    return
  }
  if (!editForm.content.trim()) {
    showSnackbar('任务指令不能为空', 'error');
    return
  }
  const body = {
    name: editForm.name.trim(),
    content: editForm.content.trim(),
    trigger_type: editForm.trigger_type,
  };
  if (editForm.trigger_type === 'cron') {
    if (!editForm.cron_expression.trim()) {
      showSnackbar('请填写五段 cron 表达式', 'error');
      return
    }
    body.cron_expression = editForm.cron_expression.trim();
  } else {
    if (!editForm.run_at.trim()) {
      showSnackbar('请填写单次触发时间', 'error');
      return
    }
    body.run_at = editForm.run_at.trim();
  }

  editSaving.value = true;
  try {
    const result = await pluginRequest(
      props.api,
      props.pluginId,
      `/tasks/${editForm.id}/update`,
      { method: 'POST', body },
    );
    showSnackbar(result?.message || '任务已更新', 'success');
    editDialog.value = false;
    await loadTasks();
  } catch (error) {
    showSnackbar(errorMessage(error, '保存任务失败'), 'error');
  } finally {
    editSaving.value = false;
  }
}

/** 打开运行历史弹窗。 */
async function openHistory(row) {
  historyTask.value = row;
  historyDialog.value = true;
  historyLoading.value = true;
  historyRuns.value = [];
  try {
    const result = await pluginRequest(
      props.api,
      props.pluginId,
      `/tasks/${row.id}/runs`,
      { method: 'GET', params: { limit: 50 } },
    );
    historyRuns.value = result?.runs || [];
  } catch (error) {
    showSnackbar(errorMessage(error, '加载运行历史失败'), 'error');
  } finally {
    historyLoading.value = false;
  }
}

/** 打开删除确认弹窗。 */
function openDelete(row) {
  deleteTarget.value = row;
  deleteDialog.value = true;
}

/** 确认删除。 */
async function confirmDelete() {
  if (!deleteTarget.value) return
  deleteLoading.value = true;
  try {
    const result = await pluginRequest(
      props.api,
      props.pluginId,
      `/tasks/${deleteTarget.value.id}/delete`,
      { method: 'POST' },
    );
    showSnackbar(result?.message || '任务已删除', 'success');
    deleteDialog.value = false;
    deleteTarget.value = null;
    await loadTasks();
  } catch (error) {
    showSnackbar(errorMessage(error, '删除任务失败'), 'error');
  } finally {
    deleteLoading.value = false;
  }
}

/** 触发来源展示文本。 */
function triggerSourceLabel(source) {
  return source === 'manual' ? '手动' : source === 'scheduled' ? '定时' : source || '未知'
}

/** 触发配置占位提示。 */
const triggerHint = computed(() =>
  editForm.trigger_type === 'cron'
    ? '标准五段 cron 表达式，例如：0 10,22 * * *'
    : '带时区 ISO 8601 时间，例如：2026-12-31 08:00:00',
);

onMounted(loadTasks);

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent("v-icon");
  const _component_v_chip = _resolveComponent("v-chip");
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_col = _resolveComponent("v-col");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_v_select = _resolveComponent("v-select");
  const _component_v_progress_circular = _resolveComponent("v-progress-circular");
  const _component_v_switch = _resolveComponent("v-switch");
  const _component_v_card_text = _resolveComponent("v-card-text");
  const _component_v_card = _resolveComponent("v-card");
  const _component_v_container = _resolveComponent("v-container");
  const _component_v_card_title = _resolveComponent("v-card-title");
  const _component_v_text_field = _resolveComponent("v-text-field");
  const _component_v_textarea = _resolveComponent("v-textarea");
  const _component_v_card_actions = _resolveComponent("v-card-actions");
  const _component_v_dialog = _resolveComponent("v-dialog");
  const _component_v_snackbar = _resolveComponent("v-snackbar");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createVNode(_component_v_container, {
      fluid: "",
      class: "pa-4"
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_row, null, {
          default: _withCtx(() => [
            _createVNode(_component_v_col, { cols: "12" }, {
              default: _withCtx(() => [
                _createElementVNode("div", _hoisted_2, [
                  _createVNode(_component_v_icon, {
                    size: "x-small",
                    class: "mr-1"
                  }, {
                    default: _withCtx(() => [...(_cache[15] || (_cache[15] = [
                      _createTextVNode("mdi-clock-outline", -1)
                    ]))]),
                    _: 1
                  }),
                  _cache[18] || (_cache[18] = _createElementVNode("span", { class: "text-h6 font-weight-bold" }, "Agent 定时任务", -1)),
                  _createVNode(_component_v_chip, {
                    size: "small",
                    color: "primary",
                    variant: "tonal"
                  }, {
                    default: _withCtx(() => [
                      _createTextVNode(_toDisplayString(total.value), 1)
                    ]),
                    _: 1
                  }),
                  _createVNode(_component_v_spacer),
                  _createVNode(_component_v_btn, {
                    size: "small",
                    color: "primary",
                    variant: "tonal",
                    loading: loading.value,
                    onClick: loadTasks
                  }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_icon, { start: "" }, {
                        default: _withCtx(() => [...(_cache[16] || (_cache[16] = [
                          _createTextVNode("mdi-refresh", -1)
                        ]))]),
                        _: 1
                      }),
                      _cache[17] || (_cache[17] = _createTextVNode(" 刷新 ", -1))
                    ]),
                    _: 1
                  }, 8, ["loading"])
                ])
              ]),
              _: 1
            })
          ]),
          _: 1
        }),
        _createVNode(_component_v_row, null, {
          default: _withCtx(() => [
            _createVNode(_component_v_col, { cols: "12" }, {
              default: _withCtx(() => [
                (!aiAgentEnable.value)
                  ? (_openBlock(), _createBlock(_component_v_alert, {
                      key: 0,
                      type: "warning",
                      variant: "tonal",
                      class: "mb-4",
                      icon: "mdi-alert",
                      prominent: ""
                    }, {
                      default: _withCtx(() => [...(_cache[19] || (_cache[19] = [
                        _createTextVNode(" AI Agent 未启用（AI_AGENT_ENABLE=false），自主定时任务不会被调度执行。此处仅能查看和管理任务配置。 ", -1)
                      ]))]),
                      _: 1
                    }))
                  : _createCommentVNode("", true),
                _createVNode(_component_v_card, {
                  variant: "outlined",
                  rounded: "lg"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card_text, null, {
                      default: _withCtx(() => [
                        _createElementVNode("div", _hoisted_3, [
                          _createVNode(_component_v_select, {
                            modelValue: filterEnabled.value,
                            "onUpdate:modelValue": [
                              _cache[0] || (_cache[0] = $event => ((filterEnabled).value = $event)),
                              loadTasks
                            ],
                            items: filterOptions,
                            label: "启用状态",
                            variant: "outlined",
                            density: "compact",
                            "hide-details": "",
                            class: "atm-filter"
                          }, null, 8, ["modelValue"])
                        ]),
                        (loading.value && !hasTasks.value)
                          ? (_openBlock(), _createElementBlock("div", _hoisted_4, [
                              _createVNode(_component_v_progress_circular, {
                                indeterminate: "",
                                color: "primary"
                              }),
                              _cache[20] || (_cache[20] = _createElementVNode("div", { class: "text-caption text-grey mt-2" }, "正在加载任务列表…", -1))
                            ]))
                          : (!hasTasks.value)
                            ? (_openBlock(), _createBlock(_component_v_alert, {
                                key: 1,
                                type: "info",
                                variant: "tonal",
                                icon: "mdi-information"
                              }, {
                                default: _withCtx(() => [...(_cache[21] || (_cache[21] = [
                                  _createTextVNode(" 暂无 Agent 定时任务。新建任务仍通过对话让 Agent 使用 agent_task 工具创建。 ", -1)
                                ]))]),
                                _: 1
                              }))
                            : (_openBlock(), _createElementBlock("div", _hoisted_5, [
                                _createElementVNode("table", _hoisted_6, [
                                  _cache[26] || (_cache[26] = _createElementVNode("thead", null, [
                                    _createElementVNode("tr", null, [
                                      _createElementVNode("th", null, "任务"),
                                      _createElementVNode("th", null, "触发"),
                                      _createElementVNode("th", null, "最近状态"),
                                      _createElementVNode("th", null, "上次运行"),
                                      _createElementVNode("th", null, "次数"),
                                      _createElementVNode("th", null, "下次运行"),
                                      _createElementVNode("th", null, "启用"),
                                      _createElementVNode("th", { class: "text-right" }, "操作")
                                    ])
                                  ], -1)),
                                  _createElementVNode("tbody", null, [
                                    (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(tasks.value, (row) => {
                                      return (_openBlock(), _createElementBlock("tr", {
                                        key: row.id
                                      }, [
                                        _createElementVNode("td", null, [
                                          _createElementVNode("div", _hoisted_7, _toDisplayString(row.name), 1),
                                          (row.owner_username || row.owner_user_id)
                                            ? (_openBlock(), _createElementBlock("div", _hoisted_8, " 归属：" + _toDisplayString(row.owner_username || row.owner_user_id), 1))
                                            : _createCommentVNode("", true),
                                          _createElementVNode("div", _hoisted_9, [
                                            _createTextVNode(" ID " + _toDisplayString(row.id) + " ", 1),
                                            _createVNode(_component_v_chip, {
                                              size: "x-small",
                                              variant: "tonal",
                                              class: "ml-1"
                                            }, {
                                              default: _withCtx(() => [
                                                _createTextVNode(_toDisplayString(_unref(triggerTypeLabel)(row.trigger_type)), 1)
                                              ]),
                                              _: 2
                                            }, 1024)
                                          ])
                                        ]),
                                        _createElementVNode("td", _hoisted_10, _toDisplayString(_unref(triggerText)(row)), 1),
                                        _createElementVNode("td", null, [
                                          _createVNode(_component_v_chip, {
                                            size: "small",
                                            color: _unref(statusMeta)(row.last_status).chip
                                          }, {
                                            default: _withCtx(() => [
                                              _createTextVNode(_toDisplayString(_unref(statusMeta)(row.last_status).label), 1)
                                            ]),
                                            _: 2
                                          }, 1032, ["color"])
                                        ]),
                                        _createElementVNode("td", _hoisted_11, _toDisplayString(row.last_run_at || '—'), 1),
                                        _createElementVNode("td", _hoisted_12, _toDisplayString(row.run_count), 1),
                                        _createElementVNode("td", _hoisted_13, _toDisplayString(row.next_run_at || '—'), 1),
                                        _createElementVNode("td", null, [
                                          _createVNode(_component_v_switch, {
                                            "model-value": Boolean(row.enabled),
                                            disabled: busyIds.value.has(row.id),
                                            density: "compact",
                                            "hide-details": "",
                                            color: "primary",
                                            "onUpdate:modelValue": (value) => onToggle(row, value)
                                          }, null, 8, ["model-value", "disabled", "onUpdate:modelValue"])
                                        ]),
                                        _createElementVNode("td", _hoisted_14, [
                                          _createElementVNode("div", _hoisted_15, [
                                            _createVNode(_component_v_btn, {
                                              size: "x-small",
                                              variant: "tonal",
                                              color: "primary",
                                              disabled: busyIds.value.has(row.id),
                                              onClick: $event => (onRun(row))
                                            }, {
                                              default: _withCtx(() => [...(_cache[22] || (_cache[22] = [
                                                _createTextVNode(" 执行 ", -1)
                                              ]))]),
                                              _: 1
                                            }, 8, ["disabled", "onClick"]),
                                            _createVNode(_component_v_btn, {
                                              size: "x-small",
                                              variant: "tonal",
                                              disabled: busyIds.value.has(row.id),
                                              onClick: $event => (openEdit(row))
                                            }, {
                                              default: _withCtx(() => [...(_cache[23] || (_cache[23] = [
                                                _createTextVNode(" 编辑 ", -1)
                                              ]))]),
                                              _: 1
                                            }, 8, ["disabled", "onClick"]),
                                            _createVNode(_component_v_btn, {
                                              size: "x-small",
                                              variant: "tonal",
                                              onClick: $event => (openHistory(row))
                                            }, {
                                              default: _withCtx(() => [...(_cache[24] || (_cache[24] = [
                                                _createTextVNode(" 历史 ", -1)
                                              ]))]),
                                              _: 1
                                            }, 8, ["onClick"]),
                                            _createVNode(_component_v_btn, {
                                              size: "x-small",
                                              variant: "tonal",
                                              color: "error",
                                              disabled: busyIds.value.has(row.id),
                                              onClick: $event => (openDelete(row))
                                            }, {
                                              default: _withCtx(() => [...(_cache[25] || (_cache[25] = [
                                                _createTextVNode(" 删除 ", -1)
                                              ]))]),
                                              _: 1
                                            }, 8, ["disabled", "onClick"])
                                          ])
                                        ])
                                      ]))
                                    }), 128))
                                  ])
                                ])
                              ]))
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        })
      ]),
      _: 1
    }),
    _createVNode(_component_v_dialog, {
      modelValue: editDialog.value,
      "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((editDialog).value = $event)),
      "max-width": "720",
      persistent: ""
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_card, { rounded: "lg" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card_title, { class: "d-flex align-center" }, {
              default: _withCtx(() => [
                _createTextVNode(" 编辑任务 #" + _toDisplayString(editForm.id) + " ", 1),
                _createVNode(_component_v_spacer),
                _createVNode(_component_v_btn, {
                  size: "small",
                  variant: "text",
                  icon: "mdi-close",
                  onClick: _cache[1] || (_cache[1] = $event => (editDialog.value = false))
                })
              ]),
              _: 1
            }),
            _createVNode(_component_v_card_text, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_text_field, {
                  modelValue: editForm.name,
                  "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((editForm.name) = $event)),
                  label: "任务名称",
                  variant: "outlined",
                  density: "compact",
                  maxlength: "100",
                  class: "mb-3"
                }, null, 8, ["modelValue"]),
                _createElementVNode("div", _hoisted_16, [
                  _createVNode(_component_v_select, {
                    modelValue: editForm.trigger_type,
                    "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((editForm.trigger_type) = $event)),
                    items: [
                { title: '周期（cron）', value: 'cron' },
                { title: '单次（date）', value: 'date' },
              ],
                    label: "触发类型",
                    variant: "outlined",
                    density: "compact",
                    "hide-details": "",
                    class: "atm-trigger-select"
                  }, null, 8, ["modelValue"]),
                  (editForm.trigger_type === 'cron')
                    ? (_openBlock(), _createBlock(_component_v_text_field, {
                        key: 0,
                        modelValue: editForm.cron_expression,
                        "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((editForm.cron_expression) = $event)),
                        label: "cron 表达式",
                        variant: "outlined",
                        density: "compact",
                        "hide-details": ""
                      }, null, 8, ["modelValue"]))
                    : (_openBlock(), _createBlock(_component_v_text_field, {
                        key: 1,
                        modelValue: editForm.run_at,
                        "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((editForm.run_at) = $event)),
                        label: "单次触发时间",
                        variant: "outlined",
                        density: "compact",
                        "hide-details": ""
                      }, null, 8, ["modelValue"]))
                ]),
                _createElementVNode("div", _hoisted_17, _toDisplayString(triggerHint.value), 1),
                _createVNode(_component_v_textarea, {
                  modelValue: editForm.content,
                  "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((editForm.content) = $event)),
                  label: "任务指令（交给 Agent 执行的完整内容）",
                  variant: "outlined",
                  density: "compact",
                  rows: "6",
                  maxlength: "10000",
                  "hide-details": ""
                }, null, 8, ["modelValue"])
              ]),
              _: 1
            }),
            _createVNode(_component_v_card_actions, { class: "px-4 pb-4" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_spacer),
                _createVNode(_component_v_btn, {
                  variant: "text",
                  onClick: _cache[7] || (_cache[7] = $event => (editDialog.value = false))
                }, {
                  default: _withCtx(() => [...(_cache[27] || (_cache[27] = [
                    _createTextVNode("取消", -1)
                  ]))]),
                  _: 1
                }),
                _createVNode(_component_v_btn, {
                  color: "primary",
                  loading: editSaving.value,
                  onClick: saveEdit
                }, {
                  default: _withCtx(() => [...(_cache[28] || (_cache[28] = [
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
      ]),
      _: 1
    }, 8, ["modelValue"]),
    _createVNode(_component_v_dialog, {
      modelValue: historyDialog.value,
      "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => ((historyDialog).value = $event)),
      "max-width": "860"
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_card, { rounded: "lg" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card_title, { class: "d-flex align-center" }, {
              default: _withCtx(() => [
                _createTextVNode(" 运行历史：" + _toDisplayString(historyTask.value?.name || '') + " ", 1),
                _createVNode(_component_v_spacer),
                _createVNode(_component_v_btn, {
                  size: "small",
                  variant: "text",
                  icon: "mdi-close",
                  onClick: _cache[9] || (_cache[9] = $event => (historyDialog.value = false))
                })
              ]),
              _: 1
            }),
            _createVNode(_component_v_card_text, null, {
              default: _withCtx(() => [
                (historyLoading.value)
                  ? (_openBlock(), _createElementBlock("div", _hoisted_18, [
                      _createVNode(_component_v_progress_circular, {
                        indeterminate: "",
                        color: "primary"
                      })
                    ]))
                  : (!historyRuns.value.length)
                    ? (_openBlock(), _createBlock(_component_v_alert, {
                        key: 1,
                        type: "info",
                        variant: "tonal"
                      }, {
                        default: _withCtx(() => [...(_cache[29] || (_cache[29] = [
                          _createTextVNode(" 暂无运行历史。 ", -1)
                        ]))]),
                        _: 1
                      }))
                    : (_openBlock(), _createElementBlock("div", _hoisted_19, [
                        _createElementVNode("table", _hoisted_20, [
                          _cache[31] || (_cache[31] = _createElementVNode("thead", null, [
                            _createElementVNode("tr", null, [
                              _createElementVNode("th", null, "Run ID"),
                              _createElementVNode("th", null, "来源"),
                              _createElementVNode("th", null, "状态"),
                              _createElementVNode("th", null, "开始时间"),
                              _createElementVNode("th", null, "结束时间"),
                              _createElementVNode("th", null, "结果")
                            ])
                          ], -1)),
                          _createElementVNode("tbody", null, [
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(historyRuns.value, (run) => {
                              return (_openBlock(), _createElementBlock("tr", {
                                key: run.run_id
                              }, [
                                _createElementVNode("td", _hoisted_21, _toDisplayString(run.run_id), 1),
                                _createElementVNode("td", _hoisted_22, _toDisplayString(triggerSourceLabel(run.trigger_source)), 1),
                                _createElementVNode("td", null, [
                                  _createVNode(_component_v_chip, {
                                    size: "small",
                                    color: _unref(statusMeta)(run.status).chip
                                  }, {
                                    default: _withCtx(() => [
                                      _createTextVNode(_toDisplayString(_unref(statusMeta)(run.status).label), 1)
                                    ]),
                                    _: 2
                                  }, 1032, ["color"])
                                ]),
                                _createElementVNode("td", _hoisted_23, _toDisplayString(run.started_at || '—'), 1),
                                _createElementVNode("td", _hoisted_24, _toDisplayString(run.finished_at || '—'), 1),
                                _createElementVNode("td", _hoisted_25, [
                                  (run.result)
                                    ? (_openBlock(), _createElementBlock("details", _hoisted_26, [
                                        _cache[30] || (_cache[30] = _createElementVNode("summary", { class: "atm-result-toggle" }, "查看结果", -1)),
                                        _createElementVNode("pre", _hoisted_27, _toDisplayString(run.result), 1)
                                      ]))
                                    : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
                                        _createTextVNode("—")
                                      ], 64))
                                ])
                              ]))
                            }), 128))
                          ])
                        ])
                      ]))
              ]),
              _: 1
            }),
            _createVNode(_component_v_card_actions, { class: "px-4 pb-4" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_spacer),
                _createVNode(_component_v_btn, {
                  variant: "text",
                  onClick: _cache[10] || (_cache[10] = $event => (historyDialog.value = false))
                }, {
                  default: _withCtx(() => [...(_cache[32] || (_cache[32] = [
                    _createTextVNode("关闭", -1)
                  ]))]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        })
      ]),
      _: 1
    }, 8, ["modelValue"]),
    _createVNode(_component_v_dialog, {
      modelValue: deleteDialog.value,
      "onUpdate:modelValue": _cache[13] || (_cache[13] = $event => ((deleteDialog).value = $event)),
      "max-width": "480",
      persistent: ""
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_card, { rounded: "lg" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_card_title, null, {
              default: _withCtx(() => [...(_cache[33] || (_cache[33] = [
                _createTextVNode("删除任务", -1)
              ]))]),
              _: 1
            }),
            _createVNode(_component_v_card_text, null, {
              default: _withCtx(() => [
                _createTextVNode(" 确定要删除任务「" + _toDisplayString(deleteTarget.value?.name || '') + "」（#" + _toDisplayString(deleteTarget.value?.id || '') + "）吗？ 删除会一并清除其全部运行历史，且不可恢复。 ", 1)
              ]),
              _: 1
            }),
            _createVNode(_component_v_card_actions, { class: "px-4 pb-4" }, {
              default: _withCtx(() => [
                _createVNode(_component_v_spacer),
                _createVNode(_component_v_btn, {
                  variant: "text",
                  onClick: _cache[12] || (_cache[12] = $event => (deleteDialog.value = false))
                }, {
                  default: _withCtx(() => [...(_cache[34] || (_cache[34] = [
                    _createTextVNode("取消", -1)
                  ]))]),
                  _: 1
                }),
                _createVNode(_component_v_btn, {
                  color: "error",
                  loading: deleteLoading.value,
                  onClick: confirmDelete
                }, {
                  default: _withCtx(() => [...(_cache[35] || (_cache[35] = [
                    _createTextVNode("删除", -1)
                  ]))]),
                  _: 1
                }, 8, ["loading"])
              ]),
              _: 1
            })
          ]),
          _: 1
        })
      ]),
      _: 1
    }, 8, ["modelValue"]),
    _createVNode(_component_v_snackbar, {
      modelValue: snackbar.show,
      "onUpdate:modelValue": _cache[14] || (_cache[14] = $event => ((snackbar.show) = $event)),
      color: snackbar.color,
      timeout: "3000"
    }, {
      default: _withCtx(() => [
        _createTextVNode(_toDisplayString(snackbar.text), 1)
      ]),
      _: 1
    }, 8, ["modelValue", "color"])
  ]))
}
}

};
const Page = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-e6b15382"]]);

export { Page as default };
