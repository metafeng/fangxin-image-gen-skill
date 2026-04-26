# fangxin-image-gen

面向 Claude Code、Codex、OpenClaw、Hermes 等 agent 的图片生成 Skill，封装了 [放心 API](https://fangxinapi.com) 的 `gpt-image-2` 接口，支持文生图、改图、多图合成和 URL 引图。

当前版本：`v1.6.1`

## 这版更新了什么

- 不再假设 Skill 一定安装在 `~/.claude/...`，脚本会根据当前安装副本自动解析 `<skill-root>`
- 支持主备 key 顺序切换：`FANGXIN_API_KEY`、`FANGXIN_API_KEY1`、`FANGXIN_API_KEY2` ...
- 支持用 `FANGXIN_ENV_FILE` 指向共享 `.env`
- 默认输出目录仍是当前工作目录下的 `./tmp/fangxin-image-gen-output`
- 已在 OpenClaw 实测通过

## 仓库结构

```text
fangxin-image-gen/
├── README.md
├── SKILL.md
├── agents/openai.yaml
├── scripts/generate.py
├── fangxin-image-gen.zip
└── .gitignore
```

## 配置

先准备放心 API key，建议优先使用 `AZ` 分组。

把 key 写进当前 Skill 安装副本的 `.env`：

```bash
SKILL_ROOT=/path/to/fangxin-image-gen
mkdir -p "$SKILL_ROOT"
touch "$SKILL_ROOT/.env"
chmod 600 "$SKILL_ROOT/.env"
```

最少写一行：

```bash
FANGXIN_API_KEY=sk-xxxxxxxx
```

如果要自动主备切换，可以写成：

```bash
FANGXIN_API_KEY=sk-primary
FANGXIN_API_KEY1=sk-backup-1
FANGXIN_API_KEY2=sk-backup-2
```

如果多个 agent 要共用同一份配置，可以额外设置：

```bash
FANGXIN_ENV_FILE=/absolute/path/to/shared-fangxin.env
```

读取顺序是：

1. 当前 shell 已导出的环境变量
2. `FANGXIN_ENV_FILE` 指定的 `.env`
3. 当前 skill 根目录下的 `.env`

## 安装

这个仓库根目录就是 Skill 本体，直接 clone 到你的 skills 目录即可：

```bash
git clone https://github.com/metafeng/fangxin-image-gen.git /path/to/skills/fangxin-image-gen
```

适配的安装路径可以是：

- Claude Code / Codex：各自 skills 目录下的 `fangxin-image-gen/`
- OpenClaw：任意被 skill 扫描到的目录
- Hermes：任意被 Hermes skill/gateway 配置加载的目录

关键点只有一个：`SKILL.md`、`agents/`、`scripts/` 这几个文件夹要保持同级。

## 用法

### 文生图

```bash
python3 /path/to/fangxin-image-gen/scripts/generate.py \
  --prompt "一只在月亮上钓鱼的猫，水彩风" \
  --size 1024x1536 \
  --quality high
```

### 改图 / 多图合成

```bash
python3 /path/to/fangxin-image-gen/scripts/generate.py \
  --prompt "combine both people into one natural portrait" \
  --image /path/to/a.png \
  --image /path/to/b.png \
  --size 1024x1024 \
  --quality high
```

也可以把 URL 直接传给 `--image`；脚本会先下载到临时目录，再上传给编辑接口。

## 输出位置

默认输出目录是：

```text
./tmp/fangxin-image-gen-output
```

这是相对于你发起命令时的当前工作目录，不是固定写死到 `/tmp`。如果想改位置，传 `--outdir /absolute/path`。

## 注意事项

- 默认并强烈建议使用 `gpt-image-2`
- 输出格式只支持 `png` / `jpeg`
- `gpt-image-2` 常见耗时 30 到 120 秒，高质量和多图编辑会更久
- `401` / `403` / `429` / `5xx` / 超时 / 连接中断时，脚本会自动切换到下一个 key
- `.env` 已加入 `.gitignore`，不要把 key 提交到仓库

## 更新

```bash
cd /path/to/skills/fangxin-image-gen
git pull
```

## 反馈

问题和改进建议请提到 [Issues](https://github.com/metafeng/fangxin-image-gen/issues)。
