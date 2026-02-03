#!/bin/bash
set -e

# ===== 스크립트 위치 기준 =====
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR" || exit 1

BOT_FILE="$BASE_DIR/bot.py"

echo "📂 작업 디렉토리: $BASE_DIR"

# ===== bot.py 존재 확인 =====
if [ ! -f "$BOT_FILE" ]; then
  echo "❌ bot.py 파일이 존재하지 않습니다."
  exit 1
fi

# ===== bot.py에 shebang 섞였는지 검사 =====
if grep -q "#!/bin/bash" "$BOT_FILE"; then
  echo "❌ bot.py 안에 bash shebang 이 섞여 있습니다."
  echo "👉 run.sh 와 bot.py 파일이 섞였을 가능성이 큽니다."
  exit 1
fi

# ===== python 확인 =====
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 를 찾을 수 없습니다."
  exit 1
fi

# ===== venv =====
if [ ! -d ".venv" ]; then
  echo "🐍 .venv 생성 중..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# ===== 의존성 =====
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
fi

# ===== 실행 (절대경로 + 안전) =====
echo "🚀 bot.py 실행"
exec python "$BOT_FILE"
