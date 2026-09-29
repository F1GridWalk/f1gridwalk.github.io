# WORLD MEDIA LENS — how each race's column is made

Race weekends get three issues, one per day (owner's decision, 29 Sep 2026), each with its own page and vote:
- 金曜号 (practice): after FP2 — long runs, upgrades, what teams and drivers said, practice incidents. Slug `<gp>-2026-fri`, gpLabel e.g. "マレーシア・金曜".
- 土曜号 (qualifying): after qualifying — the grid, surprises, penalties, quotes. Slug `<gp>-2026-sat`, gpLabel e.g. "マレーシア・予選".
- 日曜号 (race): after the race — the main issue. Slug `<gp>-2026`, gpLabel e.g. "マレーシアGP".
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
