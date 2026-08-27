# 订阅提醒 (SubscribeReminder)

MoviePilot V3 插件 — 每天定时推送当天有更新的订阅内容。

## 功能

- 电视剧：遍历订阅 → TMDB 拉季内剧集 → 筛 air_date==今天 → 推送「📺 剧名 SxxEyy」
- 电影：recognize_media 识别 → release_date==今天 → 推送「📽 剧名」
- 每 8 条分批发消息，带随机封面图

## 配置项

| 字段 | 说明 | 默认值 |
|------|------|--------|
| enabled | 启用插件 | False |
| onlyonce | 立即运行一次 | False |
| time | 推送时间（小时） | 9 |
| subtype | 订阅类型（movie/tv） | ["movie", "tv"] |
| msgtype | 消息类型 | Plugin |

## 安装

将 `plugins.v3/subscribereminder/` 复制到 MoviePilot 插件目录，或从市场安装。

## 开发

```bash
# 编译检查
python -m compileall plugins.v3/subscribereminder

# 运行测试
pytest tests/v3/subscribereminder
```

## 版本历史

- v1.0.0: 适配 MoviePilot V3
