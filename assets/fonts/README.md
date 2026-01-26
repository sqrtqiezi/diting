# Fonts

Place Source Han Sans (思源黑体) font files in this directory for PDF rendering.

Recommended file names:
- `SourceHanSansSC-Regular.ttf`
- `SourceHanSansCN-Regular.ttf`
- `SourceHanSansSC-Regular.ttc`
- `SourceHanSansCN-Regular.ttc`

Note: ReportLab does not support CFF-based `.otf` fonts. If you only have `.otf`,
please obtain a TrueType `.ttf`/`.ttc` build or convert the font before use.

Bold font (optional, for headings):
- `SourceHanSansSC-Bold.ttf`
- `SourceHanSansSC-Bold.ttc`

If present, the renderer uses the bold font automatically. You can also set
`SOURCE_HAN_SANS_BOLD_PATH`.

Emoji images (Twemoji PNG, optional):
- Directory example: `assets/twemoji/72x72`
- CLI: `--emoji-image-dir assets/twemoji/72x72`
- Env: `TWEMOJI_DIR` or `EMOJI_IMAGE_DIR`
Auto-download (if enabled) stores into `data/twemoji/72x72`.
You can disable downloads via `EMOJI_AUTO_DOWNLOAD=0` or override the base URL
with `TWEMOJI_BASE_URL`.

Download from the official open-source releases:
https://github.com/adobe-fonts/source-han-sans/releases
