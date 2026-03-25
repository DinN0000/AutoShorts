# AutoShorts

Automated animal shorts pipeline: collect → validate → edit → translate → upload.

## Commands

- `autoshorts collector run --platform <name> --limit <n>` - Collect videos
- `autoshorts validate source --input <path>` - Stage 1 validation
- `autoshorts validate final --input <path>` - Stage 2+3 validation
- `autoshorts edit --input <path>` - Edit video
- `autoshorts translate --input <path> --langs <codes>` - Translate
- `autoshorts upload --input <path> --platforms <names>` - Upload
- `autoshorts pipeline run` - Run full pipeline

## Rules

- When modifying a module, update its corresponding doc in `docs/modules/`
- All copyright validation logic lives in `src/autoshorts/validator/`
- Never skip validation stages — the 3-stage loop is the core safety mechanism
- Data files go in `data/` (gitignored), config in `config/`
- Test with `pytest`
- **작업이 끝나면 반드시 `HANDOFF.md`를 업데이트하라** — 완료된 것, 다음에 할 것, 변경사항을 기록하여 다음 세션 에이전트가 즉시 파악할 수 있도록 한다
- GitHub push 시 `gh auth switch --user DinN0000` 필요
