# WORLD MEDIA LENS — how the columns are made

WORLD MEDIA LENS has two kinds of pages (owner's decision, 29 Sep 2026):
- **コラム** (daily column): one every day, including race weekends, published automatically at about 07:00 JST by the scheduled task. A plain read — "こういう見方がある" — with no mystery and no vote. See §0.
- **グランプリ特別号** (race-weekend specials): three per race weekend, with "not seen in Japanese" stories, a mystery and a vote. The owner always checks them before they go out. See below and §1–5.

## 0. Daily column (コラム)
- One story a day from the last 24–48 hours of foreign coverage (non-English outlets preferred): a quote, number or inside detail not reported in Japanese; a headline that does not match what was said; the same event seen very differently by different countries; or a thread over several days (A said → B answered → C…). Do not reuse a story from the last 14 days of columns, special issues (グランプリ特別号) or 臨時号: open every `lens/*.json` that is not a draft (and the published ones' `extraSources` URLs) and skip any story, quote or source article already used there — even from a different angle (e.g. the Perez quote from the Italian motorsport.com article was already in the Baku speed-gap issue, so a column about it was pulled on 30 Sep 2026).
- Same fact rules as below: open every source with WebFetch and use only what it says; translate quotes faithfully; never invent numbers, names or dates; rumours and opinions are "〜と報じた" / "〜の見方"; never mix an article's own narration with a person's quote; no bias for or against any team or maker; run the Japanese check (autosport web, F1-Gate, Formula1-Data, motorsport.com 日本版, TopNews) — if the core story is already reported in Japanese, pick another. If no story can be confirmed, publish nothing that day and say so.
- Voice (owner's decision, 1 Oct 2026): the writer's own view is always the site's, never a person's — write 「F1 Grid Walkとしての見方です」 / 「F1 Grid Walkとしては〜と見ています」, never 「私の見方」「私は」「私の考えでは」「筆者」. Same in note manuscripts and X posts.
- Tone: easy to read, a little light, accurate. The first three lines say what is interesting. About 1,000–1,800 Japanese characters, 2–4 headings, quotes in 「」 with who said it and where. End with one question to the reader (block kind "ask"), e.g. 「あなたはどう見る？」.
- File: `lens/<slug>.json` with `"type": "column"`, `"gpLabel": "コラム"`, slug like `<keyword>-<yyyymmdd>` (e.g. `domenicali-ferrari-20260929`), `published` (real publish time, +09:00), `big` (one short word or number shown faintly in the hero, e.g. "80" or "?"), `title`, `titleHtml` (title with one `<em>` highlight), `dek` (1–2 sentences), `topics` (related topic slugs from articles.json, may be empty), `body` (list of `["p"|"h2"|"quote"|"bold"|"ask", text]`), no `note` field (owner's decision, 1 Oct 2026: the Japanese check is done behind the scenes only, to choose the story; never write 「日本語で検索し…見当たらなかった」 or 「日本語では報じられていない」 anywhere in a column, its note manuscript or its X posts — it reads like an excuse and like judging Japanese media), `extraSources` (every source used: `{source, region (Japanese country name), lang, title (Japanese translation of the headline), url}`).
- Title (owner's decision, 1 Oct 2026): click-friendly but true. About 25–35 characters. Put the hook first: a well-known name (driver/team), a striking number, a clash (「AはこうBはこう」), or a fair question (「〜は本当？」「〜か？」). Quote words exactly as in the body. Never promise what the article does not deliver, never make a rumour sound confirmed, no 「衝撃」「ヤバい」 style hype. Examples: 「土曜のF1は見られなかった？ ドイツのSky、視聴者が平均の半分以下に」, 「オコン「僕は最高の一人」 元王者は「結果はほとんどない」」, 「セパンの観客「昔の倍」は本当？ 9万5000枚と記録12万6690人」.
- note manuscript (owner's decision, 1 Oct 2026; made by `tools/col_assets.py` on `reserve`): column body → right after it the site entrance (F1 Grid Walk top page URL and this column's page URL with the fixed line 「ほかの海外記事も読みたい方は、F1 Grid Walkへ。」 above it (always, owner's choice), each URL alone on its own line so note shows them as image cards) → the sources as linked outlet names (「出典：GPblog（オランダ）」 with the link on the name, never a bare URL line, so they do not become cards).
- Share image (owner's OK, 1 Oct 2026): copy each issue's note header image (`note_<slug>_見出し画像.png`, 1280×670) to `lens/<slug>/og.png` on `main`, then run `python3 build.py`; the page then uses it as its og:image, so note/X cards show the column's own image. Applies to columns, 臨時号 and グランプリ特別号.
- Header image (owner's decision, 1 Oct 2026): big, high-contrast, click-friendly. Add an `"eye"` object to the column JSON and pick the layout that fits the story (spec in `tools/eye_layouts.py` on the `reserve` branch): `number` (one striking number + 2–3 short lines), `bignum` (number inside a phrase + 2 lines), `question` (a fair 「〜本当？」/「〜か？」 question, optional small line above or below), `band` (a driver/team name in an orange band + 1–3 short rows, e.g. 日本「…」/ オランダ「…」), `versus` (two people's quotes side by side), `headline` (2 big lines). Lines ≤13 characters, `<em>` for one highlight. Every quote, number and name on the image must be in the body exactly as the source says — shorten, never change the meaning (「結果はほとんどない」 is fine, 「結果がない」 is not). No bait the article does not deliver.
- A column that could stand as a グランプリ特別号 story may also be reused there later.

## 0b. Breaking column (速報コラム)
Owner's decision, 30 Sep 2026: no automatic breaking columns. A 速報コラム is written only when the owner asks for one on a specific story (e.g. `ocon-future-20260930`). Same format and fact rules as §0, show the owner a phone-width preview and the note/X assets, and publish on the owner's OK. Always offer 3–5 title options (each following the Title rule) with a copy button on each, and 3–4 header-image options in different "eye" layouts, so the owner can choose (owner's request, 1 Oct 2026); same for any other text the owner is asked to choose or paste.

## 0c. Japan vs abroad (臨時号・グランプリ特別号・速報コラム)
Owner's decision, 30 Sep 2026: the daily column stays foreign-sources only (§0). In the issues the owner checks — 臨時号, グランプリ特別号 and 速報コラム written on request — Japanese outlets may be used as sources too, to show readers how the same story is told in Japan and abroad: "日本の〇〇（媒体名）はこう伝えた / 海外の〇〇（媒体名・国）はこう伝えた". Name every outlet. Never say which side is better or worse and never mock either side; lay the differences side by side (what was emphasised, what was left out, which quote was used, headline vs body) and let the reader decide. The "not seen in Japanese" stories still follow §2.

## Race weekends: グランプリ特別号
Race weekends get three special issues, one per day, each with its own page and vote:
- 金曜 (practice): after FP2 — long runs, upgrades, what teams and drivers said, practice incidents. Slug `<gp>-2026-fri`, gpLabel e.g. "マレーシアGP特別号・金曜".
- 土曜 (qualifying): after qualifying — the grid, surprises, penalties, quotes. Slug `<gp>-2026-sat`, gpLabel e.g. "マレーシアGP特別号・予選".
- 日曜 (race): after the race — the main issue. Slug `<gp>-2026`, gpLabel e.g. "マレーシアGP特別号・決勝".
Friday and Saturday issues may have 2 stories instead of 3 when fewer good ones are confirmed. Each issue opens with the previous issue's vote result when the owner has shared it. Start each about two hours after the session ends (Japan time), when quotes and non-English analysis are out, show the owner a phone-width preview, and publish on the owner's OK, together with a note article. On sprint weekends, Friday's issue follows sprint qualifying and Saturday's covers the sprint and qualifying (start two hours after the last session of that day).
Scheduling chain: the three start times are booked one weekend at a time, as in-session reminders (send_later). When the Sunday issue is done, book the next weekend's three starts from the new `weekend` in season.json (official timetable, Japan time, minute :07 or similar, not :00), and write this same chain instruction into the new Sunday reminder so it carries on to the end of the season. Tell the owner the three times. Races held in the Americas end in the Japanese night or early morning; keep the two-hour rule anyway. If a round is cancelled (e.g. Qatar/Abu Dhabi), skip it and book the next one.
Page: `lens/<slug>.json` → `python3 build.py` → `lens/<slug>/index.html` (listed at /lens/, linked from the top page).

## 1. Collect (the session day)
- Start from the race-weekend articles in `news/archive.json` (topic of the race result and related topics).
- Add more non-English coverage by searching: Italian (formula1.it, f1grandprix.motorionline.com, formulapassion.it), German (F1-Insider, Motorsport-Magazin, auto motor und sport, Sportschau), Dutch (F1Maximaal, GPblog, GPFans NL), Brazilian (Lance!, Grande Prêmio, ge.globo), Spanish (SoyMotor, AS, Marca), French (Nextgen-Auto, L'Équipe free pieces).
- Free articles only. Open every one and read what it actually says.

## 2. "Not seen in Japanese" stories (3)
- Candidate = a concrete fact, quote or detail from a foreign article.
- Search in Japanese for it (autosport web, F1-Gate, Formula1-Data, motorsport.com 日本版, TopNews, DAZN, Yahoo! ニュース). Keep only candidates with no Japanese article covering the same point. English big outlets are almost always translated; the good candidates usually come from non-English outlets.
- Wording: titles and header images say "日本語では語られない3つの話" (owner's choice). The note under the stories always keeps the careful form "日本語で検索し、同じ内容の記事が見当たらなかった（◯月◯日時点）". Never "一切報じられていない".
- Rumours and pundit opinions get kind "rumor" and are labelled as someone's view.

## 3. The mystery (1)
- A gap between what the headlines say and what the sources show (e.g. Baku: headlines "0.196s photo finish" vs Verstappen "it was always one second; Russell lost boost under the last-lap yellow").
- Every piece of evidence must be a quote or fact from a named, linked source. Prefer a question about interpretation over a factual contradiction that might be our own summary error. Check the originals before using a "contradiction".
- Two or three choices. The answer box says what the evidence shows and what is still unconfirmed.

## 4. Write
- `lens/<slug>.json` (copy `lens/baku-2026.json`): start with `"draft": true`, fill slug, topic (or `topics`: a list, for columns that span several topics), gpLabel, published, big, title, titleHtml, dek, unreported, mystery.
- `python3 build.py`, check the page on phone width, then remove `"draft"` when the owner says go.
- note article: same 3 stories written for note (lighter tone, shorter), the mystery only as a teaser linking to the lens page for the answer and vote. Add `"noteUrl"` to the JSON once it is posted.

## 5. After publishing
- X: poll post (no link), answer reply 24 h later with the lens link, note introduction post.
- Next column: open with last race's vote result (GoatCounter events `lens/<slug>/vote/A|B`).

## 6. Reserve columns (臨時号)
Special issues on a news theme (not a race), written ahead and kept as drafts until the owner wants to run them.
- Kept on the git branch `reserve` (not on `main`, so nothing reaches the site): `lens/<slug>.json` with `"draft": true` and `"gpLabel": "臨時号"`, plus the note manuscript and header image under `reserve/`. To publish, copy the JSON onto `main`. Even on `main`, a JSON with `"draft": true` is never built; `build.py` deletes any page left over from a draft.
- Published: `horner-ferrari-2026` (28 Sep 2026). Reserve: `honda-abroad-2026` — rejected by the owner on 28 Sep; to be rebuilt from scratch before use.
- Before publishing a reserve, refresh it on the day:
  1. Search again for new articles on the theme (English and non-English). If something big happened (an announcement, a denial, new data), update the stories and the mystery, or drop the reserve.
  2. Re-run the Japanese check for all 3 stories. If a story is now covered in Japanese, replace it. Update the date in `unreported.note` and in the answer/caveat ("◯月◯日時点").
  3. Re-open every original link (still online, same wording).
  4. Fix time words that have gone stale (e.g. "10月22日発売予定" after the release, "今季ここまで17回" after the next race).
  5. Set `published` to the real publish time, remove `"draft"`, run `python3 build.py`, check on phone width, and publish together with the note article (same steps as §4–5).
