Telegram Message Formatting Skill

Purpose

Use this skill when generating, formatting, or improving Telegram messages.

The goal is to create a clean, structured, premium-looking Telegram UI using Unicode symbols, without relying on emojis.

Do not use emojis for decoration or UI structure. Use the approved Unicode symbols below instead.

---

Core Principle

Treat Unicode symbols like UI components.

Use them to create:

- Headers
- Sections
- Separators
- Lists
- Metadata rows
- Status indicators
- Borders
- Highlighted values
- Navigation-style elements
- Callouts
- Visual hierarchy

Avoid excessive decoration. Symbols should improve readability, not make the message noisy.

---

Approved Symbol Library

Primary UI Symbols

❖ ✧ ✦ ★ ✪ ◎ ○ ◇ ◆ ⟡

Use these for:

- Headers
- Important sections
- Highlights
- Feature labels
- Status indicators

Examples:

❖ Profile Information
✦ New Update
◇ Configuration
◆ Important

---

Directional / Action Symbols

➜ ▸ ◂ » « ✓ ✔

Use these for:

- Actions
- Navigation
- Key-value relationships
- Confirmation
- List items

Examples:

▸ Username: @example
▸ Status: Active
▸ Model: Gemini

Or:

Action » Continue
Status » Active

---

Structural Symbols

━ ━━
• ·
▪

Use these for:

- Horizontal separators
- Sub-items
- Compact lists
- Spacing between related information

Examples:

━━━━━━━━━━━━━━━━━━━━

• First item
• Second item
• Third item

For compact metadata:

Name · Developer
Status · Active

---

Brackets / Containers

【 】
『 』
「 」
〈 〉
《 》
╚ ╝
□

Use these to visually group information.

Examples:

【 SYSTEM STATUS 】

《 Configuration 》

〈 Active 〉

「 Developer Tools 」

Avoid nesting too many different bracket styles.

---

Font-Style Unicode

The following Unicode styles may be used when Telegram-compatible visual emphasis is useful:

Mathematical Bold

𝐀 𝐁 𝐂

Example:

𝐒𝐭𝐚𝐭𝐮𝐬

Mathematical Bold Sans

𝗔 𝗕 𝗖

Example:

𝗦𝘆𝘀𝘁𝗲𝗺 𝗦𝘁𝗮𝘁𝘂𝘀

Mathematical Italic

𝑨 𝑩 𝑪

Example:

𝑰𝒏𝒇𝒐𝒓𝒎𝒂𝒕𝒊𝒐𝒏

Mathematical Script

𝓐 𝓑 𝓒

Example:

𝓟𝓻𝓸𝓯𝓲𝓵𝓮

Double-Struck

𝔸 𝔹 𝔺

Example:

𝔸𝕀 𝕊𝕪𝕤𝕥𝕖𝕞

Small Caps

ᴀ ʙ ᴄ ᴅ ᴇ ғ ɢ ʜ ɪ ᴊ ᴋ ʟ ᴍ ɴ ᴏ ᴘ ǫ ʀ s ᴛ ᴜ ᴠ ᴡ x ʏ ᴢ

Example:

ᴘʀᴏꜰɪʟᴇ

Squared Characters

🅂 🄸 🄶 🄽 🄰 🄻

These should generally be avoided because they can have inconsistent rendering and are less readable than normal Unicode text.

---

Recommended Formatting Patterns

1. Simple Header

❖ 𝐏𝐫𝐨𝐟𝐢𝐥𝐞
━━━━━━━━━━━━━━━━━━━━

2. Section Header

✦ 𝗦𝘆𝘀𝘁𝗲𝗺 𝗜𝗻𝗳𝗼

3. Metadata

▸ Name · Example
▸ ID · 123456
▸ Status · Active
▸ Role · Developer

4. Compact Information Card

╔════════════════════╗
   ❖ 𝗦𝘆𝘀𝘁𝗲𝗺 𝗦𝘁𝗮𝘁𝘂𝘀
╚════════════════════╝

▸ Status · Online
▸ Model · Gemini
▸ Requests · 42
▸ Remaining · 18

If box-drawing characters are not available, use:

━━━━━━━━━━━━━━━━━━━━
❖ 𝗦𝘆𝘀𝘁𝗲𝗺 𝗦𝘁𝗮𝘁𝘂𝘀
━━━━━━━━━━━━━━━━━━━━

---

Lists

Prefer:

▸ First item
▸ Second item
▸ Third item

For nested information:

❖ Features

  ├─ OCR
  ├─ Translation
  ├─ Context Detection
  └─ Caching

Only use "├─" and "└─" when the hierarchy benefits from it.

---

Status Formatting

Use symbols instead of emojis.

✔ Completed
✓ Verified
◆ Active
◇ Pending
○ Inactive

Example:

❖ Task Status

✔ Authentication
✔ Database
◆ WebSocket
◇ Deployment

---

Alerts / Important Information

Use structural emphasis instead of emojis.

【 IMPORTANT 】

The requested operation could not be completed.

▸ Reason · Rate limit exceeded
▸ Retry · 30 seconds

Or:

◆ Warning
━━━━━━━━━━━━━━━━━━━━
The request could not be completed.

---

Key-Value Formatting

Preferred:

▸ Username · @example
▸ User ID · 123456789
▸ Role · Admin
▸ Status · Active

Alternative:

Username » @example
User ID » 123456789
Role » Admin
Status » Active

Do not randomly mix "·", "»", ":" and "=" within the same block.

Choose one style and stay consistent.

---

Message Footer

Use a subtle footer when appropriate:

━━━━━━━━━━━━━━━━━━━━
❖ Powered by Example

Or:

━━━━━━━━━━━━━━━━━━━━
· Example System ·

Do not add a footer to every message unnecessarily.

---

Design Rules

1. No Emoji
UI

Do not use emoji characters such as:

😀 😂 🔥 ❤️ 🚀 🎉 ✅ ❌

Use Unicode symbols instead:

◆ ✦ ❖ ✓ ✔ ◇ ○

---

2. Use Symbols With Purpose

Bad:

✦ ❖ ★ ◆ ✧ Profile ✧ ◆ ★ ❖ ✦

Good:

❖ 𝗣𝗿𝗼𝗳𝗶𝗹𝗲
━━━━━━━━━━━━━━━━━━━━

---

3. Maintain Visual Hierarchy

A good message should generally follow:

HEADER
───────
Section
▸ Information
▸ Information

Section
▸ Information
▸ Information
───────
Footer

Use different symbol types for different semantic purposes.

---

4. Keep Messages Scannable

Prefer:

❖ 𝗨𝘀𝗲𝗿 𝗜𝗻𝗳𝗼

▸ Name · John
▸ ID · 123456
▸ Role · Developer
▸ Status · Active

Instead of putting everything into a paragraph.

---

5. Avoid Symbol Overuse

Do not decorate every line.

Bad:

✦ ▸ Name ✧ » John ◆
❖ ▸ ID ✦ » 123456 ◇
★ ▸ Role ✧ » Developer ❖

Good:

❖ 𝗨𝘀𝗲𝗿 𝗜𝗻𝗳𝗼

▸ Name · John
▸ ID · 123456
▸ Role · Developer

---

Consistency Rules

Within one message:

- Pick one primary header symbol.
- Pick one list symbol.
- Pick one separator style.
- Pick one key-value separator.
- Use font styles sparingly.
- Do not mix many decorative styles without a reason.

Recommended default combination:

Header    → ❖
Section   → ✦
List      → ▸
Success   → ✓
Important → ◆
Pending   → ◇
Separator → ━━━
Key/value → ·

---

Default Telegram Message Template

When no specific formatting style is requested, use:

❖ 𝗛𝗲𝗮𝗱𝗲𝗿
━━━━━━━━━━━━━━━━━━━━

✦ 𝗦𝗲𝗰𝘁𝗶𝗼𝗻

▸ Field · Value
▸ Field · Value
▸ Field · Value

✦ 𝗦𝗲𝗰𝘁𝗶𝗼𝗻

✓ Completed
◇ Pending
◆ Active

━━━━━━━━━━━━━━━━━━━━

---

AI Generation Instructions

When generating a Telegram message:

1. First identify the message hierarchy.
2. Create a concise header if useful.
3. Divide large content into logical sections.
4. Use Unicode symbols as visual UI elements.
5. Use "▸" for ordinary information rows.
6. Use "✓", "✔", "◆", "◇", and "○" for meaningful statuses.
7. Use "━" for major separators.
8. Use "·" for compact key-value relationships.
9. Use Unicode font variants only for important headings or values.
10. Do not use emojis for decoration.
11. Do not add symbols to every line.
12. Keep the result readable when Telegram renders it on a small phone screen.
13. Prefer clean spacing over excessive decoration.
14. Never invent unusual Unicode characters when an approved symbol can perform the same job.
15. Preserve the actual information and wording; formatting must not alter its meaning.

Priority

Readability > Consistency > Visual hierarchy > Decoration.

The message should look intentionally designed, not overloaded with symbols.