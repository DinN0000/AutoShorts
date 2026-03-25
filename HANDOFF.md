# AutoShorts 핸드오프 문서

> 마지막 업데이트: 2026-03-26

## 프로젝트 상태: Collector 완전 구현, 나머지 모듈 구현 필요

### 완료된 것

- **6개 모듈 골격** 전부 구현 (collector, validator, editor, translator, uploader, pipeline)
- **Collector 4개 플랫폼 완전 구현** (Playwright 검색 + yt-dlp 다운로드)
  - `douyin.py` — Douyin 검색/다운로드 구현
  - `bilibili.py` — Bilibili 검색/다운로드 구현 (BV ID 추출, 시간 파싱 포함)
  - `kuaishou.py` — Kuaishou 검색/다운로드 구현
  - `xiaohongshu.py` — Xiaohongshu 검색/다운로드 구현 (비디오 인디케이터 감지)
- **pyproject.toml** collector optional에 `yt-dlp>=2024.1` 의존성 추가
- **CLI** 전체 커맨드 동작 (`autoshorts <command>`)
- **3단계 저작권 검증 로직** 구현 및 테스트 통과 (Stage 1/2/3)
- **적응형 수집 전략** 엔진 구현 (폐기 사유 분석 → 검색 방향 전환)
- **FFmpeg 필터 빌더** 구현 (속도/반전/크롭/색보정/줌)
- **SRT 자막 생성기** 구현
- **업로드 스케줄러** 구현 (9개 언어 타임존/프라임타임)
- **파이프라인 상태 관리** 구현 (7단계 상태 추적)
- **Config 파일** 3개 (platforms.yaml, languages.yaml, schedule.yaml)
- **OpenClaw 가이드** 5개 문서 + 3개 스킬 + 8개 훅 스크립트
- **Claude API 번역 기능** 완전 구현 (9개 언어 텍스트/자막/메타데이터 번역)
- **테스트** 59개 + 번역 7개 전부 통과
- **GitHub** https://github.com/DinN0000/AutoShorts

### 아직 스텁(stub)인 것 — 다음에 구현해야 할 것

우선순위 순서:

#### 1. Whisper + Claude 연동 (Editor AI 기능)
- `src/autoshorts/editor/narration.py` — `transcribe_audio()` Whisper 로컬 실행
- `src/autoshorts/editor/narration.py` — `generate_storyline()` Claude 구독 토큰으로 스토리라인 생성
- `src/autoshorts/editor/runner.py` — 실제 FFmpeg 파이프라인 실행

#### 2. ~~Claude Vision 연동 (Validator Stage 3)~~ ✅ 완료
- `src/autoshorts/validator/vision.py` — OpenCV 프레임 추출 (10초 간격) + Claude Vision API 분석
- `src/autoshorts/validator/stage3.py` — `FinalCheckInput.video_path` 추가, Vision 점수 병합 (기존 70% + Vision 30%)
- Vision 검출 항목: 로고/워터마크, 저작권 캐릭터, 방송 오버레이, 스튜디오 제작 징후, 크리에이터 텍스트
- 의존성: `anthropic>=0.39` (optional `[validator]`)
- 테스트 13개 통과 (`tests/validator/test_stage3.py`)

#### 3. ~~번역 연동 (Translator)~~ ✅ 완료
- `src/autoshorts/translator/runner.py` — Claude Haiku API로 9개 언어 번역 구현
- `translate_text()` — 텍스트 번역, `translate_metadata()` — 제목/설명 번역, `translate_srt_entries()` — 자막 번역
- CLI `autoshorts translate --input <path> --langs en,ko,ja` 동작
- 환경변수 `ANTHROPIC_API_KEY` 필요
- 의존성: `anthropic>=0.42` (optional `[translator]`)
- 테스트 7개 추가 (`tests/translator/test_runner.py`)

#### 4. 플랫폼 API 연동 (Uploader)
- `src/autoshorts/uploader/youtube.py` — YouTube Data API v3 OAuth + 업로드
- `src/autoshorts/uploader/tiktok.py` — TikTok API
- `src/autoshorts/uploader/instagram.py` — Instagram Graph API
- `src/autoshorts/uploader/facebook.py` — Facebook Graph API
- `src/autoshorts/uploader/threads.py` — Threads API
- `src/autoshorts/uploader/snapchat.py` — Snapchat API
- API 키 설정 필요 (`config/secrets.yaml`)

#### 5. ~~Stage 1 유튜브 유사도 검색~~ ✅ 완료
- `src/autoshorts/validator/youtube_similarity.py` — YouTube Data API v3 검색, fuzzywuzzy 텍스트 유사도, OpenCV 썸네일 유사도
- `src/autoshorts/validator/stage1.py` — 하드 게이트 통합 (75% 이상 유사 시 +100점 → 자동 폐기)
- API 키: 환경변수 `YOUTUBE_API_KEY` 우선, `config/secrets.yaml` fallback
- 테스트 16개 추가 (`tests/validator/test_youtube_similarity.py`), 전체 48개 통과
- 의존성: `fuzzywuzzy`, `python-Levenshtein`, `opencv-python`, `google-api-python-client` (optional `[validator]`)

#### 6. 누락된 문서
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
