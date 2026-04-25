---
name: fangxin-image-gen
description: AI image generation and image editing via fangxinapi.com using gpt-image-2. Supports text-to-image, image-to-image, multi-image composite edits, masks, PNG/JPEG output, and quality/background controls. Use when the user wants to generate images, edit uploaded images, merge multiple reference photos, or create illustrations. Triggered by phrases like "画一张", "生成图片", "改图", "合成照片", "draw", "generate image", "edit image", "image to image".
---

# Fangxin Image Generation

v1.5.0

## ⚠️ Agent 必读约束

### 🌐 Base URL

```
https://fangxinapi.com
```

所有图片接口请求必须使用此 Base URL，不要使用 `fangxin.com` / `fangxin.ai` / `fxapi.com` 或其他仿写域名。

统一入口脚本：`~/.claude/skills/fangxin-image-gen/scripts/generate.py`，脚本会自动路由到下面两个端点，**不要手拼 URL 去调用**：

- 文生图 → `POST /v1/images/generations`（未传 `--image`）
- 图片编辑 / 多图合成 → `POST /v1/images/edits`（传了一张或多张 `--image`）

### 🔑 认证

环境变量：

- `FANGXIN_API_KEY` — Bearer token（格式 `sk-xxxxxxxx`，必填）
- `FANGXIN_MODEL` — 模型名（默认 `gpt-image-2`，可选）

读取顺序：shell 中已 `export` 的值优先；其次脚本启动时自动从 `~/.claude/skills/fangxin-image-gen/.env` 加载（不覆盖已有环境变量）。

**每次调用 `generate.py` 前先检查 `$FANGXIN_API_KEY` 是否存在**。若不存在或为空，提示用户按下面流程完成配置，配置完成后再继续执行用户原本的请求：

1. 前往 https://fangxinapi.com 注册并创建 API Key。
2. **优先选用 `AZ` 分组下的 key**，出图稳定性明显更好；其他分组容易超时或连接中断。
3. 将 key 写入 `~/.claude/skills/fangxin-image-gen/.env`，格式：`FANGXIN_API_KEY=sk-xxxxxxxx`。
4. 将文件权限收紧到 `600`。

```bash
mkdir -p ~/.claude/skills/fangxin-image-gen
touch ~/.claude/skills/fangxin-image-gen/.env
chmod 600 ~/.claude/skills/fangxin-image-gen/.env
# 然后用任意编辑器写入：FANGXIN_API_KEY=sk-xxxxxxxx
```

写入后无需重启 shell，下一次调用 `generate.py` 会自动加载。

### 🛟 用户在对话里贴出 key 时的处理流程

如果用户直接在对话里发出一段形如 `sk-xxxxxxxx` 的 key，**不要原样回显或长期保留在对话中**。按以下步骤执行：

1. 立刻把 key 写入 `.env`，覆盖或新增 `FANGXIN_API_KEY` 这一行；文件不存在则创建并 `chmod 600`：

```bash
ENV_FILE=~/.claude/skills/fangxin-image-gen/.env
mkdir -p "$(dirname "$ENV_FILE")"
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"
# KEY 通过环境变量传入，避免出现在 ps / shell history 中
FANGXIN_API_KEY="<paste-here>" awk -v k="FANGXIN_API_KEY" -v v="$FANGXIN_API_KEY" '
  BEGIN{found=0}
  $0 ~ "^"k"=" {print k"="v; found=1; next}
  {print}
  END{if(!found) print k"="v}
' "$ENV_FILE" > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"
```

2. 写入成功后用一句话告诉用户：「已保存到 `~/.claude/skills/fangxin-image-gen/.env`，下次可直接使用；以后不要将 key 贴在聊天里，可能被日志或其他工具收录。」
3. 回复中不要复述完整 key，最多展示前 4 位 + `...` + 后 4 位用于确认。
4. 随即继续执行用户原本的图片生成请求。

### ⏳ 出图耗时与重试

`gpt-image-2` 在高质量 / 2K / 4K 尺寸下单张耗时可能达到 30～120 秒，多图编辑更久。调用脚本时：

- **不要提前中断**；脚本已设 `--max-time 420` 并内置重试，耐心等到脚本返回即可。
- 遇到 `Empty reply from server` / `Connection reset by peer` / `SSL_ERROR_SYSCALL` 之类报错属于上游问题，脚本会自动重试，**不要主动改参数抢跑**。
- 用户催问「怎么还没出」时，回复正常等待状态而不是重启任务。
- 反复超时且当前不是 AZ 分组的 key，提醒用户到控制台切换到 AZ 分组的 key 后重试。

### 🔒 安全规则

- `.env` 文件权限必须是 `600`，且已加入 `.gitignore`，**不要 commit 到任何仓库**。
- 不要在 stdout / stderr / 日志中输出完整 key 或 `Authorization` 请求头。
- 不要将 key 作为命令行参数传递（会出现在 `ps` 和 shell 历史中），统一通过环境变量或 `.env` 注入。
- 在对话里复述 key 时，最多展示前 4 位 + `...` + 后 4 位。
- 用户怀疑 key 泄露时，提醒他到 https://fangxinapi.com 控制台撤销后重新创建。

### 💡 模型选择

默认且强烈推荐使用 `gpt-image-2`，除非用户明确要求其他模型。`dall-e-3` 等模型不支持本 skill 的部分参数（如 `background` / `output_format`）。

## Supported Sizes

- `1024x1024` — 正方形
- `1536x1024` — 横版
- `1024x1536` — 竖版
- `2048x2048` — 2K 正方形
- `2048x1152` — 2K 横版
- `3840x2160` — 4K 横版
- `2160x3840` — 4K 竖版
- `auto` — 让模型自行决定

## Usage

### Text to image

```bash
python3 ~/.claude/skills/fangxin-image-gen/scripts/generate.py \
  --prompt "your prompt here" \
  [--model gpt-image-2] \
  [--size 1024x1024] \
  [--n 1] \
  [--quality auto] \
  [--background auto] \
  [--output-format png] \
  [--output-compression 100] \
  [--moderation auto] \
  [--outdir ./tmp/fangxin-image-gen-output] \
  [--retries 3]
```

### Image edit / image-to-image / multi-image merge

```bash
python3 ~/.claude/skills/fangxin-image-gen/scripts/generate.py \
  --prompt "combine both people into one photo" \
  --image /path/to/photo-1.png \
  --image /path/to/photo-2.png \
  [--mask /path/to/mask.png] \
  [--input-fidelity high] \
  [--model gpt-image-2] \
  [--size 1024x1024] \
  [--quality high] \
  [--output-format png] \
  [--outdir ./tmp/fangxin-image-gen-output] \
  [--retries 3]
```

`--image` accepts either local file paths or remote URLs. Repeat `--image` to pass multiple references in one request.

When a URL is provided, the script downloads it to a temporary file under `/tmp`, calls the Fangxin edit endpoint with file uploads, then deletes the temporary file after the request completes. This avoids keeping long-lived copies on your server while still working around Fangxin's lack of direct URL support for edits.

## Parameters

| Param | Default | Notes |
|-------|---------|-------|
| `--prompt` | required | Image description or edit instruction |
| `--model` | `gpt-image-2` | Default and preferred model on this provider |
| `--image` | none | Reference image path or URL. URLs are downloaded to temp files automatically |
| `--mask` | none | Optional mask path or URL for edit mode |
| `--input-fidelity` | `high` | Edit-mode fidelity to the source images: `high` or `low` |
| `--size` | `auto` | Output size: `auto`, `1024x1024`, `1536x1024`, `1024x1536`, `2048x2048`, `2048x1152`, `3840x2160`, `2160x3840` |
| `--n` | `1` | Number of output images |
| `--quality` | `auto` | Quality level: `auto`, `high`, `medium`, `low` |
| `--background` | `auto` | Background: `auto`, `transparent`, `opaque` |
| `--output-format` | `png` | Supported on this provider: `png`, `jpeg` |
| `--output-compression` | `100` | Compression level 0-100 |
| `--moderation` | `auto` | Content moderation: `auto`, `low` |
| `--style` | none | Only for `dall-e-3`; not supported for `gpt-image-2` |
| `--user` | none | Optional end-user identifier |
| `--outdir` | `./tmp/fangxin-image-gen-output` | Output directory **relative to the current working directory** by default, so users can find files next to the project they are working on. Pass an absolute path to override. |
| `--retries` | `3` | Retry count when the provider closes the connection or drops TLS |

## Request Routing

The script now routes automatically based on inputs:

- No `--image`: uses `POST /v1/images/generations`
- One or more `--image`: uses `POST /v1/images/edits`
- `--mask` is only meaningful in edit mode

This gives one unified skill for the full image workflow.

## Tested Provider Differences

Compared with the standard OpenAI image API behavior, this provider differs in a few important ways:

- `response_format` is **not** accepted.
- Successful `gpt-image-2` responses return `data[].b64_json`, not image URLs.
- `output_format=webp` is **not** supported by the provider validation. Only `png` and `jpeg` are accepted.
- `style` is rejected as an unknown parameter for `gpt-image-2`.
- The script uses `curl --http1.1` because direct `urllib` requests were observed to disconnect on this endpoint.
- For image edits, this provider expects multipart form uploads and accepts repeated `image` fields for multi-image requests.
- Direct remote URL references were not accepted reliably by the provider, so the script converts URLs into temporary local files before upload.
- `images[]` and `images[0]` style multipart fields were tested and did **not** work on this provider.

## Model Priority

Always use `gpt-image-2` unless the user explicitly requests a different model by name.

## Output Format

脚本会把保存路径解析为**绝对路径**后再输出，这样不论从哪个 CWD 运行，用户都能直接复制路径打开文件。输出示例（假设 CWD 是 `/Users/me/proj`）：

```text
mode=edit | model=gpt-image-2 | inputs=2 | size=1024x1024 | quality=high | format=png | n=1 | time=42.1s

[1/1] /Users/me/proj/tmp/fangxin-image-gen-output/image_....png
      revised_prompt: ...
```

运行完后向用户呈现结果时，**保留这个绝对路径**，不要手工裁成 `./tmp/...`。另外可以额外补一句「默认出图目录是当前工作目录下的 `tmp/fangxin-image-gen-output/`，要改位置传 `--outdir`。」供用户快速定位：

```text
模式: edit | 模型: gpt-image-2 | 输入图: 2 | 尺寸: 1024x1024 | 质量: high | 格式: png | 耗时: 42.1s

生成文件: /Users/me/proj/tmp/fangxin-image-gen-output/image_....png
说明: 默认保存到当前工作目录下的 tmp/fangxin-image-gen-output/
```

If `revised_prompt` is present, show it as a note so the user knows the API adjusted their prompt.

## Workflow

1. Check `FANGXIN_API_KEY`：脚本启动时已自动加载 `~/.claude/skills/fangxin-image-gen/.env`。如果仍为空，按上文「🔑 认证」引导用户；如果用户已经把 key 直接粘贴进对话，按「🛟 用户在对话里贴出 key 时的处理流程」自动写入 `.env` 后再继续。
2. If the user only gives text, run generation mode.
3. If the user provides one or more images, run edit mode with repeated `--image` flags.
4. If an image input is a URL, download it to a temp file first and clean it up after the request.
5. Build the command from the user's request.
6. Run the script and capture stdout/stderr.
7. Parse the summary line and each `[i/n] path` line from stdout.
8. Present a clean result block with metadata plus saved file paths.
9. If the script exits non-zero, show the stderr error to the user.

## Reusing Old Images

If a user wants to regenerate from an older image, they do **not** need to upload it manually again as long as they still have one of these:

- The original image URL
- The saved local file path from a previous generation result
- A durable object-storage URL you issued for the image

Recommended practice:

- For transient processing: pass image URLs and let the script download to `/tmp` and clean up automatically
- For repeatable workflows: store the original source URLs or the final generated image URLs/paths in your application database, then feed them back into `--image` later
