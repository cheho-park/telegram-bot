# Telegram Bot (뼈대)

간단한 텔레그램 봇 뼈대입니다. python-telegram-bot 라이브러리를 사용한 비동기 폴링 방식입니다.

## 요구사항

-   Python 3.8+
-   `python-telegram-bot` (버전 20 이상 권장)
-   `python-dotenv` (환경변수 로드용)

## 설치 (PowerShell)

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# .env 파일을 열어 BOT_TOKEN 값을 설정하세요
python bot.py
```

## Docker 사용

도커로 개발 환경을 띄우려면 다음과 같이 합니다. 이 예시는 로컬 Postgres 컨테이너를 띄워 마이그레이션 테스트를 할 때 유용합니다.

```powershell
docker-compose up --build
```

앱이 빌드되고 실행됩니다. `.env` 파일을 루트에 두면 `docker-compose`가 환경 변수를 읽습니다.

마이그레이션을 실행하려면(로컬 Postgres를 사용하는 경우):

```powershell
docker-compose run --rm app python migrate.py
```

## 기본 명령

-   /start — 시작 인사
-   /help — 도움말
-   /ping — 응답 확인
-   /register — Supabase의 `users` 테이블에 사용자 등록 (처음 한 번 사용)
-   /me — 등록된 내 정보 조회
-   /xp — 내 XP 및 레벨 조회
-   /leaderboard — XP 기준 상위 사용자 확인

## 환경변수

`.env` 파일에 다음을 설정하세요:

```
BOT_TOKEN=your-telegram-bot-token
```

Supabase 연동을 추가하려면 아래 값을 `.env`에 추가하세요:

```
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-supabase-service-role-or-anon-key
```

참고: 위 기능은 프로젝트에 `users` 테이블(최소 `id`, `username` 컬럼)이 있어야 동작합니다. 프로젝트 초기에는 Supabase 콘솔에서 테이블을 생성하거나 SQL로 다음과 같이 생성할 수 있습니다:

```sql
create table if not exists users (
	id bigint primary key,
	username text,
	xp integer DEFAULT 0,
	level integer DEFAULT 1
);
```

## 자동 마이그레이션

간단한 마이그레이션 스크립트 `migrate.py`를 추가했습니다. 이 스크립트는 환경변수 `DATABASE_URL`을 사용해 Postgres에 접속하여 `users` 테이블을 생성합니다.

사용법(Windows PowerShell):

```powershell
# .env에 DATABASE_URL이 설정되어 있거나, 환경변수로 DATABASE_URL을 설정하세요.
python migrate.py
```

`DATABASE_URL`은 Supabase 프로젝트의 Settings > Database > Connection string 에서 확인할 수 있습니다. 서비스 역할 키와 DB 접속 문자열을 안전하게 관리하세요.

-   출석 시 기본 보상으로 10 XP를 지급하며, XP가 일정 수치에 도달하면 레벨업합니다. (레벨 공식: level = floor(sqrt(xp/100))+1)
-   메시지 전송 시 기본 보상으로 5 XP(쿨다운 60초)를 지급하고, 출석 시 기본 보상으로 10 XP를 지급합니다. XP가 일정 수치에 도달하면 레벨업합니다. (레벨 공식: level = floor(sqrt(xp/100))+1)
-   출석, 출석 기록, 연속 출석(streak)은 KST (UTC+9) 기준으로 계산합니다.
-   성능 최적화: 유저 정보와 리더보드 결과를 짧은 TTL(몇 초)로 메모리 캐시하여 메시지 기반 XP 집계 등의 상호작용에서 응답 지연을 줄였습니다. 메시지 XP 처리는 비동기로 백그라운드에 등록되어 빠른 응답을 제공합니다.

### 배포(예: 서버에서 Docker 사용)

1. 서버에 저장소를 복사하고 `.env`를 준비하세요. 로컬 Postgres 또는 Supabase를 사용한다면 `DATABASE_URL` 또는 `SUPABASE_URL`/`SUPABASE_KEY`를 설정하세요.

2. 컨테이너를 빌드하고 실행합니다.

```bash
docker-compose up -d --build
```

로컬에서 Docker 이미지를 직접 빌드하려면 다음을 사용하세요.

Make (UNIX/macOS/WSL):

```bash
make build
make run
```

PowerShell (Windows):

.
.
powershell\scripts\build.ps1 -ImageName telegram_bot -ImageTag latest
powershell\scripts\build.ps1 -ImageName telegram_bot -ImageTag latest

Exporting the image to a file (for transport or saving):

Make (UNIX/macOS/WSL):

```bash
make save  # creates telegram_bot-latest.tar.gz
```

PowerShell (Windows):

```powershell
.
.
powershell\scripts\export.ps1 -ImageName telegram_bot -ImageTag latest
```

Loading the image on a different machine:

```bash
docker load -i telegram_bot-latest.tar.gz
```

````

3. 앱 서비스는 컨테이너 시작 시 `migrate.py`를 실행하여 필요한 테이블을 생성하려 시도합니다. 만약 수동으로 마이그레이션을 실행하려면 다음 명령을 사용하세요.

```bash
docker-compose run --rm app python migrate.py
````

4. 모니터링 및 로그:

```bash
docker-compose logs -f
```

#### 서버에서 Docker 자동 시작(systemd 예시)

아래는 서버 재부팅 후 `docker compose` 애플리케이션을 자동으로 시작하기 위한 systemd 서비스 예시입니다. 파일을 `/etc/systemd/system/telegram_bot.service`로 생성하세요.

```ini
[Unit]
Description=Telegram Bot (docker-compose)
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=/path/to/your/repo
ExecStart=/usr/bin/docker compose up -d --build
ExecStop=/usr/bin/docker compose down
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

실행 후 다음 명령으로 서비스 등록 및 시작:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now telegram_bot.service
```

주의사항:

-   현재 XP 캐시/큐는 컨테이너 내부 메모리를 사용합니다. 다중 인스턴스 환경에서는 Redis 등을 사용하여 중앙화하도록 변경해야 합니다.
-   민감한 정보(BOT_TOKEN, SUPABASE_KEY 등)는 안전하게 관리하세요(Secrets Manager, Docker Secrets 등).

## 예시 출력(사람이 보기 편하게 개선)

`/xp` 응답 예시:

```
Lv2 — 150 XP (50/200 | 25%)
```

`/leaderboard` 응답 예시:

```
🏆 리더보드:
🥇 @alice    — Lv10 — 5000 XP
🥈 @bob      — Lv9  — 4200 XP
🥉 @charlie  — Lv8  — 3600 XP
4. ID:123456 — Lv7  — 3000 XP
```

`/attendance` 응답 예시:

```
최근 출석 기록:
- 2025-11-25 08:32:10 KST
- 2025-11-24 09:15:03 KST
```

`/me` 응답 예시:

```
@username
Lv2 — 150 XP (50/200 | 25%)
마지막 활동: 2025-11-25 08:32:10 KST
```

더 확장하고 싶은 기능(웹훅, 데이터베이스, 명령 분리 등)이 있다면 알려주세요.
