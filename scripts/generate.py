#!/usr/bin/env python3
import argparse
import base64
import json
import mimetypes
import os
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

GENERATIONS_API_URL = "https://fangxinapi.com/v1/images/generations"
EDITS_API_URL = "https://fangxinapi.com/v1/images/edits"
DEFAULT_MODEL = "gpt-image-2"
REQUEST_TIMEOUT_SECONDS = 420
DOTENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _load_dotenv():
    """Load KEY=VALUE pairs from <skill>/.env into os.environ if not already set.

    Shell-exported values always win; .env only fills in what's missing so users
    can keep a per-skill config file without polluting their global shell.
    """
    if not DOTENV_PATH.is_file():
        return
    try:
        for raw_line in DOTENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


_load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Generate or edit images via fangxinapi.com (OpenAI-compatible)"
    )
    parser.add_argument("--prompt", required=True, help="Image prompt (max 32000 chars for GPT models)")
    parser.add_argument("--model", default=None, help=f"Model name (default: {DEFAULT_MODEL})")
    parser.add_argument(
        "--size",
        default="auto",
        help="Image size: auto, 1024x1024, 1536x1024, 1024x1536, 2048x2048, 2048x1152, 3840x2160, 2160x3840",
    )
    parser.add_argument("--n", type=int, default=1, help="Number of images (1-10, dall-e-3 only supports 1)")
    parser.add_argument("--quality", default="auto", help="Quality: auto, high, medium, low (GPT); hd, standard (dall-e-3)")
    parser.add_argument("--background", default="auto", help="Background: auto, transparent, opaque (GPT models only)")
    parser.add_argument("--output-format", default="png", help="Output format: png, jpeg")
    parser.add_argument("--output-compression", type=int, default=100, help="Compression 0-100%%")
    parser.add_argument("--moderation", default="auto", help="Content moderation: auto, low (GPT models only)")
    parser.add_argument("--style", default=None, help="Style: vivid, natural (dall-e-3 only)")
    parser.add_argument(
        "--outdir",
        default="./tmp/fangxin-image-gen-output",
        help="Directory to save decoded images. Default is relative to the current working "
        "directory so users can find files easily; pass an absolute path to override.",
    )
    parser.add_argument("--retries", type=int, default=3, help="Retry count when the provider closes the connection")
    parser.add_argument("--image", action="append", default=[], help="Reference image path or URL. Repeat for multiple images.")
    parser.add_argument("--mask", default=None, help="Optional mask image path or URL for edit mode")
    parser.add_argument("--input-fidelity", default="high", choices=["high", "low"], help="How closely edit mode follows the input image(s)")
    parser.add_argument("--user", default=None, help="Optional end-user identifier")
    args = parser.parse_args()

    api_key = os.environ.get("FANGXIN_API_KEY", "").strip()
    if not api_key:
        print("Error: FANGXIN_API_KEY is not set.", file=sys.stderr)
        print(
            "Get a key at https://fangxinapi.com, then save it to:",
            file=sys.stderr,
        )
        print(f"  {DOTENV_PATH}", file=sys.stderr)
        print("as a single line:", file=sys.stderr)
        print("  FANGXIN_API_KEY=sk-xxxxxxxx", file=sys.stderr)
        sys.exit(1)

    model = args.model or os.environ.get("FANGXIN_MODEL", DEFAULT_MODEL)
    if not args.model:
        model = DEFAULT_MODEL

    edit_mode = bool(args.image or args.mask)
    api_url = EDITS_API_URL if edit_mode else GENERATIONS_API_URL
    temp_dir = None

    try:
        if edit_mode:
            temp_dir = tempfile.TemporaryDirectory(prefix="fangxin-image-gen-")
            args = localize_edit_inputs(args, Path(temp_dir.name))

        start = time.time()
        raw = run_request(api_url=api_url, api_key=api_key, model=model, args=args, edit_mode=edit_mode)

        try:
            status_code, body = parse_curl_response(raw)
        except ValueError as exc:
            print(f"Request failed: {exc}", file=sys.stderr)
            sys.exit(1)

        if status_code >= 400:
            print(f"HTTP {status_code}: {json.dumps(body, ensure_ascii=False)}", file=sys.stderr)
            sys.exit(1)

        elapsed = time.time() - start
        images = body.get("data", [])
        if not images:
            print(f"Unexpected response: {json.dumps(body)}", file=sys.stderr)
            sys.exit(1)

        summary_parts = [
            f"mode={'edit' if edit_mode else 'generate'}",
            f"model={model}",
            f"size={body.get('size', args.size)}",
            f"quality={body.get('quality', args.quality)}",
            f"format={body.get('output_format', args.output_format)}",
            f"n={len(images)}",
            f"time={elapsed:.1f}s",
        ]
        if edit_mode:
            summary_parts.insert(2, f"inputs={len(args.image)}")
        print(" | ".join(summary_parts))
        print()

        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        file_ext = body.get("output_format", args.output_format or "png")

        for i, item in enumerate(images, 1):
            url = item.get("url", "")
            b64_json = item.get("b64_json", "")
            revised = item.get("revised_prompt", "")
            location = url
            if b64_json:
                path = outdir / f"image_{int(start)}_{i}.{file_ext}"
                path.write_bytes(base64.b64decode(b64_json))
                # Print the resolved absolute path so the user can find the file
                # regardless of whatever CWD they invoked the script from.
                location = str(path.resolve())
            print(f"[{i}/{len(images)}] {location}")
            if revised and revised != args.prompt:
                print(f"      revised_prompt: {revised}")
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def run_request(api_url, api_key, model, args, edit_mode):
    if edit_mode:
        cmd = build_edit_command(api_url, api_key, model, args)
    else:
        cmd = build_generation_command(api_url, api_key, model, args)

    attempts = max(1, args.retries + 1)
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT_SECONDS + 15, check=False)
        except subprocess.TimeoutExpired:
            last_error = f"Request timed out after {REQUEST_TIMEOUT_SECONDS} seconds."
            result = None
        else:
            last_error = result.stderr.strip() or f"curl exited with code {result.returncode}"
            if result.returncode == 0:
                return result.stdout
            transient_errors = (
                "Empty reply from server",
                "SSL_ERROR_SYSCALL",
                "Connection reset by peer",
            )
            if not any(err in last_error for err in transient_errors):
                break

        if attempt < attempts:
            time.sleep(2 + random.random())

    if last_error and "Empty reply from server" in last_error:
        print(f"Request failed after {attempts} attempts: provider closed the connection without a response.", file=sys.stderr)
        sys.exit(1)
    print(f"Request failed: {last_error or 'unknown curl failure'}", file=sys.stderr)
    sys.exit(1)


def build_generation_command(api_url, api_key, model, args):
    payload = {"model": model, "prompt": args.prompt}
    if args.n != 1:
        payload["n"] = args.n
    payload["size"] = args.size if args.size != "auto" else "auto"
    payload["quality"] = args.quality if args.quality != "auto" else "auto"

    if model.startswith("gpt-image"):
        payload["background"] = args.background if args.background != "auto" else "auto"
        payload["output_format"] = args.output_format if args.output_format != "png" else "png"
        if args.output_compression != 100:
            payload["output_compression"] = args.output_compression
        payload["moderation"] = args.moderation if args.moderation != "auto" else "auto"

    if model == "dall-e-3" and args.style:
        payload["style"] = args.style

    if args.user:
        payload["user"] = args.user

    return [
        "curl",
        "--http1.1",
        "-sS",
        "-D",
        "-",
        api_url,
        "-H",
        f"Authorization: Bearer {api_key}",
        "-H",
        "Content-Type: application/json",
        "-H",
        "User-Agent: fangxin-image-gen/1.0",
        "--max-time",
        str(REQUEST_TIMEOUT_SECONDS),
        "--data",
        json.dumps(payload, ensure_ascii=False),
    ]


def build_edit_command(api_url, api_key, model, args):
    cmd = [
        "curl",
        "--http1.1",
        "-sS",
        "-D",
        "-",
        api_url,
        "-H",
        f"Authorization: Bearer {api_key}",
        "-H",
        "User-Agent: fangxin-image-gen/1.0",
        "--max-time",
        str(REQUEST_TIMEOUT_SECONDS),
        "-F",
        f"model={model}",
        "-F",
        f"prompt={args.prompt}",
        "-F",
        f"input_fidelity={args.input_fidelity}",
        "-F",
        f"size={args.size}",
        "-F",
        f"quality={args.quality}",
        "-F",
        f"output_format={args.output_format}",
    ]

    if args.background != "auto":
        cmd.extend(["-F", f"background={args.background}"])
    if args.moderation != "auto":
        cmd.extend(["-F", f"moderation={args.moderation}"])
    if args.output_compression != 100:
        cmd.extend(["-F", f"output_compression={args.output_compression}"])
    if args.n != 1:
        cmd.extend(["-F", f"n={args.n}"])
    if args.user:
        cmd.extend(["-F", f"user={args.user}"])

    for image in args.image:
        cmd.extend(build_image_form_field("image", image))

    if args.mask:
        cmd.extend(build_image_form_field("mask", args.mask))

    if not args.image:
        print("Error: edit mode requires at least one --image input.", file=sys.stderr)
        sys.exit(1)

    return cmd


def localize_edit_inputs(args, temp_root):
    localized_images = [download_if_url(image, temp_root, f"image_{index + 1}") for index, image in enumerate(args.image)]
    localized_mask = download_if_url(args.mask, temp_root, "mask") if args.mask else None
    args.image = localized_images
    args.mask = localized_mask
    return args


def download_if_url(image_value, temp_root, stem):
    if not image_value:
        return image_value
    if not (image_value.startswith("http://") or image_value.startswith("https://")):
        return image_value

    url_path = image_value.split("?", 1)[0]
    suffix = Path(url_path).suffix or ".img"
    output_path = temp_root / f"{stem}{suffix}"
    cmd = [
        "curl",
        "-L",
        "--fail",
        "-sS",
        "-o",
        str(output_path),
        image_value,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT_SECONDS, check=False)
    if result.returncode != 0:
        error = result.stderr.strip() or f"curl exited with code {result.returncode}"
        print(f"Error: failed to download image URL {image_value}: {error}", file=sys.stderr)
        sys.exit(1)
    return str(output_path)


def build_image_form_field(field_name, image_value):
    path = Path(image_value).expanduser()
    if not path.exists():
        print(f"Error: image file not found: {image_value}", file=sys.stderr)
        sys.exit(1)

    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return ["-F", f"{field_name}=@{path};type={mime_type}"]


def parse_curl_response(raw):
    blocks = [block for block in raw.replace("\r\n", "\n").split("\n\n") if block.strip()]
    if len(blocks) < 2:
        raise ValueError("unexpected response format from curl")

    body_text = blocks[-1]
    header_block = None
    for block in reversed(blocks[:-1]):
        if block.startswith("HTTP/"):
            header_block = block
            break
    if not header_block:
        raise ValueError("missing HTTP status line")

    status_line = header_block.splitlines()[0]
    try:
        status_code = int(status_line.split()[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"bad status line: {status_line}") from exc

    try:
        body = json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"non-JSON body: {body_text[:200]}") from exc

    return status_code, body


if __name__ == "__main__":
    main()
