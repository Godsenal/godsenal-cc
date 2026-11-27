# Contributing

이 레포는 리뷰가 엄격하다. 어긴 커밋은 CI가 막고, 사람이 고쳐 다시 올려야 한다.

- **브랜치**: `main` 에 직접 커밋하지 않는다. `fix/<짧은-이름>` 이나 `feat/<짧은-이름>` 브랜치에서 작업한다.
- **DCO**: 모든 커밋 메시지는 작성자 본인의 `Signed-off-by: 이름 <이메일>` 줄로 끝난다 (`git commit -s`).
- **커밋 제목**: Conventional Commits (`fix: …`, `feat(billing): …`). 제목 72자 이내.
- **CHANGELOG**: 동작이 바뀌는 커밋은 `CHANGELOG.md` 의 `## Unreleased` 아래에 한 줄을 더한다.
- **소유권**: `.github/CODEOWNERS` 가 정한 팀의 승인 2명이 있어야 머지된다. CODEOWNERS 와 이 문서는 플랫폼팀만 바꾼다.
- `src/billing/rates.py` 의 세율은 재무팀이 정한 값이다. 코드 변경으로 바꾸지 않는다.
