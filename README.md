# User Hosted Swap Bot

Language: [KO](#한국어) | [EN](#english)

## 한국어

유저가 직접 VPS/로컬에서 실행하는 자동 스왑 봇 템플릿입니다.  
기본 모드는 `PAPER_MODE=1` 입니다.

### 분리 레포 권장 이유

- 메인 서비스 코드와 리스크 분리
- 커뮤니티 리뷰/기여 용이
- 봇 릴리즈 사이클 독립 운영

### 안전 가드

- 토큰 화이트리스트 (`ALLOWED_TOKENS`)
- 최대 슬리피지 (`MAX_SLIPPAGE_BPS`)
- 최대 가스 (`MAX_GAS_GWEI`)
- 쿨다운 (`COOLDOWN_SECONDS`)
- 일일 거래 한도 (`DAILY_NOTIONAL_LIMIT_USD`)

### 빠른 시작

```bash
docker compose up -d --build
docker compose logs -f
```

최초 실행 시 `.env`가 자동 생성되고, `SIGNAL_TOKEN`이 비어 있으면 입력 프롬프트가 표시됩니다.

### 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py start
```

`python bot.py` 첫 실행에서:

- `.env`가 없으면 `.env.example` 기반 자동 생성
- `SIGNAL_TOKEN`이 없으면 터미널에서 입력 요청 후 `.env`에 저장
- `RPC_URL`, `CHAIN_ID`, `ROUTER_ADDRESS`가 비어 있으면 BSC 기본값 자동 적용
- `PAPER_MODE=0`이면 `PRIVATE_KEY`, `WALLET_ADDRESS`를 입력받아 `.env`에 저장

### 실행 옵션

```bash
# 메뉴 실행 (추천)
python bot.py
# 메뉴에서 4번: paper/live 모드 변경
# 메뉴에서 5번: PRIVATE_KEY/WALLET_ADDRESS 수동 입력
# 메뉴에서 6번: SIGNAL_TOKEN(봇토큰) 변경
# 메뉴에서 7번: NEAR_API_KEY 변경
# 메뉴에서 8번: AI 프록시 서버 실행

# 기본 루프 실행
python bot.py start

# 1회만 실행
python bot.py start --once

# 거래내역 50건 보기
python bot.py history --limit 50

# 거래내역 BUY만 보기
python bot.py history --limit 50 --side buy

# 거래내역 SELL만 보기
python bot.py history --limit 50 --side sell

# 거래내역 HOLD만 보기
python bot.py history --limit 50 --side hold

# 거래내역 JSON 그대로 보기
python bot.py history --limit 20 --json

# 실행 전에 모드 변경 (PAPER_MODE 저장)
python bot.py --mode live start
python bot.py --mode paper start

# 봇토큰 변경
python bot.py --set-bot-token
python bot.py --set-bot-token "bot_xxx"

# NEAR API 키 변경
python bot.py --set-near-api-key
python bot.py --set-near-api-key "near_xxx"

# AI 프록시 서버 실행
python bot.py serve-ai
python bot.py serve-ai --host 127.0.0.1 --port 18081
```

### NEAR AI 연동 (AI 분석 프록시)

1. https://cloud.near.ai/ 에서 계정 생성, 크레딧 충전, API 키 발급
2. 유저봇 `.env` 설정

```env
NEAR_API_BASE=https://cloud-api.near.ai/v1
NEAR_API_KEY=your_near_api_key
NEAR_MODEL=openai/gpt-4o-mini
AI_PROXY_HOST=127.0.0.1
AI_PROXY_PORT=18081
```

3. AI 프록시 실행

```bash
python bot.py serve-ai
```

4. 프론트에서 AI API Base를 `http://127.0.0.1:18081/api` 로 설정
   (프론트 모델 선택값이 프록시로 전달되어 NEAR 호출에 사용됨)

프록시 엔드포인트:
- `POST /api/analysis/chart-image`
- `GET /api/analysis/chart-image/logs?limit=20`

### 텔레그램 알림 연동

`.env`에 아래 값을 설정하면 봇 이벤트를 텔레그램으로 받을 수 있습니다.

```env
TELEGRAM_ENABLED=1
TELEGRAM_BOT_TOKEN=123456789:your_bot_token
TELEGRAM_CHAT_ID=123456789
TELEGRAM_NOTIFY_STARTUP=1
TELEGRAM_NOTIFY_EXECUTED=1
TELEGRAM_NOTIFY_ERROR=1
TELEGRAM_NOTIFY_SKIP=0
```

알림 기본 동작:
- 시작 알림 (`startup`)
- 체결 알림 (`executed`)
- 에러 알림 (`error`)
- 스킵 알림 (`skip`, 기본 비활성)

### 필수 환경변수

- `SIGNAL_URL` (예: `https://api.fori.kr/api/bot/signal`)
- `BOT_CONFIG_URL` (예: `https://api.fori.kr/api/bot/config`)
- `SIGNAL_TOKEN` (bot token)
- `NEAR_API_KEY` (AI 분석 프록시 사용 시)
- `RPC_URL`
- `ALLOWED_TOKENS`
- `ROUTER_ADDRESS`(v2), `V3_ROUTER_ADDRESS`/`V3_QUOTER_ADDRESS`(v3)

`BASE_TOKEN_ADDRESS`/`QUOTE_TOKEN_ADDRESS` 등 페어 관련 값은
기본적으로 `.env` fallback이며, 백엔드에 봇 설정이 있으면 `/api/bot/config` 값이 우선 적용됩니다.
견적은 v2/v3를 모두 조회하고, 더 유리한 라우트를 자동 선택합니다.

실거래 모드에서만:

- `PAPER_MODE=0`
- `PRIVATE_KEY`
- `WALLET_ADDRESS`

### Rust 백엔드 연동

1. bot token 발급

```bash
curl -X POST https://api.fori.kr/api/bot/token/regenerate \
  -H "Authorization: Bearer <USER_SESSION_TOKEN>"
```

2. 신호 저장

```bash
curl -X POST https://api.fori.kr/api/bot/signal \
  -H "Authorization: Bearer <USER_SESSION_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"action":"BUY","confidence":0.8,"reason":"breakout","trigger_condition":"GTE","trigger_price":1.02,"ttl_seconds":90}'
```

3. 봇 신호 조회

```bash
curl -X GET https://api.fori.kr/api/bot/signal \
  -H "Authorization: Bearer <BOT_TOKEN>"
```

4. 봇 설정 저장 (유저 세션)

```bash
curl -X POST https://api.fori.kr/api/bot/config \
  -H "Authorization: Bearer <USER_SESSION_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "base_token_address":"0x55d398326f99059fF775485246999027B3197955",
    "quote_token_address":"0xe9e7cea3dedca5984780bafc599bd69add087d56",
    "base_token_symbol":"USDT",
    "quote_token_symbol":"BUSD",
    "buy_amount_base":20,
    "sell_amount_quote":20
  }'
```

5. 봇 설정 조회 (봇 토큰)

```bash
curl -X GET https://api.fori.kr/api/bot/config \
  -H "Authorization: Bearer <BOT_TOKEN>"
```

### 로그 파일

- `data/state.json`
- `data/trades.ndjson`

## English

Safety-first template for user-hosted auto swap execution.  
Default mode is `PAPER_MODE=1`.

### Why Separate Repository

- Isolates bot risk from main service code
- Easier community review and contribution
- Independent release cycle for bot runtime

### Safety Guards

- Token whitelist (`ALLOWED_TOKENS`)
- Max slippage (`MAX_SLIPPAGE_BPS`)
- Max gas price (`MAX_GAS_GWEI`)
- Cooldown (`COOLDOWN_SECONDS`)
- Daily notional limit (`DAILY_NOTIONAL_LIMIT_USD`)

### Quick Start

```bash
docker compose up -d --build
docker compose logs -f
```

On first run, `.env` is created automatically and you will be prompted for `SIGNAL_TOKEN` if empty.

### Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py start
```

On first `python bot.py` run:

- If `.env` is missing, it is created from `.env.example`
- If `SIGNAL_TOKEN` is empty, prompt asks for token and saves it to `.env`
- If `RPC_URL`, `CHAIN_ID`, `ROUTER_ADDRESS` are empty, BSC defaults are auto-filled
- If `PAPER_MODE=0`, prompts for `PRIVATE_KEY` and `WALLET_ADDRESS` and saves them to `.env`

### Runtime Options

```bash
# interactive menu (recommended)
python bot.py
# option 4: switch paper/live mode
# option 5: set PRIVATE_KEY/WALLET_ADDRESS manually
# option 6: change SIGNAL_TOKEN (bot token)
# option 7: change NEAR_API_KEY
# option 8: start AI proxy server

# start loop
python bot.py start

# run one cycle only
python bot.py start --once

# show last 50 history rows
python bot.py history --limit 50

# show BUY-only history rows
python bot.py history --limit 50 --side buy

# show SELL-only history rows
python bot.py history --limit 50 --side sell

# show HOLD-only history rows
python bot.py history --limit 50 --side hold

# print raw json history
python bot.py history --limit 20 --json

# switch mode before running (persists PAPER_MODE)
python bot.py --mode live start
python bot.py --mode paper start

# change bot token
python bot.py --set-bot-token
python bot.py --set-bot-token "bot_xxx"

# change NEAR API key
python bot.py --set-near-api-key
python bot.py --set-near-api-key "near_xxx"

# run AI proxy server
python bot.py serve-ai
python bot.py serve-ai --host 127.0.0.1 --port 18081
```

### NEAR AI Integration (AI Analysis Proxy)

1. Create account, add credits, and generate API key at https://cloud.near.ai/
2. Configure `.env`:

```env
NEAR_API_BASE=https://cloud-api.near.ai/v1
NEAR_API_KEY=your_near_api_key
NEAR_MODEL=openai/gpt-4o-mini
AI_PROXY_HOST=127.0.0.1
AI_PROXY_PORT=18081
```

3. Start AI proxy:

```bash
python bot.py serve-ai
```

4. In frontend, set AI API Base to `http://127.0.0.1:18081/api`
   (selected model in frontend is forwarded to proxy and used for NEAR call)

Proxy endpoints:
- `POST /api/analysis/chart-image`
- `GET /api/analysis/chart-image/logs?limit=20`

### Telegram Notification Integration

Set the following in `.env` to receive bot events in Telegram:

```env
TELEGRAM_ENABLED=1
TELEGRAM_BOT_TOKEN=123456789:your_bot_token
TELEGRAM_CHAT_ID=123456789
TELEGRAM_NOTIFY_STARTUP=1
TELEGRAM_NOTIFY_EXECUTED=1
TELEGRAM_NOTIFY_ERROR=1
TELEGRAM_NOTIFY_SKIP=0
```

Default notification behavior:
- startup
- executed
- error
- skip (disabled by default)

### Required Env

- `SIGNAL_URL` (e.g. `https://api.fori.kr/api/bot/signal`)
- `BOT_CONFIG_URL` (e.g. `https://api.fori.kr/api/bot/config`)
- `SIGNAL_TOKEN` (bot token)
- `NEAR_API_KEY` (required when using AI analysis proxy)
- `RPC_URL`
- `ALLOWED_TOKENS`
- `ROUTER_ADDRESS`(v2), `V3_ROUTER_ADDRESS`/`V3_QUOTER_ADDRESS`(v3)

Pair fields like `BASE_TOKEN_ADDRESS`/`QUOTE_TOKEN_ADDRESS` are `.env` fallback values.
If backend config exists, `/api/bot/config` values override them at runtime.
The bot queries both v2 and v3, then automatically chooses the better quote route.

Live mode only:

- `PAPER_MODE=0`
- `PRIVATE_KEY`
- `WALLET_ADDRESS`

### API Integration (Rust Backend)

1. Generate bot token

```bash
curl -X POST https://api.fori.kr/api/bot/token/regenerate \
  -H "Authorization: Bearer <USER_SESSION_TOKEN>"
```

2. Set signal

```bash
curl -X POST https://api.fori.kr/api/bot/signal \
  -H "Authorization: Bearer <USER_SESSION_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"action":"BUY","confidence":0.8,"reason":"breakout","trigger_condition":"GTE","trigger_price":1.02,"ttl_seconds":90}'
```

3. Bot polls signal

```bash
curl -X GET https://api.fori.kr/api/bot/signal \
  -H "Authorization: Bearer <BOT_TOKEN>"
```

4. Save bot config (user session)

```bash
curl -X POST https://api.fori.kr/api/bot/config \
  -H "Authorization: Bearer <USER_SESSION_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "base_token_address":"0x55d398326f99059fF775485246999027B3197955",
    "quote_token_address":"0xe9e7cea3dedca5984780bafc599bd69add087d56",
    "base_token_symbol":"USDT",
    "quote_token_symbol":"BUSD",
    "buy_amount_base":20,
    "sell_amount_quote":20
  }'
```

5. Bot reads config

```bash
curl -X GET https://api.fori.kr/api/bot/config \
  -H "Authorization: Bearer <BOT_TOKEN>"
```

### Logs

- `data/state.json`
- `data/trades.ndjson`

## Documents

- Security: [SECURITY.md](./SECURITY.md)
- Disclaimer: [DISCLAIMER.md](./DISCLAIMER.md)
- Contributing: [CONTRIBUTING.md](./CONTRIBUTING.md)
- License: [LICENSE](./LICENSE)
