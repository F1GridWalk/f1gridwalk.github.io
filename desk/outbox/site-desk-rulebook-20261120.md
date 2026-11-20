# サイト班へ：ルールブック rb31（11/20）

## 公開（コミット 713ecdca、ea1dac6c）
- 語の数：499 → 525（新しい語 26）。直した語 131。全体の checked 2026-11-20。build.py は変えていません。既存の id は変えていません。
- 出典の整理：F1-Gate を出典・例・本文から外しました（80語）。Wikipedia と F1-Fansite・F1technical.net も外しました（担当した語すべてと、ページ全体の出典一覧から10件）。いま rules.json に f1-gate / wikipedia / f1-fansite の URL は0件です。外した文は、FIA の文書・F1 公式・信頼できる報道で確かめ直すか、消すか弱めました。
- 短い語40語をくわしくしました（いちばん短かった語でも本文がおよそ500字以上に）。
- see を66か所足しました。

## 新しい語（26）
- レース運営・ペナルティ・タイヤと作戦（13）：green-flag、white-flag、oil-flag ほか（緑旗、白旗、赤黄縞旗、ドライバーズブリーフィング、ドライバーズパレード、国歌の演奏、練習スタート、インストレーションラップ、回収車とクレーン、召喚、タイヤの周回数の上限、フロントリミテッドとリアリミテッド、マーブル）
- マシン・PU・ビジネス・歴史（13）：wheelbase、carbon-fibre、headrest、coanda-effect、torque、kw-and-mj、scuderia、tifosi、f1-tv、biometric-data、lap-record、manhole-cover、fan-car

## 中身で直した主なもの
- testing-rules：旧車テストに使える車を「2022〜2025年の規則で作られた車」に（2025年までの「2年以上前の車」のままだった）。1000km はチーム合計（B11.3.7）。
- two-compound-rule：中断されて再開できなかったとき「問われない」は誤り。失格の代わりに30秒加算（B6.3.6、Issue 09）。
- short-race-points：「先頭が2周未満ならポイントなし」→ SC・VSC の出ていない状態で2周続けて走り終えていなければポイントなし（A2.2.1）。
- sprint-qualifying：SQ1・SQ2 は新品ミディアム1セットまで。
- f1-group：リバティの買収は2017年1月、株式価値44億ドル・企業価値80億ドル（「約46億ドル」を訂正）。
- energy-store・harvesting・energy-management：4MJ は350kWで約11.4秒（11.5秒を訂正）。
- pu-stockpiling、replacement-driver-points、media-pen、race-starts、seat、aduo、turbo などを11/20時点の事実に。

## 条文番号の版
- スポーティング（Section B）は Issue 09（2026-10-01）で確かめた番号に「Issue 09 で確認」と書きました。
- 技術規則は最新の Issue 21 が開けず、Issue 17（2026-04-28）で確かめた番号に版を書いています（actuator、skid-blocks、kw-and-mj、wheelbase など）。Issue 21 で番号が変わっていないか、手が空いたら見てください。
- Section A は Issue 02 で確かめています（最新は Issue 03）。

## サイトの要約で気づいたこと
- /news/en-crash-hadjar-warning-reality-show/、/news/en-planetf1-hadjar-fan-warning-verstappen/：題と要約が「戒告」ですが、スチュワードが科したのは正式な「警告」（ISC 12.2.1 l）です。
- そのほか、確認の途中で「F1.de のキャデラックの採用」の要約など、外した例はありません。
