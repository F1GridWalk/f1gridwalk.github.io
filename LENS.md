# WORLD MEDIA LENS — how each race's column is made

One column per race, published the morning after the race (Japan time), together with a note article.
Page: `lens/<slug>.json` → `python3 build.py` → `lens/<slug>/index.html` (listed at /lens/, linked from the top page).

## 1. Collect (race day + 1 day)
- Start from the race-weekend articles in `news/archive.json` (topic of the race result and related topics).
- Add more non-English coverage by searching: Italian (formula1.it, f1grandprix.motorionline.com, formulapassion.it), German (F1-Insider, Motorsport-Magazin, auto motor und sport, Sportschau), Dutch (F1Maximaal, GPblog, GPFans NL), Brazilian (Lance!, Grande Prêmio, ge.globo), Spanish (SoyMotor, AS, Marca), French (Nextgen-Auto, L'Équipe free pieces).
- Free articles only. Open every one and read what it actually says.

## 2. "Not seen in Japanese" stories (3)
- Candidate = a concrete fact, quote or detail from a foreign article.
- Search in Japanese for it (autosport web, F1-Gate, Formula1-Data, motorsport.com 日本版, TopNews, DAZN, Yahoo! ニュース). Keep only candidates with no Japanese article covering the same point. English big outlets are almost always translated; the good candidates usually come from non-English outlets.
- Wording: always "日本語ではほぼ見かけない / 見当たらなかった（◯月◯日時点）", never "一切報じられていない".
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
- Current reserves: `horner-ferrari-2026` (Horner / Ferrari), `honda-abroad-2026` (Aston Martin-Honda seen from abroad). Both were researched on 28 Sep 2026.
- Before publishing a reserve, refresh it on the day:
  1. Search again for new articles on the theme (English and non-English). If something big happened (an announcement, a denial, new data), update the stories and the mystery, or drop the reserve.
  2. Re-run the Japanese check for all 3 stories. If a story is now covered in Japanese, replace it. Update the date in `unreported.note` and in the answer/caveat ("◯月◯日時点").
  3. Re-open every original link (still online, same wording).
  4. Fix time words that have gone stale (e.g. "10月22日発売予定" after the release, "今季ここまで17回" after the next race).
  5. Set `published` to the real publish time, remove `"draft"`, run `python3 build.py`, check on phone width, and publish together with the note article (same steps as §4–5).
