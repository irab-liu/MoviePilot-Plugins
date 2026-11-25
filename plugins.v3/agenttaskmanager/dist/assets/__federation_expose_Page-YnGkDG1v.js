import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc, t as triggerTypeLabel, a as triggerText, s as statusMeta, p as pluginRequest, e as errorMessage } from './_plugin-vue_export-helper-ClNIXR6t.js';

const {createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,openBlock:_openBlock,createElementBlock:_createElementBlock,createCommentVNode:_createCommentVNode,vModelSelect:_vModelSelect,withDirectives:_withDirectives,renderList:_renderList,Fragment:_Fragment,unref:_unref,normalizeClass:_normalizeClass,vModelText:_vModelText,Transition:_Transition,withCtx:_withCtx,createVNode:_createVNode} = await importShared('vue');


const _hoisted_1 = { class: "atm-page" };
const _hoisted_2 = { class: "atm-header" };
const _hoisted_3 = { class: "atm-title" };
const _hoisted_4 = { class: "atm-count" };
const _hoisted_5 = ["disabled"];
const _hoisted_6 = {
  key: 0,
  class: "atm-alert atm-alert--warn"
};
const _hoisted_7 = { class: "atm-toolbar" };
const _hoisted_8 = {
  key: 1,
  class: "atm-empty"
};
const _hoisted_9 = {
  key: 2,
  class: "atm-alert atm-alert--info"
};
const _hoisted_10 = {
  key: 3,
  class: "atm-table-wrap"
};
const _hoisted_11 = { class: "atm-table" };
const _hoisted_12 = { class: "atm-name" };
const _hoisted_13 = {
  key: 0,
  class: "atm-sub"
};
const _hoisted_14 = { class: "atm-sub" };
const _hoisted_15 = { class: "atm-mono" };
const _hoisted_16 = { class: "atm-sub" };
const _hoisted_17 = { class: "atm-sub" };
const _hoisted_18 = { class: "atm-mono" };
const _hoisted_19 = ["disabled", "onClick"];
const _hoisted_20 = { class: "atm-right" };
const _hoisted_21 = { class: "atm-actions" };
const _hoisted_22 = ["disabled", "onClick"];
const _hoisted_23 = ["disabled", "onClick"];
const _hoisted_24 = ["onClick"];
const _hoisted_25 = ["disabled", "onClick"];
const _hoisted_26 = {
  key: 4,
  class: "atm-modal"
};
const _hoisted_27 = { class: "atm-modal-box" };
const _hoisted_28 = { class: "atm-modal-head" };
const _hoisted_29 = { class: "atm-modal-body" };
const _hoisted_30 = { class: "atm-field" };
const _hoisted_31 = { class: "atm-row" };
const _hoisted_32 = { class: "atm-field" };
const _hoisted_33 = {
  key: 0,
  class: "atm-field"
};
const _hoisted_34 = {
  key: 1,
  class: "atm-field"
};
const _hoisted_35 = { class: "atm-hint" };
const _hoisted_36 = { class: "atm-field" };
const _hoisted_37 = { class: "atm-modal-foot" };
const _hoisted_38 = ["disabled"];
const _hoisted_39 = {
  key: 5,
  class: "atm-modal"
};
const _hoisted_40 = { class: "atm-modal-box atm-modal-box--wide" };
const _hoisted_41 = { class: "atm-modal-head" };
const _hoisted_42 = { class: "atm-modal-body" };
const _hoisted_43 = {
  key: 0,
  class: "atm-empty"
};
const _hoisted_44 = {
  key: 1,
  class: "atm-alert atm-alert--info"
};
const _hoisted_45 = {
  key: 2,
  class: "atm-table-wrap"
};
const _hoisted_46 = { class: "atm-table" };
const _hoisted_47 = { class: "atm-mono" };
const _hoisted_48 = { class: "atm-sub" };
const _hoisted_49 = { class: "atm-sub" };
const _hoisted_50 = { class: "atm-sub" };
const _hoisted_51 = { class: "atm-result-cell" };
const _hoisted_52 = { key: 0 };
const _hoisted_53 = { class: "atm-result" };
const _hoisted_54 = { key: 1 };
const _hoisted_55 = { class: "atm-modal-foot" };
const _hoisted_56 = {
  key: 6,
  class: "atm-modal"
};
const _hoisted_57 = { class: "atm-modal-box" };
const _hoisted_58 = { class: "atm-modal-head" };
const _hoisted_59 = { class: "atm-modal-body" };
const _hoisted_60 = { class: "atm-modal-foot" };
const _hoisted_61 = ["disabled"];

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
 * 纯 HTML/CSS 实现，不依赖宿主 Vuetify 组件，保证在远程联邦组件上下文中
 * 按钮、开关、弹窗与提示都可用。交互错误由后端返回明确文案。
 */
const props = __props;

const loading = ref(false);
const tasks = ref([]);
const total = ref(0);
const aiAgentEnable = ref(true);
const filterEnabled = ref('');
const busyIds = ref(new Set());
const snackbar = reactive({ show: false, text: '', type: 'info' });

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

/** 触发配置占位提示。 */
const triggerHint = computed(() =>
  editForm.trigger_type === 'cron'
    ? '标准五段 cron 表达式，例如：0 10,22 * * *'
    : '带时区 ISO 8601 时间，例如：2026-12-31 08:00:00',
);

let toastTimer = null;

/** 显示一条自动消失的提示。 */
function showToast(text, type = 'info') {
  if (toastTimer) clearTimeout(toastTimer);
  snackbar.text = text;
  snackbar.type = type;
  snackbar.show = true;
  toastTimer = setTimeout(() => {
    snackbar.show = false;
    toastTimer = null;
  }, 4000);
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
    if (filterEnabled.value === 'true' || filterEnabled.value === 'false') {
      params.enabled = filterEnabled.value;
    }
    const result = await pluginRequest(props.api, props.pluginId, '/tasks', {
      method: 'GET',
      params,
    });
    tasks.value = result?.tasks || [];
    total.value = result?.total || 0;
    aiAgentEnable.value = result?.ai_agent_enable !== false;
  } catch (error) {
    showToast(errorMessage(error, '加载任务列表失败'), 'error');
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
    showToast(result?.message || (value ? '任务已启用' : '任务已停用'), 'success');
  } catch (error) {
    showToast(errorMessage(error, '启停任务失败'), 'error');
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
    showToast(result?.message || '已提交立即执行', 'success');
    await loadTasks();
  } catch (error) {
    showToast(errorMessage(error, '立即执行失败'), 'error');
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
    showToast('任务名称不能为空', 'error');
    return
  }
  if (!editForm.content.trim()) {
    showToast('任务指令不能为空', 'error');
    return
  }
  const body = {
    name: editForm.name.trim(),
    content: editForm.content.trim(),
    trigger_type: editForm.trigger_type,
  };
  if (editForm.trigger_type === 'cron') {
    if (!editForm.cron_expression.trim()) {
      showToast('请填写五段 cron 表达式', 'error');
      return
    }
    body.cron_expression = editForm.cron_expression.trim();
  } else {
    if (!editForm.run_at.trim()) {
      showToast('请填写单次触发时间', 'error');
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
    showToast(result?.message || '任务已更新', 'success');
    editDialog.value = false;
    await loadTasks();
  } catch (error) {
    showToast(errorMessage(error, '保存任务失败'), 'error');
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
    showToast(errorMessage(error, '加载运行历史失败'), 'error');
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
    showToast(result?.message || '任务已删除', 'success');
    deleteDialog.value = false;
    deleteTarget.value = null;
    await loadTasks();
  } catch (error) {
    showToast(errorMessage(error, '删除任务失败'), 'error');
  } finally {
    deleteLoading.value = false;
  }
}

/** 触发来源展示文本。 */
function triggerSourceLabel(source) {
  return source === 'manual' ? '手动' : source === 'scheduled' ? '定时' : source || '未知'
}

onMounted(loadTasks);

return (_ctx, _cache) => {
  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("div", _hoisted_2, [
      _createElementVNode("div", _hoisted_3, [
        _cache[15] || (_cache[15] = _createElementVNode("span", { class: "atm-title-icon" }, "⏰", -1)),
        _cache[16] || (_cache[16] = _createElementVNode("span", null, "Agent 定时任务", -1)),
        _createElementVNode("span", _hoisted_4, _toDisplayString(total.value), 1)
      ]),
      _createElementVNode("button", {
        class: "atm-btn",
        disabled: loading.value,
        onClick: loadTasks
      }, _toDisplayString(loading.value ? '刷新中…' : '刷新'), 9, _hoisted_5)
    ]),
    (!aiAgentEnable.value)
      ? (_openBlock(), _createElementBlock("div", _hoisted_6, " AI Agent 未启用（AI_AGENT_ENABLE=false），自主定时任务不会被调度执行。此处仅能查看和管理任务配置。 "))
      : _createCommentVNode("", true),
    _createElementVNode("div", _hoisted_7, [
      _withDirectives(_createElementVNode("select", {
        "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((filterEnabled).value = $event)),
        class: "atm-select",
        onChange: loadTasks
      }, [...(_cache[17] || (_cache[17] = [
        _createElementVNode("option", { value: "" }, "全部状态", -1),
        _createElementVNode("option", { value: "true" }, "已启用", -1),
        _createElementVNode("option", { value: "false" }, "已停用", -1)
      ]))], 544), [
        [_vModelSelect, filterEnabled.value]
      ])
    ]),
    (loading.value && !hasTasks.value)
      ? (_openBlock(), _createElementBlock("div", _hoisted_8, "正在加载任务列表…"))
      : (!hasTasks.value)
        ? (_openBlock(), _createElementBlock("div", _hoisted_9, " 暂无 Agent 定时任务。新建任务仍通过对话让 Agent 使用 agent_task 工具创建。 "))
        : (_openBlock(), _createElementBlock("div", _hoisted_10, [
            _createElementVNode("table", _hoisted_11, [
              _cache[18] || (_cache[18] = _createElementVNode("thead", null, [
                _createElementVNode("tr", null, [
                  _createElementVNode("th", null, "任务"),
                  _createElementVNode("th", null, "触发"),
                  _createElementVNode("th", null, "最近状态"),
                  _createElementVNode("th", null, "上次运行"),
                  _createElementVNode("th", null, "次数"),
                  _createElementVNode("th", null, "下次运行"),
                  _createElementVNode("th", null, "启用"),
                  _createElementVNode("th", { class: "atm-right" }, "操作")
                ])
              ], -1)),
              _createElementVNode("tbody", null, [
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(tasks.value, (row) => {
                  return (_openBlock(), _createElementBlock("tr", {
                    key: row.id
                  }, [
                    _createElementVNode("td", null, [
                      _createElementVNode("div", _hoisted_12, _toDisplayString(row.name), 1),
                      (row.owner_username || row.owner_user_id)
                        ? (_openBlock(), _createElementBlock("div", _hoisted_13, " 归属：" + _toDisplayString(row.owner_username || row.owner_user_id), 1))
                        : _createCommentVNode("", true),
                      _createElementVNode("div", _hoisted_14, " ID " + _toDisplayString(row.id) + " · " + _toDisplayString(_unref(triggerTypeLabel)(row.trigger_type)), 1)
                    ]),
                    _createElementVNode("td", _hoisted_15, _toDisplayString(_unref(triggerText)(row)), 1),
                    _createElementVNode("td", null, [
                      _createElementVNode("span", {
                        class: _normalizeClass(["atm-badge", `atm-badge--${_unref(statusMeta)(row.last_status).chip}`])
                      }, _toDisplayString(_unref(statusMeta)(row.last_status).label), 3)
                    ]),
                    _createElementVNode("td", _hoisted_16, _toDisplayString(row.last_run_at || '—'), 1),
                    _createElementVNode("td", _hoisted_17, _toDisplayString(row.run_count), 1),
                    _createElementVNode("td", _hoisted_18, _toDisplayString(row.next_run_at || '—'), 1),
                    _createElementVNode("td", null, [
                      _createElementVNode("button", {
                        class: _normalizeClass(["atm-btn atm-btn--sm", row.enabled ? 'atm-btn--on' : 'atm-btn--off']),
                        disabled: busyIds.value.has(row.id),
                        onClick: $event => (onToggle(row, !row.enabled))
                      }, _toDisplayString(busyIds.value.has(row.id) ? '…' : row.enabled ? '停用' : '启用'), 11, _hoisted_19)
                    ]),
                    _createElementVNode("td", _hoisted_20, [
                      _createElementVNode("div", _hoisted_21, [
                        _createElementVNode("button", {
                          class: "atm-btn atm-btn--sm",
                          disabled: busyIds.value.has(row.id),
                          onClick: $event => (onRun(row))
                        }, " 执行 ", 8, _hoisted_22),
                        _createElementVNode("button", {
                          class: "atm-btn atm-btn--sm",
                          disabled: busyIds.value.has(row.id),
                          onClick: $event => (openEdit(row))
                        }, " 编辑 ", 8, _hoisted_23),
                        _createElementVNode("button", {
                          class: "atm-btn atm-btn--sm",
                          onClick: $event => (openHistory(row))
                        }, "历史", 8, _hoisted_24),
                        _createElementVNode("button", {
                          class: "atm-btn atm-btn--sm atm-btn--danger",
                          disabled: busyIds.value.has(row.id),
                          onClick: $event => (openDelete(row))
                        }, " 删除 ", 8, _hoisted_25)
                      ])
                    ])
                  ]))
                }), 128))
              ])
            ])
          ])),
    (editDialog.value)
      ? (_openBlock(), _createElementBlock("div", _hoisted_26, [
          _createElementVNode("div", {
            class: "atm-modal-mask",
            onClick: _cache[1] || (_cache[1] = $event => (editDialog.value = false))
          }),
          _createElementVNode("div", _hoisted_27, [
            _createElementVNode("div", _hoisted_28, [
              _createElementVNode("span", null, "编辑任务 #" + _toDisplayString(editForm.id), 1),
              _createElementVNode("button", {
                class: "atm-close",
                onClick: _cache[2] || (_cache[2] = $event => (editDialog.value = false))
              }, "×")
            ]),
            _createElementVNode("div", _hoisted_29, [
              _createElementVNode("label", _hoisted_30, [
                _cache[19] || (_cache[19] = _createElementVNode("span", null, "任务名称", -1)),
                _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((editForm.name) = $event)),
                  maxlength: "100"
                }, null, 512), [
                  [_vModelText, editForm.name]
                ])
              ]),
              _createElementVNode("div", _hoisted_31, [
                _createElementVNode("label", _hoisted_32, [
                  _cache[21] || (_cache[21] = _createElementVNode("span", null, "触发类型", -1)),
                  _withDirectives(_createElementVNode("select", {
                    "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((editForm.trigger_type) = $event))
                  }, [...(_cache[20] || (_cache[20] = [
                    _createElementVNode("option", { value: "cron" }, "周期（cron）", -1),
                    _createElementVNode("option", { value: "date" }, "单次（date）", -1)
                  ]))], 512), [
                    [_vModelSelect, editForm.trigger_type]
                  ])
                ]),
                (editForm.trigger_type === 'cron')
                  ? (_openBlock(), _createElementBlock("label", _hoisted_33, [
                      _cache[22] || (_cache[22] = _createElementVNode("span", null, "cron 表达式", -1)),
                      _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((editForm.cron_expression) = $event))
                      }, null, 512), [
                        [_vModelText, editForm.cron_expression]
                      ])
                    ]))
                  : (_openBlock(), _createElementBlock("label", _hoisted_34, [
                      _cache[23] || (_cache[23] = _createElementVNode("span", null, "单次触发时间", -1)),
                      _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((editForm.run_at) = $event))
                      }, null, 512), [
                        [_vModelText, editForm.run_at]
                      ])
                    ]))
              ]),
              _createElementVNode("div", _hoisted_35, _toDisplayString(triggerHint.value), 1),
              _createElementVNode("label", _hoisted_36, [
                _cache[24] || (_cache[24] = _createElementVNode("span", null, "任务指令（交给 Agent 执行的完整内容）", -1)),
                _withDirectives(_createElementVNode("textarea", {
                  "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((editForm.content) = $event)),
                  rows: "6",
                  maxlength: "10000"
                }, null, 512), [
                  [_vModelText, editForm.content]
                ])
              ])
            ]),
            _createElementVNode("div", _hoisted_37, [
              _createElementVNode("button", {
                class: "atm-btn",
                onClick: _cache[8] || (_cache[8] = $event => (editDialog.value = false))
              }, "取消"),
              _createElementVNode("button", {
                class: "atm-btn atm-btn--primary",
                disabled: editSaving.value,
                onClick: saveEdit
              }, _toDisplayString(editSaving.value ? '保存中…' : '保存'), 9, _hoisted_38)
            ])
          ])
        ]))
      : _createCommentVNode("", true),
    (historyDialog.value)
      ? (_openBlock(), _createElementBlock("div", _hoisted_39, [
          _createElementVNode("div", {
            class: "atm-modal-mask",
            onClick: _cache[9] || (_cache[9] = $event => (historyDialog.value = false))
          }),
          _createElementVNode("div", _hoisted_40, [
            _createElementVNode("div", _hoisted_41, [
              _createElementVNode("span", null, "运行历史：" + _toDisplayString(historyTask.value?.name || ''), 1),
              _createElementVNode("button", {
                class: "atm-close",
                onClick: _cache[10] || (_cache[10] = $event => (historyDialog.value = false))
              }, "×")
            ]),
            _createElementVNode("div", _hoisted_42, [
              (historyLoading.value)
                ? (_openBlock(), _createElementBlock("div", _hoisted_43, "正在加载运行历史…"))
                : (!historyRuns.value.length)
                  ? (_openBlock(), _createElementBlock("div", _hoisted_44, "暂无运行历史。"))
                  : (_openBlock(), _createElementBlock("div", _hoisted_45, [
                      _createElementVNode("table", _hoisted_46, [
                        _cache[26] || (_cache[26] = _createElementVNode("thead", null, [
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
                              _createElementVNode("td", _hoisted_47, _toDisplayString(run.run_id), 1),
                              _createElementVNode("td", _hoisted_48, _toDisplayString(triggerSourceLabel(run.trigger_source)), 1),
                              _createElementVNode("td", null, [
                                _createElementVNode("span", {
                                  class: _normalizeClass(["atm-badge", `atm-badge--${_unref(statusMeta)(run.status).chip}`])
                                }, _toDisplayString(_unref(statusMeta)(run.status).label), 3)
                              ]),
                              _createElementVNode("td", _hoisted_49, _toDisplayString(run.started_at || '—'), 1),
                              _createElementVNode("td", _hoisted_50, _toDisplayString(run.finished_at || '—'), 1),
                              _createElementVNode("td", _hoisted_51, [
                                (run.result)
                                  ? (_openBlock(), _createElementBlock("details", _hoisted_52, [
                                      _cache[25] || (_cache[25] = _createElementVNode("summary", null, "查看结果", -1)),
                                      _createElementVNode("pre", _hoisted_53, _toDisplayString(run.result), 1)
                                    ]))
                                  : (_openBlock(), _createElementBlock("span", _hoisted_54, "—"))
                              ])
                            ]))
                          }), 128))
                        ])
                      ])
                    ]))
            ]),
            _createElementVNode("div", _hoisted_55, [
              _createElementVNode("button", {
                class: "atm-btn",
                onClick: _cache[11] || (_cache[11] = $event => (historyDialog.value = false))
              }, "关闭")
            ])
          ])
        ]))
      : _createCommentVNode("", true),
    (deleteDialog.value)
      ? (_openBlock(), _createElementBlock("div", _hoisted_56, [
          _createElementVNode("div", {
            class: "atm-modal-mask",
            onClick: _cache[12] || (_cache[12] = $event => (deleteDialog.value = false))
          }),
          _createElementVNode("div", _hoisted_57, [
            _createElementVNode("div", _hoisted_58, [
              _cache[27] || (_cache[27] = _createElementVNode("span", null, "删除任务", -1)),
              _createElementVNode("button", {
                class: "atm-close",
                onClick: _cache[13] || (_cache[13] = $event => (deleteDialog.value = false))
              }, "×")
            ]),
            _createElementVNode("div", _hoisted_59, " 确定要删除任务「" + _toDisplayString(deleteTarget.value?.name || '') + "」（#" + _toDisplayString(deleteTarget.value?.id || '') + "）吗？ 删除会一并清除其全部运行历史，且不可恢复。 ", 1),
            _createElementVNode("div", _hoisted_60, [
              _createElementVNode("button", {
                class: "atm-btn",
                onClick: _cache[14] || (_cache[14] = $event => (deleteDialog.value = false))
              }, "取消"),
              _createElementVNode("button", {
                class: "atm-btn atm-btn--danger",
                disabled: deleteLoading.value,
                onClick: confirmDelete
              }, _toDisplayString(deleteLoading.value ? '删除中…' : '删除'), 9, _hoisted_61)
            ])
          ])
        ]))
      : _createCommentVNode("", true),
    _createVNode(_Transition, { name: "atm-toast-fade" }, {
      default: _withCtx(() => [
        (snackbar.show)
          ? (_openBlock(), _createElementBlock("div", {
              key: 0,
              class: _normalizeClass(["atm-toast", `atm-toast--${snackbar.type}`])
            }, _toDisplayString(snackbar.text), 3))
          : _createCommentVNode("", true)
      ]),
      _: 1
    })
  ]))
}
}

};
const Page = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-35a02d1e"]]);

export { Page as default };
