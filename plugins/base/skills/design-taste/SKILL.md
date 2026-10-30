---
name: design-taste
description: "Holds the user's own UI/UX taste, collected from their design feedback across apps, as rules to apply while working: let layout, defaults, and affordances lead the action instead of a caption that explains the UI (\"필터는 아래에서 고를 수 있어요\"), interactive onboarding instead of instruction screens, no feature or selling point nobody asked for, a redesign that visibly changes something, empty and loading states that earn every element, and platform details (safe area, keyboard, small screens, skeletons, current iOS materials) counted as part of done. Use whenever building, changing, or reviewing any app or web screen, component, onboarding, empty/loading/completion state, on-screen copy, design option, icon, or App Store screenshot, and when the user gives design feedback."
---

# design-taste

The user's taste, from their own feedback (dates and words in [sources.md](references/sources.md)). Apply it while building, not as a pass afterwards. The app's `DESIGN.md`, tokens, and design system decide the look; these rules decide what the user will reject regardless of the look. A general taste skill (`design-taste-frontend`, `frontend-design`) can sit alongside for art direction; where it disagrees, these rules win.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드, 보고 줄의 접두사(`교훈:` 등), 커밋 메시지·브랜치 이름(레포 관례). 앱 안의 UI 문구는 앱의 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Rules

1. **The UI leads; no caption explains it.** This is the one that keeps coming back. A line like "아래에서 필터를 고를 수 있어요", "스와이프해서 넘겨보세요", or "탭해서 자세히 보기" means the layout isn't doing its job: put the control where it's expected, make it look tappable, show a selected default or a preview (the next card peeking from the edge), then delete the line. Text stays only where the UI can't carry it: a format or limit before input (비밀번호 8자 이상), a money or irreversible consequence, an error at the moment it happens, an empty state's next step.
2. **Onboarding is something to do, not to read.** No pages of explanation or coach marks; let the first real action teach the gesture (swipe the actual card). Put onboarding where the user would otherwise wait (the first photo import, a long load), so the wait isn't a blank screen with a progress bar.
3. **Nothing the user didn't ask for.** No share button, extra step, or upsell added to a screen on your own, and no marketing of what users take for granted ("사진이 기기 밖으로 안 나가요" is not a selling point). Before adding an element, name the user action it serves; an element you can't justify (a photo grid on an empty screen) comes out.
4. **Empty, loading, and done states are designed screens.** An empty first screen has one clear next action and nothing else. Images load behind a skeleton in their final size, which keeps the layout from jumping the way a spinner does. Finishing a long task gets its own moment, quiet and without new features.
5. **Batch the repetitive flow.** When the user will do the same thing many times (importing photos), give multi-select, not one at a time. Lists that can grow to thousands stay smooth: virtualize and use thumbnails.
6. **Ask for what you need; don't tell the user to go get it.** A missing permission triggers the system prompt, or opens the right Settings page if already denied, from the button that needed it, not a message saying permission is required.
7. **Platform details are part of done, not polish.** Respect safe areas (a sheet's close button must be reachable), keep inputs above the keyboard, check the smallest supported screen (iPhone SE: nothing clipped, everything scrolls), keep text legible in every picker and input in both light and dark. On iOS use the system's Liquid Glass material on the control layer (tab bar, toolbar, sheets), never on content and never glass on glass, and not a flat translucent box called glass.
8. **A redesign must be visible.** If the before and after need a caption to tell apart, it wasn't a redesign: change hierarchy, structure, or emphasis, and show the two side by side. Don't flip the app's default appearance (light ↔ dark) as a side effect; that's the user's call.
9. **Follow a reference's feel, not its layout.** When the user points at another app, take its material, rhythm, and type, and keep this app's own structure. A home screen that reads as a copy gets rejected as fast as one that ignores the reference. When the UI imitates a real-world thing, match the real thing ("실제 작품처럼"), not a schematic of it.
10. **No AI tells.** "감도 높게" means a deliberate, specific look; it fails on the generated defaults: Inter on everything, a purple or blue-violet gradient, every block centered, one radius on everything, a card grid for every layout, emoji or an icon in a small colored box where a real visual belongs, a colored stripe on a card's left edge, italic accent words, sparkle icons for "AI". Name the default you're avoiding instead of "make it less AI-like", which only swaps one default for another. An AI feature is shown by what it does for the user (its pick, its learned order), lightly, not by an "AI" badge.
11. **Store art and marketing images show the actual users' world.** Use real-looking subjects the target users would photograph themselves (for a photo app: travel and pet photos), never generic sci-fi or stock filler.

## Design options

The user decides on things they can see and tap, not on descriptions. When a design question has more than one answer, offer `/gbase:mockup` (explicit only, so suggest it; don't call it) or put the options on screen in the app, rather than describing them in a reply.

## Before calling a screen done

Look at it, don't reason about it: screenshots on the smallest and a large supported device, light and dark, empty and very long content, keyboard open where there's input. Read every visible line of copy against rule 1 and every element against rule 3.

## New feedback

When the user gives design feedback that would apply beyond the current screen, report it in the same turn, one line at column 0: `교훈: design-taste — <date "user's words">: <rule>`. A `work` run reviews it and adds it here, replacing the rule it contradicts instead of adding a second one. Don't edit this plugin's source from the task you're on.
