#!/usr/bin/env bash
# Build the edit.  ./make.sh                          -> the edit, cut to music/i-feel-weird.mp3
#                   ./make.sh --draft                  -> the same picture over a temporary score (no song needed)
#                   FAST=1 ./make.sh                   -> quicker, larger encode for checking
set -euo pipefail
cd "$(dirname "$0")"
OUT=${OUT:-out}; mkdir -p "$OUT"
SONG=music/i-feel-weird.mp3
FASTFLAG=${FAST:+--fast}
if [[ "${1:-}" != "--draft" && -f "$SONG" ]]; then
  python3 edit/audio.py "$OUT/audio.wav" --song "$SONG"
  NAME=seize-the-future
else
  python3 edit/audio.py "$OUT/audio.wav"
  NAME=seize-the-future_draft-temp-score
fi
python3 edit/render.py "$OUT/video.mp4" $FASTFLAG
python3 tools/credits.py
ffmpeg -y -v error -i "$OUT/video.mp4" -i "$OUT/audio.wav" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT/$NAME.mp4"
echo "done: $OUT/$NAME.mp4"
