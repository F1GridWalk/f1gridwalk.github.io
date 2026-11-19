# サイト班へ：11/19 OFF GRID 8本、公開済み記事の直し3つ、ルールブックと人名表

## OFF GRID 8本（コミット a2453365、published 15:12〜15:19）
1. bearman-2027-contract-wait-20261119　ベアマン「かなり残念」　21戦目でも2027年の契約なし
2. cadillac-bottas-2027-20261119　ボッタス「僕は残ります」　キャデラックが2027年の続投を発表
3. mclaren-2027-car-auction-20261119　マクラーレン、走る前の2027年型F1を競売へ　届くのは2029年末
4. piastri-vegas-grid-penalty-20261119　ピアストリ、ラスベガスで10グリッド降格へ　5基目のエンジンで
5. v8-announcement-timing-20261119　FIA会長「V8エンジンはもうすぐやって来る」　関連の投稿はすぐ削除
6. mercedes-w17-update18-20261119　アリソン「車をもっと扱いにくくした」　王者メルセデスが失速した理由
7. monza-brakes-2026-20261119　ブレーキに厳しかったモンツァ　ブレンボ担当者「もうそうではない」
8. marco-antonelli-russell-luck-20261119　「事故をただの不運とは言えない」　アントネッリの父がラッセルに反論

案4はFIAの文書が出る前の「見通し」で書いています。FP1のあとFIAの降格の文書が出たら知らせてください（「降格へ」を直します）。

## 公開済み記事の直し（同じコミット、オーナーOK済み）
- lens/v8-engine-proposal-20261117：11/17のFIAの基本合意の発表は、SNSやFIAのサイトに出たあと短い時間で取り下げられていました（理由の説明なし）。先頭に【11月19日 追記】を足し、11/18の追記を「発表を出しました」「その発表の中で述べていました」「取り下げられた発表には入っていませんでした」に直しました。updated は 15:20。出典に Nextgen-Auto を足しました。
- lens/rosberg-ferrari-unclear-rules-20261107：「36万ドル」を「36万（ポンドともユーロとも報じられています）」に（dek と本文）。画像の上の見出しは「修理費36万」。
- lens/allison-2027-downforce-20261116：引用の枠（quote）に入っていた地の文の重複1つを消しました。

## ルールブック（コミット 764d1546）と人名表（a2453365）
- v8-era・hybrid-era：「基本合意したと発表した」を「基本合意したとする発表を出したが、短い時間で取り下げた（The Race）」に。checked 2026-11-19。
- people.json valtteri-bottas：avoid を「2028年以降の去就を決まったこととして書かない（2027年の続投は11/18に発表済み）」に。本文に11/18の発表を足し、F1公式の記事を出典に。

## サイトの要約で気づいたこと（直すかはお任せします）
- V8の基本合意を「発表した」と書いている要約が3つあります（articles.json の de-motorsportmagazin-v8-2030-einigung、nl-f1maximaal-fia-v8-akkoord など）。発表は短い時間で取り下げられたので、書き添えが必要だと思います。
- en-therace-cadillac-bottas-2027：題の「ハーツ」は「ハータ」（people.json の表記）。要約の「ブラジルGP」はサイトの表記では「サンパウロGP」。articles.json と news/archive.json の両方にあります。
- de-motorsporttotal-allison-w17-update18：アリソンの「おそらく（probably）唯一重さの下限に届いていた」から「おそらく」が抜けています。
- ハータの肩書きが people.json（テストドライバー）と topics/bottas-in-my-head-it-should-be-okay（リザーブ）で割れています。
