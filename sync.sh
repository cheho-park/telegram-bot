#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# ===== 설정 =====
BRANCH="main"
REMOTE="origin"
FORCE=false

if [ "${1:-}" = "--yes" ]; then
  FORCE=true
fi

echo "🔄 Git 저장소 안전 동기화 스크립트"
echo "--------------------------------"

# Git 저장소 확인
if [ ! -d ".git" ]; then
  echo "❌ 여기는 Git 저장소가 아닙니다."
  exit 1
fi

# 현재 브랜치
CURRENT_BRANCH=$(git branch --show-current)
echo "📌 현재 브랜치: $CURRENT_BRANCH"

# 변경사항 체크
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "⚠ 로컬에 커밋되지 않은 변경사항이 있습니다."
  git status --short
  echo

  if ! $FORCE; then
    read -p "❓ 변경사항을 모두 버리고 진행할까요? (yes/no): " ANSWER
    if [ "$ANSWER" != "yes" ]; then
      echo "🛑 사용자에 의해 중단됨"
      exit 0
    fi
  fi

  echo "🧹 로컬 변경사항 제거 중..."
  git reset --hard
  git clean -fd
fi

# 브랜치 확인
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
  echo "⚠ 현재 브랜치가 $BRANCH 가 아닙니다."

  if ! $FORCE; then
    read -p "❓ $BRANCH 브랜치로 이동할까요? (yes/no): " ANSWER
    if [ "$ANSWER" != "yes" ]; then
      echo "🛑 사용자에 의해 중단됨"
      exit 0
    fi
  fi

  git switch "$BRANCH"
fi

# 원격 fetch
echo "📡 원격 저장소 정보 가져오는 중..."
git fetch "$REMOTE"

# 원격 브랜치 존재 여부 확인
if ! git show-ref --verify --quiet "refs/remotes/$REMOTE/$BRANCH"; then
  echo "❌ 원격 브랜치 $REMOTE/$BRANCH 가 존재하지 않습니다."
  exit 1
fi

# 변경 요약
echo
echo "🔍 원격과의 차이 요약:"
git log --oneline --decorate --max-count=5 "HEAD..$REMOTE/$BRANCH" || echo "(차이 없음)"

echo
if ! $FORCE; then
  read -p "❓ 위 변경사항을 적용할까요? (yes/no): " ANSWER
  if [ "$ANSWER" != "yes" ]; then
    echo "🛑 사용자에 의해 중단됨"
    exit 0
  fi
fi

# 최종 적용
echo "🧹 원격 상태로 완전 동기화 중..."
git reset --hard "$REMOTE/$BRANCH"

echo "🗑 추적되지 않는 파일 정리..."
git clean -fd

echo
echo "✅ 동기화 완료"
git status