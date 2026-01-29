#!/bin/bash
# run.sh
# 역할: 프로젝트 실행 스크립트 (서버 재부팅/자동실행용)

cd "$(dirname "$0")" || exit 1
python3 bot.py
