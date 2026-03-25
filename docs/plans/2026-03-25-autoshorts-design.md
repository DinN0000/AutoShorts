# AutoShorts 설계 문서

## 개요

중국 SNS(Douyin, Kuaishou, Bilibili, Xiaohongshu)에서 동물 쇼츠를 자동 수집하고, 고수준 편집(AI 나레이션, 스토리라인 재구성, 비주얼 이펙트)을 통해 완전히 새로운 콘텐츠로 재창조한 뒤, 다중 언어로 번역하여 여러 플랫폼에 자동 업로드하는 시스템.

**최우선 목표:** 유튜브 및 각 플랫폼 저작권 정책 100% 준수

---

## 아키텍처

```
[OpenClaw] ──(크론/훅/하트비트)──▶ [Pipeline CLI]
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              [Collector]         [Validator]          [Editor]
              Douyin/Kuaishou     저작권 다중검증        FFmpeg + AI
              Bilibili/XHS       루프 (3단계)          나레이션/자막
                    │                   │                   │
                    ▼                   ▼                   ▼
              [Translator]        [Validator]          [Uploader]
              다중언어 자막/TTS    최종 검증 루프        YouTube API
                                        │               + 5개 플랫폼
                                   PASS or REJECT
```

- 모든 단계는 CLI 커맨드 (`python -m autoshorts <command>`)
- OpenClaw은 CLI만 호출하면 됨
- Validator가 편집 전(소스 검증) + 편집 후(최종 검증) 2회 배치
- 각 단계는 상태를 JSON 파일로 저장
- 검증 실패 시 자동 재시도 또는 폐기

---

## 기술 스택

| 영역 | 기술 | 비용 |
|------|------|------|
| 언어 | Python | 무료 |
| 크롤링 | Playwright | 무료 |
| 영상 처리 | FFmpeg / MoviePy | 무료 |
| 음성→텍스트 | Whisper (로컬) | 무료 |
| TTS | edge-tts | 무료 |
| AI 분석/생성 | Claude (구독 토큰) | 구독 내 |
| 영상 분석 | Claude Vision (구독 토큰) | 구독 내 |
| 유튜브 업로드 | YouTube Data API v3 | 무료 |
| 기타 업로드 | 각 플랫폼 공식 API | 무료 |

---

## 에이전트 모듈 상세

### 1. Collector (수집)

```bash
autoshorts collector run --platform douyin --limit 50
autoshorts collector run --platform all --limit 200
autoshorts collector status
```

- Playwright 기반 크롤링 (Douyin, Kuaishou, Bilibili, XHS)
- 플랫폼별 어댑터 패턴 — 새 플랫폼 추가 용이
- 수집 결과: `data/raw/{date}/{platform}_{id}/` 에 영상 + 메타데이터 JSON
- 검색 전략 파일 (`data/strategy.json`) 읽어서 키워드/방향 반영

#### 적응형 수집 전략

폐기 사유를 분석하여 검색 방향을 자동 전환한다. 필터 추가 방식(수집량 감소)이 아닌 방향 전환 방식(수집량 유지 + 통과율 상승).

| 폐기율 | 대응 |
|--------|------|
| < 50% | 현행 유지 |
| 50-80% | 전략 조정 |
| > 80% | 긴급 재탐색 |

방향 전환 예시:
- "이미 유튜브 존재" 다수 → 인기 영상 대신 최신/비인기 영상 탐색
- "저작권 불명확" 다수 → CC 라이선스 명시 계정, 개인 촬영 크리에이터 우선
- "브랜드/로고 포함" 다수 → 야외/자연 배경 키워드 강화

학습 사이클: 수집 → 검증 → 폐기 사유 집계 → 전략 리포트 → 다음 사이클 반영

### 2. Validator (검증)

```bash
autoshorts validate source --input data/raw/2026-03-25/
autoshorts validate final --input data/edited/2026-03-25/
autoshorts validate report
```

#### Stage 1: 소스 검증 (편집 전)

1. **라이선스 체크** — CC 라이선스 여부, 플랫폼별 이용약관 분석
2. **원본 유사도 검색** — 이미 유튜브에 존재하는지, 다른 채널이 같은 소스 사용 중인지
3. **콘텐츠 분류** — 동물 학대/위험 콘텐츠 필터, 브랜드/로고/얼굴 감지

통과 실패 시: 폐기 + 사유 로그 → 적응형 수집에 피드백

#### Stage 2: 변환 검증 (편집 후)

1. **Transformative 충분성** — 원본 대비 변경 비율, 나레이션/스토리 추가 확인, 시각적 변형 정도
2. **오디오 검증** — BGM 저작권 (royalty-free), TTS 음성 사용 적법성
3. **메타데이터 검증** — 제목/설명/태그 오해 소지, 출처 표기 적절성

통과 실패 시: 편집 재요청 (최대 3회 재시도)

#### Stage 3: 최종 검증 (업로드 전)

1. **Claude Vision 종합 판정** — 전체 영상 프레임 샘플링, 유튜브 정책 위반 소지 판정
2. **판정 기준:**
   - 0-10: 자동 업로드
   - 11-30: OpenClaw 판단에 위임
   - 31+: 자동 폐기
3. **판정 근거 로그 저장**

핵심 원칙: 의심스러우면 폐기. 모든 판정에 근거 로그. 100개 수집해서 10개만 통과해도 OK.

### 3. Editor (편집)

```bash
autoshorts edit --input data/validated/source/{id}/
autoshorts edit --retry {id}
```

- FFmpeg 기반 영상 처리
- 편집 파이프라인:
  - 원본 클립 분할/재조합
  - 속도 변경 (0.8x-1.2x 랜덤)
  - 색보정/필터 적용
  - 좌우반전, 크롭, 줌 등 시각 변형
  - 원본 오디오 제거
- Whisper (로컬) 로 원본 음성→텍스트
- Claude (구독) 로 텍스트 기반 새 스토리라인 생성
- 결과: `data/edited/{id}/`

### 4. Translator (번역/로컬라이즈)

```bash
autoshorts translate --input data/edited/{id}/ --langs en,ja,de,ko,fr,es,pt
```

- Claude (구독) 로 스토리라인 다중 언어 번역
- edge-tts (무료) 로 언어별 나레이션 생성
- 언어별 자막 파일 (SRT) 생성
- 언어별 제목/설명/해시태그 생성
- 결과: `data/localized/{id}/{lang}/`

### 5. Uploader (업로드)

```bash
autoshorts upload --input data/final/{id}/ --platforms youtube,tiktok,instagram
autoshorts upload status
autoshorts upload schedule
```

플랫폼별 어댑터:
- YouTube → Data API v3
- TikTok → TikTok API
- Instagram Reels → Instagram Graph API
- Facebook Reels → Graph API
- Threads → Threads API
- Snapchat → Snapchat API

국가별 타임존 기반 업로드 스케줄링. 채널당 일일 1-2개 제한.

### 6. Pipeline (오케스트레이션)

```bash
autoshorts pipeline run
autoshorts pipeline status
autoshorts pipeline heartbeat
```

- 각 단계를 순서대로 호출
- 상태 파일: `data/pipeline_state.json`
- OpenClaw이 이 커맨드들만 알면 전체 운영 가능

---

## 업로드 플랫폼

| 플랫폼 | API | 비고 |
|--------|-----|------|
| YouTube Shorts | Data API v3 | 핵심 수익원 |
| TikTok | TikTok API | 노출 극대화 |
| Instagram Reels | Graph API | Meta 생태계 |
| Facebook Reels | Graph API | 동물 콘텐츠 바이럴 최강 |
| Threads | Threads API | Meta 생태계 |
| Snapchat Spotlight | Snapchat API | 크리에이터 펀드 |

---

## 다중 언어 & 수익 전략

### Tier 1 — 고수익 (CPM $15-40)

| 언어 | 타겟 국가 |
|------|----------|
| 영어 | US, UK, Canada, Australia |
| 독일어 | Germany, Austria, Switzerland |
| 일본어 | Japan |

### Tier 2 — 중수익 (CPM $5-15)

| 언어 | 타겟 국가 |
|------|----------|
| 한국어 | Korea |
| 프랑스어 | France, Belgium, Canada(QC) |
| 스페인어 | Spain, Mexico, LatAm |
| 포르투갈어 | Brazil |

### Tier 3 — 볼륨 (CPM $1-5)

| 언어 | 비고 |
|------|------|
| 힌디어 | 인구 대비 볼륨 폭발 |
| 아랍어 | 중동 CPM 의외로 괜찮음 |

채널 분리: 언어별 채널 (알고리즘이 단일 언어 채널 선호)
업로드 시간: 타겟 국가 프라임타임 기준
썸네일/제목: 문화 차이 반영 (일본=귀여움, 미국=놀라움/웃김)

---

## OpenClaw 연동

### 훅 구조

```
hooks/
  on_collect_complete    → 수집 완료 시 검증 시작
  on_validate_pass       → 검증 통과 시 편집 시작
  on_validate_fail       → 검증 실패 시 폐기 + 로그
  on_edit_complete       → 편집 완료 시 최종 검증
  on_upload_complete     → 업로드 완료 시 결과 리포트
  on_upload_fail         → 업로드 실패 시 재시도 로직
  heartbeat              → 각 단계 상태 체크 (주기적)
  daily_report           → 일일 운영 리포트 생성
```

### OpenClaw 스킬 파일

```
skills/
  autoshorts-operator.md     → 전체 운영 (크론/훅/하트비트 설정)
  autoshorts-monitor.md      → 모니터링 (상태 체크, 리포트 확인)
  autoshorts-troubleshoot.md → 장애 대응 (실패 시 대응법)
```

### OpenClaw 운영 원칙

- `docs/openclaw-guide/README.md` 만 읽으면 운영 가능
- 모든 조작은 CLI 커맨드로 수행
- 판단이 필요한 경우 (Stage 3 점수 11-30) OpenClaw이 결정

---

## 문서 구조

```
docs/
├── openclaw-guide/
│   ├── README.md              # 퀵스타트 (이것만 읽으면 운영 가능)
│   ├── commands.md            # CLI 커맨드 전체 레퍼런스
│   ├── hooks.md               # 훅 설정 및 사용법
│   ├── troubleshooting.md     # 문제 상황별 대응
│   └── daily-operations.md    # 일일 운영 루틴
├── architecture/
│   ├── overview.md            # 시스템 전체 구조
│   ├── data-flow.md           # 데이터 흐름
│   └── copyright-policy.md    # 저작권 검증 정책 상세
├── modules/
│   ├── collector.md           # 수집 모듈 상세
│   ├── validator.md           # 검증 모듈 상세
│   ├── editor.md              # 편집 모듈 상세
│   ├── translator.md          # 번역 모듈 상세
│   └── uploader.md            # 업로드 모듈 상세
└── setup/
    ├── installation.md        # 설치 가이드
    ├── api-keys.md            # API 키 설정
    └── platform-accounts.md   # 플랫폼별 계정/채널 설정
```

코드 변경 시 관련 문서도 함께 업데이트한다 (CLAUDE.md에 규칙 명시).

---

## 디렉토리 구조

```
autoshorts/
├── src/
│   ├── collector/        # 수집
│   ├── validator/        # 검증
│   ├── editor/           # 편집
│   ├── translator/       # 번역
│   ├── uploader/         # 업로드
│   ├── pipeline/         # 오케스트레이션
│   └── common/           # 공유 유틸
├── data/                 # 작업 데이터 (gitignore)
│   ├── raw/
│   ├── validated/
│   ├── edited/
│   ├── localized/
│   ├── final/
│   └── uploads/
├── config/
│   ├── platforms.yaml    # 플랫폼별 설정
│   ├── languages.yaml    # 언어/채널 매핑
│   └── schedule.yaml     # 업로드 스케줄
├── docs/                 # 문서 (위 구조 참조)
├── skills/               # OpenClaw 스킬 파일
├── hooks/                # OpenClaw 훅 스크립트
└── tests/                # 테스트
```

---

## 운영 환경

- 로컬 머신 실행
- OpenClaw가 크론잡/하트비트/훅으로 전체 파이프라인 관리
- 일일 운영 리포트로 상태 모니터링
