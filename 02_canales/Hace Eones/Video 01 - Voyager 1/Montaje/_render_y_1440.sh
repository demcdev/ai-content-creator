#!/bin/bash
cd "$(dirname "$0")"
PYTHONIOENCODING=utf8 python video01.py 10 > salida/render_v5.log 2>&1 || exit 1
cd salida
ffmpeg -y -loglevel error -i video-01-completo.mp4 -vf "scale=2560:1440:flags=lanczos,unsharp=5:5:0.45:5:5:0.0" -c:v libx264 -preset slow -crf 15 -pix_fmt yuv420p -profile:v high -g 60 -bf 2 -c:a copy -movflags +faststart "../Entregables/video-01-v5-1440p.mp4" > enc1440.log 2>&1
echo "FIN-1440" >> render_v5.log
