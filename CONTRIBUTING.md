# Contributing / 기여 가이드

## 한국어
### 기여 범위
- 안정성 개선
- 안전 가드 개선
- 문서/배포 UX 개선
- 테스트/관측성 개선

### 규칙
- 기본 안전 가드를 우회하는 코드는 받지 않습니다.
- 기본 모드는 반드시 `PAPER_MODE=1` 유지
- 개인키/시드/개인 인증정보를 포함하지 마세요.

### PR 체크리스트
- [ ] 변경 범위와 목적을 설명했는가
- [ ] 동작 변경 시 README를 업데이트했는가
- [ ] 설정 추가 시 `.env.example`를 업데이트했는가
- [ ] diff에 비밀값이 없는가

## English
### Scope
Contributions are welcome for:
- Reliability improvements
- Safety guards
- Better docs and deployment UX
- Testing and observability

### Rules
- Do not submit code that bypasses safety guards by default.
- Keep default mode as `PAPER_MODE=1`.
- Do not include private keys, seed phrases, or personal credentials.

### Pull Request Checklist
- [ ] Change is scoped and explained
- [ ] README updated if behavior changed
- [ ] `.env.example` updated for new configuration
- [ ] No secrets in diff
