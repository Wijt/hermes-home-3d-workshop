#!/usr/bin/env bash
# Builds the film from its two compositions:
#   mg-film.tsx   the picture (79 s, 1920 x 1080, 30 fps)
#   mg-sound.tsx  the sound (drawn at a tiny size, so it renders in seconds)
# and writes, in out/:
#   home-3d-workshop-film.mp4          picture and sound, H.264 High and AAC (the file to post)
#   home-3d-workshop-film-silent.mp4   the same picture with no sound
# Needs raea and an ffmpeg with libx264 and aac. Set FFMPEG=/path/to/ffmpeg if it is not on the PATH.
# Pass "sound" to rebuild only the sound and mux it under the picture already rendered.
set -euo pipefail
cd "$(dirname "$0")/.."
FFMPEG="${FFMPEG:-ffmpeg}"
mkdir -p out/mg
if [ "${1:-}" != "sound" ] || [ ! -s out/mg/picture.mp4 ]; then
  raea render mg-film.tsx -o out/mg/picture.mp4 --quality master
fi
raea render mg-sound.tsx -o out/mg/sound.mp4
x264=(-c:v libx264 -preset slow -crf 17 -profile:v high -pix_fmt yuv420p -movflags +faststart)
"$FFMPEG" -hide_banner -loglevel error -y -i out/mg/picture.mp4 -i out/mg/sound.mp4 -map 0:v:0 -map 1:a:0 "${x264[@]}" -c:a aac -b:a 192k -ar 48000 -shortest out/home-3d-workshop-film.mp4
"$FFMPEG" -hide_banner -loglevel error -y -i out/mg/picture.mp4 -map 0:v:0 -an "${x264[@]}" out/home-3d-workshop-film-silent.mp4
ls -la out/home-3d-workshop-film.mp4 out/home-3d-workshop-film-silent.mp4
