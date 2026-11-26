# lab（非公開の分析ページの作業場所）

このブランチは Pages に出ません。サイトに出すのは、サイト作者が main で取り込んでから（オーナーの OK のあと）。

## レースの日の手順（データ分析の係）
1. `lab/fetch.txt` にレースの行を足す（例：`2026 "Qatar" R 22`）。決勝が終わり、正式結果が出てから push する。
2. push すると GitHub Actions が動く：データを `lab/data/<年>-<gp>-R.json` に取り、
   `lab/page/races/<年>-<gp>.json` があれば `lab/pages/<年>-<gp>.html` も作ってコミットする。
3. 手元で pull して、ページを作り直しながら選ぶ：
   `python lab/page/make_page.py lab/data/2026-qatar-R.json lab/page/races/2026-qatar.json /tmp/qatar.html`
   - 画面に「できごとの候補」（レースコントロール）と「1周で大きく順位を落とした人」が出る。
   - `races/<id>.json` の `ev`（▼の印）と `news`（DATA STORY の関連ニュース。サイトの news/archive.json から）を手で入れる。
   - DNF / DNS / DSQ は OpenF1 の結果から自動。プリセットは、なければ結果から自動（上位3チームのチームメイトと、1位対2位）。
4. できた HTML を Artifact に出して、オーナーに見せる。OK のあと、プロジェクトに「…to-site-desk」のメモ（版、ニュースとドライバーの組み合わせの案）。
5. サイト作者が `tools/gpdata_import.py` で取り込む（ページの形は前と同じ）。

## ファイル
- `fetch_race.py`：OpenF1 などからデータを取る。`session_key` と取得時刻も保存する。
- `page/template.html`：ページのひな形（ラスベガスの Version 11 から、レースごとの部分を外したもの）。
- `page/make_page.py`：データ＋レースの設定 → ページ。
- `page/drivers_2026.json`：ドライバーのカタカナの姓・チーム名・色。サイトのドライバーの辞典はこの姓と3文字で合わせているので、書き方を変えない。新しい人が出たら足す（足していないと警告が出て、英語の名前になる）。
- `page/races/<id>.json`：レースごとに人が選ぶもの（名前、GP ページの slug、現地の時差、ev、news、プリセット）。

## 自動で出るもの・出ないもの
- 出る：順位・差・ペース・タイヤ・スティント・比較のデータ、セーフティカーとバーチャル・セーフティカーの帯（何回でも）、ゴールの差（正式結果と1.5秒以内で合うとき）、DNF/DNS/DSQ、見出しの日付（日本時間と現地）、DATA UPDATE、session_key。
- 出ない（人が選ぶ）：▼のできごと、DATA STORY の関連ニュース。理由（接触、故障など）はページに書かない。
- まだ対応していない：赤旗の中断（帯は出ない）。
