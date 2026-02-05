# TODO List

Last updated: 2026-02-05

## Context
위키 생성 시 OpenAI Rate Limit과 프록시 타임아웃 문제가 발견됨 (gpt-4o 모델 사용 시)

---

## Priority: High 🔴

### Fix OpenAI Rate Limit Issue
**Problem**:
- 위키 생성 시 HTTP 429 (Too Many Requests) 빈번 발생
- 로그에서 12건 발생, 6-23초 대기 후 재시도
- Rate limit 대기 시간이 누적되어 프록시 타임아웃 유발

**Tasks**:
- [ ] OpenAI API 키의 rate limit tier 확인
  - Tier 1 (무료): RPM 500, TPM 200K
  - 필요시 Tier 2+ 업그레이드 검토

- [ ] 위키 생성 시 챕터 간 요청 간격 추가
  - File: `api/websocket_wiki.py`
  - 챕터 생성 루프에 1-2초 delay 추가
  - `asyncio.sleep(1.5)` 등으로 구현

- [ ] 동시 요청 수 제한
  - File: `api/websocket_wiki.py`
  - `asyncio.Semaphore`로 최대 3개 concurrent requests로 제한
  - 또는 순차 처리로 변경 검토

**Expected Impact**: Rate limit 발생 빈도 80% 감소 예상

---

## Priority: Medium 🟡

### Improve Relay Server Rate Limit Handling
**Problem**:
- 릴레이가 429 에러 시에도 3번 재시도
- 재시도 중 프록시 타임아웃(~120초) 초과 가능
- 총 소요 시간 393초까지 증가

**Tasks**:
- [ ] Rate limit 에러 즉시 전달
  - File: `api/openai_relay.py`
  - HTTP 429 발생 시 릴레이에서 재시도하지 않고 즉시 반환
  - 백엔드가 적절한 간격으로 재시도하도록 변경

- [ ] 릴레이 로깅 개선
  - Rate limit 발생 시 WARNING 레벨로 명확히 로깅
  - 통계 정보 추가 (총 요청 수, 성공/실패율 등)

**Code Example**:
```python
# api/openai_relay.py
if response.status_code == 429:
    logger.warning(f"Rate limit hit for model={model}")
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limit_exceeded", "retry_after": response.headers.get("retry-after")}
    )
```

**Expected Impact**: 프록시 타임아웃 발생 90% 감소 예상

---

## Priority: Low 🟢

### Proxy Timeout Mitigation
**Problem**:
- Samsung 프록시 타임아웃 ~120초 고정
- Rate limit 대기 시간 누적 시 초과 가능

**Tasks**:
- [ ] 백엔드 재시도 로직 검토
  - File: `api/websocket_wiki.py`
  - 현재 자동 재시도 메커니즘 확인
  - 필요시 명시적 재시도 로직 추가

- [ ] 프론트엔드 재시도 메커니즘 활용
  - CLAUDE.md에 언급된 대로 프론트엔드 자동 재시도 있는지 확인
  - 없다면 추가 고려

**Note**: High priority 작업 완료 시 자동 해결될 가능성 높음

---

### Fix Google Fonts Loading
**Problem**:
- 프록시 환경에서 `fonts.googleapis.com` 접근 실패
- 기능에는 영향 없지만 로그가 지저분함

**Tasks**:
- [ ] 로컬 폰트로 대체 검토
  - File: `src/app/layout.tsx` 또는 폰트 설정 파일
  - Google Fonts 대신 시스템 폰트 또는 로컬 폰트 사용

- [ ] 또는 프록시 설정으로 Google Fonts 허용
  - 네트워크 팀에 요청 필요

**Expected Impact**: 로그 가독성 향상

---

## Monitoring & Validation

### After Implementation
- [ ] 위키 생성 테스트 (gpt-4o, Comprehensive 타입)
- [ ] 릴레이 서버 로그 확인
  - 429 에러 발생 빈도
  - 프록시 타임아웃 발생 여부
- [ ] 평균 챕터 생성 시간 측정
- [ ] 성공률 측정 (목표: 95% 이상)

---

## Notes

### Related Files
- `api/websocket_wiki.py`: 위키 생성 로직
- `api/openai_relay.py`: OpenAI API 릴레이 서버
- `api/config.py`: 설정 관리
- `CLAUDE.md`: 프로젝트 가이드 및 Samsung 프록시 환경 정보

### Performance Metrics (Current Baseline)
- Model: gpt-4o
- Average response time: 15-38s
- Rate limit hits: 12/session
- Proxy timeouts: 2/session
- Success rate: ~90%
- Wiki cache size: 51KB (10 chapters)

### Target Metrics (After Improvements)
- Rate limit hits: <3/session
- Proxy timeouts: 0/session
- Success rate: >95%
