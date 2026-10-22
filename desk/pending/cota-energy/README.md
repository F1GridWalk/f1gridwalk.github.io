# DEEP #18 cota-energy（公開待ち）
- オーナーの決定（10/22 17:12、「OK」でおすすめの組み合わせ）：タイトル T1「アメリカGPのCOTAでは、なぜ電気のやりくりが難しいのか」、見出し画像 E1、公開は 10/23 の朝（FP1 の前）。
- cota-energy.json は確認済み（.v.json）。draft: true のまま。og.png は E1 を 1203×630 に縮めて (1,0,1201,630) で切ったもの。
- 公開手順：main を pull → deep/cota-energy.json にコピー → draft を外し、published を実際の時刻（+09:00）、history [["2026-10-23","公開。"]] → deep/cota-energy/og.png に og.png → python3 build.py → rm -rf __pycache__ → commit → pull --rebase → push → Actions 確認。
- そのあと note 素材：tools/col_assets_deep.py（入力例 daily/2026-10-22/note_deep-cost-cap-loophole_input.json）、見出し画像は E1.png、X 用は E1.html の高さを 720 にして 1.5 倍で撮る。貼り付けページ（Artifact、downloads）、note 掲載イメージPDF、X投稿①②③。reserve の daily/2026-10-23/ に保存。
