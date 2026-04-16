# Security Policy / 보안 정책

## 한국어
### 지원 버전
- 현재는 최신 `main` 브랜치만 지원합니다.

### 취약점 제보
- 비밀키/토큰 노출 이슈를 공개 이슈로 올리지 마세요.
- 저장소 관리자에게 비공개로 제보해 주세요.
- 재현 절차, 영향 범위, 관련 파일을 함께 보내주세요.

### 핵심 보안 수칙
- `.env`, 개인키, 시드 문구를 절대 커밋하지 마세요.
- 초기 검증은 반드시 `PAPER_MODE=1`로 진행하세요.
- 토큰 노출 시 즉시 재발급하세요 (`/api/bot/token/regenerate`).
- 지갑 권한/일일 한도를 보수적으로 설정하세요.

## English
### Supported Versions
- Currently, only the latest `main` branch is supported.

### Reporting a Vulnerability
- Do not open public issues for secret/key exposure.
- Report privately to repository maintainers.
- Include reproduction steps, impact, and affected files.

### Key Safety Rules
- Never commit `.env`, private keys, or seed phrases.
- Keep `PAPER_MODE=1` for initial validation.
- Rotate bot tokens if leaked (`/api/bot/token/regenerate`).
- Restrict wallet permissions and keep notional limits conservative.
