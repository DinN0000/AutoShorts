# AutoShorts 핸드오프 문서

> 마지막 업데이트: 2026-03-25

## 프로젝트 상태: 기본 골격 완료, 실제 구현 필요

### 완료된 것

- **6개 모듈 골격** 전부 구현 (collector, validator, editor, translator, uploader, pipeline)
- **CLI** 전체 커맨드 동작 (`autoshorts <command>`)
- **3단계 저작권 검증 로직** 구현 및 테스트 통과 (Stage 1/2/3)
- **적응형 수집 전략** 엔진 구현 (폐기 사유 분석 → 검색 방향 전환)
- **FFmpeg 필터 빌더** 구현 (속도/반전/크롭/색보정/줌)
- **SRT 자막 생성기** 구현
- **업로드 스케줄러** 구현 (9개 언어 타임존/프라임타임)
- **파이프라인 상태 관리** 구현 (7단계 상태 추적)
- **Config 파일** 3개 (platforms.yaml, languages.yaml, schedule.yaml)
- **OpenClaw 가이드** 5개 문서 + 3개 스킬 + 8개 훅 스크립트
- **테스트** 32개 전부 통과
- **GitHub** https://github.com/DinN0000/AutoShorts

### 아직 스텁(stub)인 것 — 다음에 구현해야 할 것

우선순위 순서:

#### 1. Playwright 크롤러 (Collector 실제 구현)
- `src/autoshorts/collector/douyin.py` — Douyin 검색/다운로드
- `src/autoshorts/collector/bilibili.py` — Bilibili 검색/다운로드
- `src/autoshorts/collector/kuaishou.py` — Kuaishou 검색/다운로드
- `src/autoshorts/collector/xiaohongshu.py` — XHS 검색/다운로드
- 모두 `NotImplementedError` 상태
- `playwright install` 필요

#### 2. Whisper + Claude 연동 (Editor AI 기능)
- `src/autoshorts/editor/narration.py` — `transcribe_audio()` Whisper 로컬 실행
- `src/autoshorts/editor/narration.py` — `generate_storyline()` Claude 구독 토큰으로 스토리라인 생성
- `src/autoshorts/editor/runner.py` — 실제 FFmpeg 파이프라인 실행

#### 3. Claude Vision 연동 (Validator Stage 3)
- `src/autoshorts/validator/stage3.py` — 현재 외부에서 `risk_score` 주입 방식
- 실제로는 영상 프레임 샘플링 → Claude Vision 분석 필요

#### 4. 번역 연동 (Translator)
- `src/autoshorts/translator/runner.py` — Claude 구독으로 다중 언어 번역
- edge-tts 호출은 구현되어 있으나 번역 텍스트가 없으면 의미 없음

#### 5. 플랫폼 API 연동 (Uploader)
- `src/autoshorts/uploader/youtube.py` — YouTube Data API v3 OAuth + 업로드
- `src/autoshorts/uploader/tiktok.py` — TikTok API
- `src/autoshorts/uploader/instagram.py` — Instagram Graph API
- `src/autoshorts/uploader/facebook.py` — Facebook Graph API
- `src/autoshorts/uploader/threads.py` — Threads API
- `src/autoshorts/uploader/snapchat.py` — Snapchat API
- API 키 설정 필요 (`config/secrets.yaml`)

#### 6. Stage 1 유튜브 유사도 검색
- 설계 문서에 명시되어 있으나 아직 미구현
- 수집된 영상이 이미 유튜브에 존재하는지 확인하는 기능

#### 7. 누락된 문서
- `docs/architecture/` (overview.md, data-flow.md, copyright-policy.md)
- `docs/modules/` (collector.md, validator.md, editor.md, translator.md, uploader.md)
- `docs/setup/` (installation.md, api-keys.md, platform-accounts.md)

### 핵심 설계 원칙 (반드시 준수)

1. **저작권 검증이 최우선** — 3단계 검증 루프 절대 생략 금지
2. **의심스러우면 폐기** — 100개 수집해서 10개만 통과해도 OK
3. **적응형 수집** — 필터 추가(수집량 감소) 대신 방향 전환(수집량 유지)
4. **채널당 1-2개/일** — 스팸 방지
5. **OpenClaw 독립 운영** — CLI만으로 모든 것 조작 가능해야 함

### 기술 스택

- Python 3.11+, venv: `.venv/`
- 테스트: `source .venv/bin/activate && python -m pytest tests/ -v`
- CLI: `autoshorts --help`
- 비용: 전부 무료/구독 범위 (API 과금 없음)

### 참조 문서

- 설계 문서: `docs/plans/2026-03-25-autoshorts-design.md`
- 구현 계획: `docs/plans/2026-03-25-autoshorts-implementation.md`
- OpenClaw 가이드: `docs/openclaw-guide/README.md`
