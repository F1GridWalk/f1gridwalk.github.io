# サイト担当へ：朝のコラムが共有キットと一覧に出ていなかった件（11/6）

コラム担当からです。オーナーから「朝のコラムが共有キットに載っていない」と指摘があり、調べて直しました。

## 1. 何が起きたか
- 対象：WORLD GRID /lens/alonso-competitive-p12-20261106/（11/6 6:24 公開）
- 公開のコミット 5b13a7b（Column alonso-competitive-p12-20261106）と ca4b8d9（Share image …）に、build.py で作り直された次のページが入っていませんでした。
  - share/index.html（共有キット）
  - columns/index.html（すべてのコラム）、lens/index.html（WORLD GRID の一覧）
- そのため、記事のページそのものは出ていましたが、共有キットと一覧には古いページが残っていました。
- 公開の手順で、build.py のあとに記事のファイルだけを選んで add したためだと思います（コミットの中身から見た推測です）。

## 2. 直したこと
- 6:5x に build.py をかけ直し、変わったファイル（60個。ほとんどは関連記事の欄などの作り直し）を全部コミットして反映しました（コミット defb877、deploy 成功）。
- 共有キットと一覧に、アロンソのコラムが出ていることを確かめました。

## 3. お願い
- 記事を公開するときは、build.py のあとに `git add -A`（または share/、columns/、lens/index.html、offgrid/index.html、deep/index.html、index.html、sitemap.xml を必ず含める）でコミットしてください。
- この公開をした手順（自動の作業か、ほかのセッションか）が分かれば、そちらの手順書にも同じことを足してください。
- コラム担当は、毎回 `git add -A` で公開しています。
