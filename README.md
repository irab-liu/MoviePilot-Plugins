# MoviePilot V3 插件仓库

本仓库包含多个适用于 MoviePilot V3 的插件。

---

## 📦 插件列表

### 1. 猫眼热度榜 (MaoyanDianYing)

**版本**：v1.1.0

**描述**：猫眼网播【电视剧+网剧】热度 TOP30 剧集订阅情况，一键订阅。

**功能**：
- 自动抓取猫眼网播热度 TOP30 剧集
- 展示 TMDB 海报和演员信息
- 支持一键订阅功能
- 支持定时自动刷新（可配置间隔）
- 详情页展示订阅/入库状态

**配置**：
- 启用/禁用插件
- 自动刷新间隔（1/2/3/6/12/24 小时）

---

### 2. 猫眼TOP30探索 (MaoyanTop30)

**版本**：v1.1.1

**描述**：让探索支持猫眼电视剧-top30，思路来源于 DDSRem 大佬的项目实现。

**数据链路**：猫眼榜单 → TMDB 搜索获取 ID 和海报 → MediaInfo → MoviePilot 探索 → 原生详情页

**功能**：
- 将猫眼网播热度榜作为探索数据源
- 通过 TMDB 搜索获取标准媒体身份
- 注册为 MoviePilot 探索数据源
- 支持在探索页面浏览猫眼 TOP30 剧集
- 支持定时自动刷新（可配置间隔）

**配置**：
- 启用/禁用插件
- 自动刷新间隔（1/2/3/6/12/24 小时）

---

### 3. 订阅提醒v3 (IrabSubscribeReminder)

**版本**：v1.0.7

**描述**：推送当天订阅更新内容。（v3兼容版）

**功能**：
- 自动推送当天订阅剧集更新
- 详情页以表格形式展示更新内容（序号/类型/名称/更新集数）

---

## 📥 安装方式

1. 在 MoviePilot 后台 → 插件市场 → 搜索插件名称
2. 点击安装并配置

或手动下载 Release 包上传安装。

---

## 📋 版本历史

### MaoyanDianYing
- v1.1.0：新增海报点击打开媒体详情页功能
- v1.0.6：修复媒体库状态检查异常处理，增强日志诊断
- v1.0.0：首次发布

### MaoyanTop30
- v1.1.1：重构插件结构和数据链路文档
- v1.0.3：增加定时自动刷新功能，可配置刷新间隔
- v1.0.0：首次发布

### IrabSubscribeReminder
- v1.0.7：详情页改为表格形式：序号/类型/名称/更新集数

---

## 🔗 下载链接

- [MaoyanDianYing v1.1.0](https://github.com/irab-liu/MoviePilot-Plugins/releases/tag/MaoyanDianYing_v1.1.0)
- [MaoyanTop30 v1.1.1](https://github.com/irab-liu/MoviePilot-Plugins/releases/tag/MaoyanTop30_v1.1.1)
- [IrabSubscribeReminder v1.0.7](https://github.com/irab-liu/MoviePilot-Plugins/releases/tag/IrabSubscribeReminder_v1.0.7)

---

## 📝 作者

**irab** - [GitHub](https://github.com/irab-liu)
