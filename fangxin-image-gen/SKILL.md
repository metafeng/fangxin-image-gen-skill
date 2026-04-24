---
name: fangxin-image-gen
description: AI image generation and image editing via fangxinapi.com using gpt-image-2. Supports text-to-image, image-to-image, multi-image composite edits, masks, PNG/JPEG output, and quality/background controls. Use when the user wants to generate images, edit uploaded images, merge multiple reference photos, or create illustrations. Triggered by phrases like "画一张", "生成图片", "改图", "合成照片", "draw", "generate image", "edit image", "image to image".
---

# Fangxin Image Generation

## Configuration

Read API key and model from environment variables:

- `FANGXIN_API_KEY` — Bearer token (required; no default is bundled in the skill)
- `FANGXIN_MODEL` — model name (default: `gpt-image-2`)

## Supported Sizes

- `1024x1024` — 正方形
- `1536x1024` — 横版
- `1024x1536` — 竖版
- `2048x2048` — 2K 正方形
- `2048x1152` — 2K 横版
- `3840x2160` — 4K 横版
- `2160x3840` — 4K 竖版
- `auto` — 让模型自行决定

If `FANGXIN_API_KEY` is not set, tell the user to configure it:
```
/update-config set FANGXIN_API_KEY=<your-key>
```

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
  [--outdir /tmp/fangxin-image-gen-output] \
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
  [--outdir /tmp/fangxin-image-gen-output] \
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
| `--outdir` | `/tmp/fangxin-image-gen-output` | Directory where decoded image files are saved |
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

The script prints a summary line followed by each saved image path:

```text
mode=edit | model=gpt-image-2 | inputs=2 | size=1024x1024 | quality=high | format=png | n=1 | time=42.1s

[1/1] /tmp/fangxin-image-gen-output/image_....png
      revised_prompt: ...
```

After running, present results to the user like this:

```text
模式: edit | 模型: gpt-image-2 | 输入图: 2 | 尺寸: 1024x1024 | 质量: high | 格式: png | 耗时: 42.1s

生成文件: /tmp/fangxin-image-gen-output/image_....png
```

If `revised_prompt` is present, show it as a note so the user knows the API adjusted their prompt.

## Workflow

1. Check `FANGXIN_API_KEY` is set.
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
