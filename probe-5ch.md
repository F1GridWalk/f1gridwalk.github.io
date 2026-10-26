# 5ch 到達性テスト結果（2026-10-26）

結論：今回の実行環境からは 5ch（5ちゃんねる）に到達できませんでした。スレッドは1件も開けず、ファンの反応の要約はありません。

## 試行一覧

| # | URL / クエリ | ツール | 結果 |
|---|---|---|---|
| 1 | https://5ch.net/ | curl（シェル） | 失敗：`curl: (56) CONNECT tunnel failed, response 403`（エグレスプロキシが connect_rejected、ホスト未許可） |
| 2 | https://egg.5ch.net/ | curl | 失敗：同上（403 / connect_rejected） |
| 3 | https://itest.5ch.net/ | curl | 失敗：同上（403 / connect_rejected） |
| 4 | 検索「5ch F1 アメリカGP 決勝 スレ」 | WebSearch | 実行できたが、5ch のURLは1件も含まれず（as-web.jp、response.jp、honda.co.jp 等のニュース／結果ページのみ） |
| 5 | 検索「5ちゃんねる F1板」 | WebSearch | 実行できたが、5ch のURLは含まれず（impress、gigazine のドメイン関連記事、wiki 系など） |
| 6 | https://egg.5ch.net/f1/ | WebFetch | 失敗：`PROVENANCE_REQUIRED`（許可リクエストに時間内に応答がなく取り下げ。無人実行のため） |
| 7 | https://itest.5ch.net/egg/f1 | WebFetch | 失敗：`PROVENANCE_REQUIRED`（同上） |

read.cgi 形式のスレッドURLは、検索結果に出てこなかったため試していません（URLを推測で組み立てると許可が必要になるため）。他のミラー／ビューアのURLも検索結果には現れませんでした。

## スレッドの内容

開けたスレッドはなく、閲覧できた投稿数は0件です。ファンの反応の要約は作成できません。

## 所見

- シェルからの直接アクセスは、プロキシのドメイン許可リストで 5ch.net 系が拒否される（claude.ai の設定 > 機能でドメイン許可を追加しない限り不可）。
- WebFetch は無人実行では URL の許可が得られず、検索結果に出ない URL は取得できない。
- 今のところ、5ch を「ファンの声」の情報源として自動取得するのは現実的ではない。
