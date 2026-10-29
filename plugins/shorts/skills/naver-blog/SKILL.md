---
name: naver-blog
description: >-
  Plans and diagnoses a Korean Naver blog (정보형 생활정보·지원금·IT 블로그) — growth strategy, post template,
  title formula, and monetization order — from Naver blogs that actually rank in 통합검색 or publicly disclose
  revenue, opened first in a browser. Use when asked for a Naver blog strategy, a post template or titles for
  one, why a Naver blog's posts don't show in search, or 애드포스트·체험단·쇼핑커넥트 planning, or when the user
  gives feedback on one.
---

# naver-blog

All of [content-common](../content-common/SKILL.md) applies; changes go through its feedback intake. Blog details (blog id, name, queue, work folder like `$HOME/LTH/naver-blog`) are the caller's settings, not this skill's. Writing a single post is a separate job (the caller's own post-writing skill); this skill covers the references, the diagnosis, and the plan. Title formulas and a post template's first paragraph start from [hook-templates](../hook-templates/SKILL.md).

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 리포트)와 콘텐츠 산출물(제목, 템플릿, 본문 예시)은 **한국어**로 쓴다. 따옴표 안 한국어는 사용자 원문 또는 레퍼런스 원문 인용이라 그대로 둔다. 코드·경로·명령어는 대상 레포의 관례를 따른다.

## References first

2026-10-28 "실제로 수익화가 잘되고 검색 노출이 잘되는 네이버 블로그 레퍼런스를 ego-browser로 직접 열어 보고 그걸 기반으로": pick references two ways, (1) the blogs ranking at the top of 네이버 통합검색 right now for the caller's own queue keywords, and (2) blogs that publicly disclose revenue (애드포스트·체험단·쇼핑커넥트·쿠팡파트너스 수익 공개). Open 2–3 real posts per blog and quote the original text in the report. If Naver can't be opened, stop and say so.

How to open them (learned 2026-10-28):
- Posts: use `https://m.blog.naver.com/{id}/{logNo}`. The desktop URL wraps the post in an iframe. Body is `.se-main-container`, title `.se-title-text`; scroll to the end before counting images (lazy load).
- Blog stats: the mobile blog home shows `오늘 N 전체 N`, `N명의 이웃`, the 블로그 주제, and the intro line.
- Cadence and categories: `page.fetch("https://m.blog.naver.com/api/blogs/{id}/post-list?categoryNo=0&itemCount=30&page=1")` returns the last 30 posts with `addDate` (UTC ms, add 9h for KST) and `categoryName`. Its `totalCount` came back 0, so blog age and post count need another route.
- Search: the blog tab is `search.naver.com/search.naver?ssc=tab.blog.all&query=…`. `where=blog` returned the same list as 통합검색.
- AdPost presence: a post with 애드포스트 ads has an `ad-content-bottom-slot` iframe at the end of the body. A blog without it shows only `ad-bottom-banner-slot` (Naver's own banner).
- Images: the system Python's urllib failed SSL on pstatic.net on the reference machine. `curl -H "Referer: https://m.blog.naver.com/"` with `?type=w400` works. Build one montage and look at it to judge photo vs. generated/card images.

## Diagnosis

- **Compare the blog, not only the post** — lesson 2026-10-28: the caller's posts (2,600–3,200자, sources cross-checked) didn't show for their exact titles, while the top-ranked posts for the same keywords were 1,100–2,000자 with generated images. What differed was blog-level: 이웃 162–20,944 vs 6, 전체 방문 9,752–19.6M vs 1,466, categories concentrated in 1–5 (vs 12), 블로그 주제 matching the content (vs `일상·생각`), a real operator identity in the first line, and a 공감·이웃추가·question ending. Always tabulate those blog-level facts next to the post facts before blaming length, images, or title format.
- **Don't invent the operator** — references open with a real identity ("현직 보건관리자입니다", "다둥이맘", "아빠도 처음이라"). Never write a fake profession or life situation into a template or post. Ask the user for a real background they're willing to show.
- Official numbers: 애드포스트 publishes no thresholds ("구체적인 수치는 공개할 수 없습니다", reviewed on last month's UV·PV). Quote the help page with its check date. Any threshold you give is a `가정:` line.
