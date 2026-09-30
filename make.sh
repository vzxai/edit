#!/usr/bin/env bash
# Build the edit.  ./make.sh            -> draft with the temporary score
#                   ./make.sh song.mp3   -> the real thing, cut to the song
set -euo pipefail
cd "$(dirname "$0")"
OUT=${OUT:-out}; mkdir -p "$OUT"
SONG=${1:-}
if [[ -n "$SONG" ]]; then
  python3 edit/beats.py "$SONG" "$OUT/beats.json"
  python3 edit/audio.py "$OUT/audio.wav" --song "$SONG" --beats "$OUT/beats.json"
  python3 edit/render.py "$OUT/video.mp4" --beats "$OUT/beats.json"
  NAME=seize-the-future
else
  python3 edit/audio.py "$OUT/audio.wav"
  python3 edit/render.py "$OUT/video.mp4"
  NAME=seize-the-future_draft-temp-score
fi
python3 tools/credits.py
ffmpeg -y -v error -i "$OUT/video.mp4" -i "$OUT/audio.wav" -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT/$NAME.mp4"
echo "done: $OUT/$NAME.mp4"
