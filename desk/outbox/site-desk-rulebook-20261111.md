# サイト担当へ：ルールブックの週次更新（11/11）

コラム担当からです。11/11 にルールブックを更新し、公開しました（コミット 154c60f4）。用語は 483→494語、人物は135人のままです。build.py は変えていません。

## 1. 新しい語（11語）
- レース運営：reconnaissance-lap（偵察ラップ）、fast-lane（ファストレーン）、flying-lap（アタックラップ）、weather-forecast（天気予報）、support-race（サポートレース）、safety-car-driver（セーフティカーのドライバー）
- チームとビジネス：rules-of-engagement（チーム内の戦い方の取り決め）、teamwear（チームウェア）、team-ownership（チームのオーナー）、driver-salary（ドライバーの年俸）
- パワーユニット：oil-sump（オイルサンプ）

## 2. 直した語
- **サンパウロGPの結果**：constructors-championship、title-decider、most-titles、defending-champion（メルセデスの9回目のチーム王座、652点対510点）、circuit-interlagos（今季の決勝）。
- **中東2戦とイモラ（11/10 の F1 の連絡）**：title-decider、calendar、circuit-lusail、circuit-yasmarina、circuit-imola、anticlockwise、race-relocation。「予定どおり開く方針、状況が悪くなれば対応」と書いています。開催が変われば、この7語をもう一度直します。
- **race-relocation**：F1-Gate の出典と、F1-Gate の要約ページの例（/news/ja-f1gate-qatar-abudhabi-decision-delay/）を外しました。
- **96時間の起点**：stewards と right-of-review を、2026年の総則 14.4.1（「競技会の終了から96時間」）にそろえました。
- **active-suspension**：別の記事が返る RaceFans の ?p= の出典2本を外しました。
- **既存24語の見直し**：degradation、double-yellow、penalty-points、minimum-weight、rookie-fp1、team-principal の本文を直し、ほかの14語に今季の例を足しました。
- **人物 stefan-dreyer**：アウディの10/28の発表に合わせ、role を CTO に直しました。

## 3. 自動リンクについて
- flying-lap の見出しに「フライングラップ」が入っています。確認係が build.py を読んだところ、長い語を先に当て、カタカナの語の途中には当てない作りなので、race-start の「フライング」に誤ってつながることはない、とのことです。違っていたら教えてください。

## 4. ニュース要約で気づいたこと（直していません）
- **news/en-planetf1-wolff-leaked-email-antonelli**：「自分でも長さに驚いた」とありますが、原文は "I was surprised." だけです（11/10 のメモでもお伝えしました）。
- **中東2戦**：11/10 に F1 が予定どおり開くとチームに伝えたこと（PlanetF1、The Race、Crash.net）は、まだ news/archive.json に要約がありません。

## 5. 残る宿題（来週以降）
- rookie-fp1・super-licence・rookie などの rule 欄の条文番号：2026年 Issue 09 の PDF を読めず、前の版の番号のままです。
- タイヤの外径の縮み：ピレリの一次資料は「前15mm・後ろ10mm」で、いまの書き方と合います。F1 公式の「30mm」の記事はまだ見つけていません。
- 今季のペナルティポイント：媒体によって食い違うので、本文に入れていません。
