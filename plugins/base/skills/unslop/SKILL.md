---
name: unslop
description: "Rewrites prose to remove AI writing tells — filler, hedging, AI vocabulary, mannered metaphors, em dashes, inline-header lists, chatbot phrases, and Korean 번역투 — while keeping the meaning and tone. Use on PR titles and bodies, commit messages, docs, READMEs, release notes, Slack drafts, or a reply before it goes out, or when asked to unslop / de-AI / make writing sound less like AI."
---

# Unslop

Ported from pstack's `unslop` (MIT), with Korean tells added. Rewrite the text so none of the patterns below remain; keep the meaning, the facts, and the intended tone. Return the rewritten text, not a list of what changed, unless asked.

## 출력 언어

사용자에게 보이는 텍스트(설명, 요약)는 **한국어**로 쓴다. 다듬는 대상 글은 원래 언어를 유지한다 — 영어 PR은 영어로, 한국어 문서는 한국어로. 코드·식별자·경로·명령어는 그대로 둔다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Content

- **Superficial -ing phrases** ("highlighting…", "ensuring…", "showcasing…"). Delete, or say what actually happens.
- **Vague attributions** ("experts believe", "industry reports suggest"). Name the source or delete.
- **Generic conclusions** ("the future looks bright"). State the plan or the fact.
- **Says how it feels, not what it does.** Replace it with the mechanism or a number. If the sentence could appear unchanged in another project's docs, cut it.

## Language

- **AI vocabulary**: additionally, crucial, delve, enhance, fostering, garner, intricate, landscape, pivotal, robust, seamless, showcase, tapestry, testament, underscore, vibrant. Use the plain word.
- **Plain words over fancy ones**: use (utilize, leverage), help (facilitate), is/has (serves as, stands as, boasts, features), if (in the event that), because (due to the fact that), to (in order to).
- **Abstract metaphor nouns**: substrate, wedge, vector, locus, nexus, primitive (as a noun), harness, surface ("API surface"), scaffolding, paradigm, north star, flywheel, ratchet. Pick the concrete word.
- **Mannered prose**: aphorisms, rhetorical fragments, personified code ("the plan holds it"), figurative verbs ("rides along"). Say it literally.
- **"Not just X, but Y"**, forced groups of three, synonym cycling (pick one name and repeat it), false ranges ("from X to Y" off any real scale).
- **Hedging stacks** ("could potentially be argued") → one hedge or none. **Adverbs propping a weak verb** ("significantly improves") → the stronger verb or the measured number.
- **Passive voice** where the actor is known → name the actor.

## Style

- **No em dashes, en dashes, or hyphen-as-dash.** End the sentence or use a comma.
- **No mid-sentence colon as a connector.** A colon before a list or an example is fine.
- **Inline-header lists** ("**Performance:** Performance improved…") → prose. A bold lead-in ending in a period followed by new detail is fine.
- **Boldface** only on the one thing that must not be missed. Sentence-case headings. No decorative emojis. Straight quotes.
- **Dense or over-compressed sentences.** One idea per sentence; write the articles, verbs, and words that arrows and abbreviations replaced.
- **Tables and bullets are prose too.** A cell or bullet that strings nouns, arrows, or terms only the author's session knows ("줄", "건별 연결", "토큰 추가") becomes a sentence a newcomer understands, saying what changed and why. Keep cells short by moving the explanation into a bullet, not by compressing it.
- **Chatbot and sycophantic phrases** ("I hope this helps!", "Great question!", "Let me know if…"). Delete.

## Korean

The same rules apply; these are the forms they take in Korean.

- **번역투**: "~에 대해", "~을 통해", "~에 있어서", "~되어지다"(이중 피동), "~하는 것이 가능하다" → 동사로 바로 쓴다("~할 수 있다", "~로", "~에서").
- **의미 없는 서두와 맺음말**: "중요한 점은 ~", "~라고 할 수 있습니다", "결론적으로", "도움이 되셨길 바랍니다", "궁금한 점이 있으면 말씀해주세요" → 지운다.
- **명사 나열·한자어 압축**: "검증 수행 후 결과 확인 필요" → "검증을 돌리고 결과를 확인해야 한다". 화살표·기호로 문장을 대신하지 않는다.
- **과한 존댓말 겹침**("~해주시면 감사하겠습니다", "~하실 수 있으십니다") → 한 단계로. 문서는 한 가지 문체(합니다체 또는 한다체)로 통일한다.
- **영어 단어를 섞은 추상어**("임팩트 있는 솔루션을 레버리지") → 구체적인 한국어 또는 실제 이름.
