# fangxin-image-gen

一个面向 Claude Skills / Codex 的中文图片生成 Skill，基于 [放心 API](https://fangxinapi.com) 的 `gpt-image-2` 接口封装。一句话：**让 AI 帮你画图、改图、合图，配置 5 分钟搞定。**

当前版本：**v1.5.0**

支持的玩法：

- 用一段文字直接出一张图
- 拿一张图改风格、改背景、改细节
- 把两张甚至多张图合成一张（比如两个人合一张合影）
- 参考一张图片 URL，不用先下到本地

## 仓库长什么样

仓库根目录就是 Skill 本身，clone 下来直接放进 Claude skills 目录就能用：

```text
fangxin-image-gen/          # 仓库根 = Skill 本体
├── README.md               # 你正在看的这个（GitHub 文档）
├── SKILL.md                # 给 AI 看的说明书（Skill 入口）
├── agents/openai.yaml      # Agent 元信息
├── scripts/generate.py     # 实际干活的脚本
├── fangxin-image-gen.zip   # 打包好的版本，方便离线分发
└── .gitignore              # 已忽略 .env / .DS_Store / __pycache__
```

## 三步用起来

### 第 1 步：拿一个放心 API 的 key

1. 打开 https://fangxinapi.com 注册 / 登录。
2. 在控制台创建 API Key（一串以 `sk-` 开头的字符）。
3. **建议优先使用 `AZ` 分组下面的 key**，出图稳定性明显更好；其他分组容易超时或者中途断连。

### 第 2 步：把 key 写进 `.env`

Skill 会自动读这个文件，**不需要改 `~/.zshrc`，也不需要重启终端**：

```bash
mkdir -p ~/.claude/skills/fangxin-image-gen
touch ~/.claude/skills/fangxin-image-gen/.env
chmod 600 ~/.claude/skills/fangxin-image-gen/.env
```

然后用任意编辑器把下面这一行写进去（替换成你自己的 key）：

```
FANGXIN_API_KEY=sk-xxxxxxxx
```

写完保存，下次调用脚本就会自动加载。

> 不小心把 key 贴在对话窗口里？没关系，Skill 内置一段流程：AI 会自动帮你写到 `.env`、把权限收紧到 600，并提醒你以后别再贴。**但还是建议从一开始就在编辑器里写，别经过聊天**。

### 第 3 步：装 Skill

仓库扁平化之后安装很简单，二选一：

**方式 A：直接 clone 到 Skills 目录（推荐，更新一行命令）**

```bash
git clone https://github.com/metafeng/fangxin-image-gen.git \
  ~/.claude/skills/fangxin-image-gen
```

以后想更新只要 `cd ~/.claude/skills/fangxin-image-gen && git pull` 即可。

**方式 B：解压打包好的 zip**

下载 `fangxin-image-gen.zip`，解压后会得到一个 `fangxin-image-gen/` 文件夹，把它整个拷到 `~/.claude/skills/` 下面。

装好后重启一下 Claude / Codex，让它读到新 Skill。

> Claude 加载 Skill 时只看 `SKILL.md` + `agents/` + `scripts/`，仓库根的 `README.md` / `.git/` / `.gitignore` 会被自动忽略，不影响运行。

## 怎么用

装好之后直接用大白话描述你想要什么，AI 会自己挑接口、配参数。下面是一些示例。

### 文生图（只有文字）

> 「画一张极简风格的红色纸飞机海报，奶油色背景」
> 「做一张科技感很强的产品发布会主视觉」
> 「给我一张适合公众号封面的插画」

### 改图（你给一张图）

> 「把这张图改成商业海报风格」
> 「保持人物不变，背景换成摄影棚」
> 「保留原构图，整体改成时尚杂志风」

### 合图（你给两张或多张图）

> 「把这两个人合成一张自然的合影」
> 「把第一张的脸放到第二张的场景里」
> 「参考这几张产品图，生成一张新的品牌主视觉」

### 给 URL 也行

> 「用这个链接里的图片重生成一版海报：https://...」
> 「把这两个 URL 的人物合成合影」

Skill 会先把远程图片下载到 `/tmp`，调用完接口立刻删掉，**不会在你的服务器上堆图**。

## 出图要等多久？

简单说：**有点慢，请耐心**。

- 单张图常规耗时 30～120 秒，2K / 4K 或高质量参数可能更久
- 多图编辑还会再久一些
- 脚本已经设了 7 分钟超时和自动重试，**不要中途取消**
- 看到 `Empty reply from server` / `Connection reset by peer` 这种报错是上游问题，脚本会自己重试，不用慌
- 反复超时？检查一下你用的是不是 `AZ` 分组的 key，不是的话切过去再试

## 支持的尺寸

| 尺寸 | 说明 |
|------|------|
| `1024x1024` | 正方形 |
| `1536x1024` | 横版 |
| `1024x1536` | 竖版 |
| `2048x2048` | 2K 正方形 |
| `2048x1152` | 2K 横版 |
| `3840x2160` | 4K 横版 |
| `2160x3840` | 4K 竖版 |
| `auto` | 让模型自己决定 |

## 主要参数（AI 一般会自动填，自己跑脚本时才用得到）

- `--prompt`：提示词（必填）
- `--image`：参考图，可重复多次传多张
- `--mask`：局部编辑用的遮罩图
- `--input-fidelity`：`high`（更像原图）/ `low`（更自由）
- `--size`：尺寸，见上表
- `--quality`：`auto` / `high` / `medium` / `low`
- `--output-format`：`png` / `jpeg`（上游不支持 webp）
- `--outdir`：图片输出目录，默认 `./tmp/fangxin-image-gen-output`（**相对于你当前的工作目录**），这样出图会出现在你正在干活的项目里、一眼就能看到；想存到别的地方，传个绝对路径即可

直接命令行跑的话长这样：

```bash
python3 ~/.claude/skills/fangxin-image-gen/scripts/generate.py \
  --prompt "一只在月亮上钓鱼的猫，水彩风" \
  --size 1024x1536 \
  --quality high
```

## 复用以前生成的图

不需要重新上传原图，只要你还有下面任一引用就行：

- 原始图片 URL
- 上次生成的本地文件路径（默认在当时工作目录的 `tmp/fangxin-image-gen-output/` 下面）
- 你自己业务系统里存的图片地址

直接把这些当 `--image` 参数传进去就 OK。

## 一些"踩过的坑"提醒

- 上游 `gpt-image-2` 返回的是 `b64_json`，**不是 URL**，脚本会自己解码保存
- 不接受 `response_format` 参数，传了会报错
- 不接受 `webp` 输出，只能 `png` 或 `jpeg`
- 编辑接口对"直接传远程 URL"兼容性差，所以脚本会先下载到 `/tmp` 再上传
- 用的是 `curl --http1.1`，因为 HTTP/2 在这家上游偶尔断流
- key 一定要走 `AZ` 分组，其他分组稳定性明显差一截

## 安全约定

- `.env` 已经加进 `.gitignore`，不会被误推到 GitHub
- 建议把 `.env` 权限设成 `600`，只让自己读写
- 别把 key 贴在 Issue、PR、聊天截图里
- 如果不小心泄露了，立刻去放心 API 控制台撤销并换一个

## 反馈

发现 bug 或者想加新能力，欢迎在 [Issues](https://github.com/metafeng/fangxin-image-gen/issues) 里提。
