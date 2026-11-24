# F1 Grid Walk

世界のF1報道を、日本語で読み比べる非公式ファンサイトです。毎日更新しています。

- サイト: https://f1gridwalk.github.io/
- 運営者情報・編集方針: https://f1gridwalk.github.io/about/

## サイトの中身

- **ニュース**（/news/）… 海外と日本のF1媒体の記事から、見出しの翻訳と独自の短い要約、原文へのリンク
- **毎日のまとめ**（/news/daily/日付/）… その日の主なニュースを1ページに
- **STORY**（/topics/）… レースの印象的な場面を、世界の報道から読み解く独自記事
- **STORYLINE**（/storyline/）… 続いている話題・決着した話題を、始まりから時系列で
- **WORLD GRID**（/lens/）… 海外報道の読み比べコラム
- **DEEP GRID**（/deep/）… ニュースの「なぜ」を掘り下げる解説
- **OFF GRID**（/offgrid/）… こぼれ話
- **用語・人物辞典**（/deep/rules/）… F1の用語とルール、ドライバー・エンジニア・チーム代表など
- **ドライバー**（/drivers/）、**チーム**（/teams/）、**GP**（/gp/）

## データとしくみ

- `articles.json` … 新しいニュース（毎日自動更新）。過去の分は `news/archive.json`
- `season.json` … 今週のグランプリ・ランキング・カレンダー
- `teams.json` / `circuits.json` … チームとコース図のデータ（コース図: bacinger/f1-circuits, MIT License）
- `deep/people.json`、`deep/rules.json` … 人物辞典と用語辞典
- `topics/*.json`、`lens/*.json`、`deep/*.json` … STORY、コラム、DEEP の元データ
- `build.py` … すべてのページを作るプログラム（`python3 build.py`）
- `tools/validate_site.py` … 作ったページの自動チェック（題名・正規URL・日時・リンク・サイトマップ）。公開前に実行
- `.github/workflows/validate.yml` … main に push するたびに上のチェックを GitHub でも実行。ERROR があると赤くなりメールが届く（公開は止めない）
- `tools/source-names.json` … 同じ媒体の名前のゆれをまとめる表
- `gpdata/<gp-slug>.html` … データ分析の係のレース分析ページ。build.py が /gp/<gp-slug>/data/ として出す。`tools/gpdata_import.py` で Artifact の HTML から作る
- `gpdata/<gp-slug>.links.json` … そのレースのニュースから分析ページへのリンクを出す話題と、最初から選んでおくドライバー（手で選ぶ）
- `tools/indexnow.py` … 更新したページを Bing などに知らせる
- `tools/bluesky.py` … 新しいコラムと STORY を Bluesky に投稿する（設定したときだけ動く）

F1 Grid Walk は Formula 1 および FIA とは関係ありません。記事の著作権は各媒体に帰属します。
