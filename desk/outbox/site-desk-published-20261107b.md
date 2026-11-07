# サイト担当へ：11/7 夜に7本を公開しました

コラム担当からです。オーナーの OK をもらい、11/7 19:40 に7本をまとめて公開しました（コミット f1edf068）。build.py のあとは `git add -A` で、共有キット・一覧・sitemap も入っています。build.py は変えていません。

## 1. 公開したもの

OFF GRID（4本）
- /lens/verstappen-steering-workout-20261107/　フェルスタッペン「エンジンと話さなきゃいけないの？」　3番手でも不満が続いた金曜
- /lens/hamilton-young-drivers-respect-20261107/　41歳ハミルトン、若手の「本物の謙虚さと品位」をたたえる　400戦目を前に
- /lens/russell-engine-penalty-brazil-20261107/　ADUOのエンジンを待たずに5グリッド降格　ラッセル、今季2度目
- /lens/camara-reprimand-leclerc-20261107/　「明らかに危険」で戒告、でも「見事だった」　カマラのF1初日

WORLD GRID（2本）
- /lens/ferrari-longrun-gap-20261107/　フェラーリの金曜の遅れ、各国はどう測った？　補正の平均か、同じタイヤか
- /lens/racing-bulls-seats-undecided-20261107/　代表は「時間は味方」、ローソンは「ぼんやり」　レーシングブルズの2席

DEEP GRID
- #45 /deep/power-steering-heavy/　F1のステアリングは、なぜ「重く」なるのか　パワーステアリングとクラッチの決まり

どれも書き手→別の確認係で確かめています。WebFetch で開けない記事は、担当が内蔵ブラウザで開いて写し、それを一次資料にしました。

## 2. サイトの既存ページで気づいたこと（直していません）

1. **ラッセルのシンガポールのグリッド降格**
   - FIA の決定は2本で、10月9日に40（ICE・ターボ・排気・MGU-K が各10）、10月11日の予選のセッションで20（ES・CE が各10）、合わせて60です。
   - topics/russell-singapore-season-in-a-weekend は全体で「40グリッド」と書いていて、60に触れていません。「木曜に40と決まった」ともありますが、FIA の決定は10月9日（金）です。
   - lens/singapore-race-three-20261011 は、前半が「40」、後半が「正式には60」で、読み手に紛らわしくなっています。
   - deep/people.json と deep/rules.json は 40＋20＝60 で正しく書けています。
2. **レーシングブルズの代表の表記**
   - people.json は「アラン・パーメイン」です。ニュース要約に「ペルマン」「ペルマネ」が残っています（例：en-f1com-permane-racing-bulls-decision）。
3. **ハミルトンの「verbittert」**
   - news/de-motorsporttotal-hamilton-bitter-old-drivers の見出し「苦々しくなりたくない」は、Motorsport-Total の見出しの言葉です。記事の中のハミルトンの発言には「苦々しい」は出てきません。本人の言葉は「自分はそういうドライバーにならないようにしてきた」です。
4. **フェルスタッペンが FP2 を早く降りた理由**
   - F1 公式は「ステアリングのため」、Motorsport-Total はシュミッツの話として「技術的な問題はなく、ロングランのデータの乱れ」と書いていて、食い違っています。要約 de-motorsporttotal-verstappen-fp2-early-end は Motorsport-Total の側だけです（誤りではありません。コラムでは両方を書きました）。
5. **ブラッドリー・ロードの肩書き**
   - Motorsport-Total は「広報責任者」と書きますが、F1 公式によれば2026年3月20日から副代表です。people.json の表記（副代表）が正しいです。

## 3. 決めてほしいこと
- DEEP #45 に出てくるデザイナー「ヴィリー・ランプ」は、サイトで初めて出る名前です。「ウィリー・ランプ」と書く媒体もあります。どちらかに決めたら、こちらで直します。

## 4. note・X の素材
- reserve の daily/2026-11-07/ に、6本の note 原稿・見出し画像・X 画像、DEEP #45 の note 原稿、X投稿_1107b.md を入れました。
