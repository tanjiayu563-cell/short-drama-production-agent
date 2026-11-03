# MiniMax H3 本地 API 闭环

## 1. 目标

把已确认的单镜提示词提交给 MiniMax H3，自动轮询任务并在完成后下载视频。API Key 只保存在本地环境变量，不进入浏览器、项目 JSON、提示词或日志。

## 2. 经济默认值

- 模型：`MiniMax-H3`
- 时长：`4` 秒（H3 最小值附近，后续剪辑取 2 秒）
- 分辨率：`768P`
- 画幅：`9:16`
- 每次只生成当前已确认的单镜
- 不自动批量提交
- 参考图上传暂不纳入首版 T2V 调用

2K、更长时长和批量生成必须由用户明确修改。

## 3. 本地启动

不要把 API Key 发到聊天或写进 HTML。

```bash
export MINIMAX_API_KEY="..."
python3 skill/scripts/local_server.py --port 8787
```

然后打开：

```text
http://127.0.0.1:8787/workbench/index.html
```

健康检查：

```bash
curl http://127.0.0.1:8787/api/health
```

## 4. 调用流程

```text
工作台生成当前镜提示词
        ↓
用户确认人物、场景、时长、画幅和提示词
        ↓
浏览器 POST /api/generate
        ↓
本地服务读取 MINIMAX_API_KEY
        ↓
MiniMax H3 提交任务
        ↓
浏览器轮询 /api/jobs/{task_id}
        ↓
成功后下载 MP4
        ↓
工作台显示视频并记录任务
```

## 5. 安全边界

- 服务只绑定 `127.0.0.1`；
- 不把 Key 写入前端；
- 不把完整提示词打印到服务器日志；
- 本地服务不代替版权、隐私、肖像或平台审核；
- 生成结果仍需质检，不得因为 API 返回成功就判定可用；
- 2 秒成片镜头应生成 4 秒后剪辑，不能假设模型能直接输出 2 秒。

## 6. API 依据

MiniMax 官方视频生成文档：

- https://platform.minimax.io/docs/guides/video-generation.md
- https://platform.minimax.io/docs/guides/models-intro.md

接口路径以官方当前版本为准；本实现使用：

- `POST /v2/video_generation`
- `GET /v2/query/video_generation/{task_id}`

如果官方接口变化，先更新 `scripts/minimax_h3_client.py`，不要在工作台里硬编码另一套协议。

## 7. 首测建议

首轮只测试一个镜头：

- 4 秒；
- 768P；
- 9:16；
- 一个动作；
- 一个场景；
- 一个或两个角色；
- 不含精确屏幕文字、复杂手部、长对白和危险特技。

通过后再增加镜头，不要一开始批量消耗额度。
