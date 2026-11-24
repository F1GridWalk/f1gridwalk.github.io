# サイト班へ：11/24 の OFF GRID 8本と、V8 の更新

## OFF GRID 8本（コミット 5158cab0、published 11/24 11:46〜11:53）
1. verstappen-qatar-rather-home-20261124　フェルスタッペン、カタールを前に「家にいたい」　それでも行く理由
2. bearman-haas-salary-stall-20261124　ベアマン「新しく言うことは何もない」　契約は給料で足踏みと報道
3. pu-supply-limit-2030-20261124　エンジン供給に上限案　独誌は6社合意、伊サイトは話し合いまだと
4. ferrari-leclerc-internal-sanction-20261124　フェラーリ、ルクレールに内部の処分か　罰金も排除せずと報道
5. gasly-engine-heat-fifth-20261124　ガスリー「表彰台はあった」　熱で約45周、出力を絞って5位
6. herta-leaves-f2-early-20261124　ハータ、F2を2戦残して離脱　ハイテックは来季の新加入を前倒し
7. russell-cooperation-radio-20261124　ラッセル「喜んでマックスと組むよ」　無線に返事なし
8. verstappen-mario-kart-20261124　フェルスタッペン、勝ったベガスを「マリオカート」にたとえる

題名・画像はオーナーの「OK」で、おすすめ（題名1・画像1）。

## V8 の更新（オーナーOK済み、コミット 0ea65895）
FIA は 11/20 に正式な発表文を出しました（https://www.fia.com/news/v8-future-unanimous-agreement-reached-fias-2030-formula-1-power-unit-framework ）。FIA・FOM・チーム・PUメーカーが2030年のPUの技術的な枠組み（2.1リッターV8ターボ、限られたハイブリッド）に全会一致で合意、最終的な枠組みは翌月上海の世界モータースポーツ評議会に出し、承認が条件。発表文に「原則合意」の言葉、電動のkW、評議会の日付はありません。
- lens/v8-engine-proposal-20261117、lens/v8-announcement-timing-20261119：冒頭に【11月24日 追記】、dek に一言、extraSources に FIA の発表文。
- deep/rules.json：hybrid-era、v8-era、boost-pressure、push-to-pass の本文を 11/20 の正式発表に合わせ、「取り下げた」は「削除した」に（合意の撤回と読まれないため）。
- deep/people.json：ビン・スライエム会長の avoid を「11/17 に消えた投稿を正式発表として書く」「11/20 の合意で規則が決まったと書く」の2つに直しました。
- FIA の公式の発表文は、FIA の文書・F1 公式の結果ページと同じく「参照」として扱い、複数のページで出典にしてよいことにしました（verstappen-mario-kart-20261124 と V8 の2本が同じ URL）。

## 気づいたこと（お任せします）
- lens の追記は前の追記に合わせて「取り下げ」、deep は「削除」です。サイト全体でそろえるかはご判断ください。
- 11/18 の追記にある会長の「この基本合意は…」（出典 PlanetF1）は、PlanetF1 の同じ URL が 11/20 の記事に書き換わったため、いまは確かめられません。
- 案6（ハータ）：タウリスCEO の言葉の元は F1 公式の記事（11/20）ですが、topics/perez-no-room-for-just-happy-to-be-here がすでに出典にしているので使わず、PlanetF1 の引用として書きました。
- 案4（フェラーリ）：内部の処分の話の元は La Gazzetta dello Sport（11/23）で、Grande Prêmio が引いたもの。トゥリーニの元の文章は Quotidiano Nazionale のブログ（11/22）。
