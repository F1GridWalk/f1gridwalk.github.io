# サイト作者へ：検索の言葉 第2回（11/6）で直したページ

コラム担当からです。依頼（column-desk-search-words-20261106.md）の分を、書き手→別の確認係で確かめて公開しました（11/6 0:52 のコミット fa1ef77。反映はそのあとの c91785c 〈サイト作者の push〉でいっしょに成功）。build.py は変えていません。用語は483語、人物は135人です。

## 1. 人物（Google への登録リクエストの候補）
| ページ | 直したこと |
|---|---|
| /deep/rules/person-peter-bonnington/ | body を新しく：「## 経歴」「## アントネッリとの無線」。冒頭近くに「愛称はボノ」。STORY /topics/bono-first-chapter/ と /topics/antonelli-champion-of-the-world/ へリンク。別名「ピーターボニントン」 |
| /deep/rules/person-kimi-antonelli/ | body を新しく：「## プロフィール」（国籍、生年月日、12番の由来＝本人の発言で3つの理由）「## 経歴」「## 2026年の王座」。別名「キミアントネッリ」 |
| /deep/rules/person-isack-hadjar/ | body を新しく（国籍、経歴、2026年のレッドブル）。別名「アイザックハジャー」 |
| /deep/rules/person-shintaro-orihara/ | 「## 経歴」に、大阪市立大学の機械工学科に入学したこと（Car Watch 2023年6月29日。原文は「入学」なので「卒業」とは書いていません） |
| /deep/rules/person-carlo-santi/ | 短い body（担当になった経緯、ハミルトンとの無線）。別名「カルロサンティ」 |
| /deep/rules/person-colton-herta/ | スーパーライセンスの点の段落（39点・40点が必要・IndyCar 公式の順位表の誤り）。用語 /deep/rules/super-licence/ と DEEP super-licence-points へリンク。別名「コルトンハータ」 |
| 正ドライバー6人：person-lando-norris、person-oscar-piastri、person-george-russell、person-max-verstappen、person-charles-leclerc、person-lewis-hamilton | body に「## プロフィール」「## 経歴」「## 2026年」（数字は「メキシコシティGP終了時点」）。中黒なしの別名（ランドノリス など） |

- 「アイザック・ハジャー」「カルロ・サンティ」「コルトン・ハータ」「ジャンピエロ・ランビアーゼ」は name と同じ文字列なので、別名には足していません（サイト内検索は中黒などを消してから照らすと聞いています。違っていたら教えてください）。ランビアーゼは変更なしです。
- 正ドライバーの残り14人は、次の回で順に足します。

## 2. 用語
| ページ | 直したこと |
|---|---|
| /deep/rules/pit-lane-start/ | 小見出し「## どんなときにピットレーンスタートになるのか」「## 有利・不利（最後尾スタートとの違い）」に組み直し |
| /deep/rules/world-champion/ | short を「その年のドライバーズ選手権で1位になったドライバー。…2026年はアントネッリ…」に |
| /deep/rules/reserve-driver/ | examples に平川亮のコラム2本（hirakawa-f1-debut-20261101、hirakawa-first-point-20261102） |
| /deep/rules/blue-flag/ | examples に /lens/sainz-blue-flags-20261030/。依頼の表には「メキシコ」とありましたが、コラムの場面はアメリカGPの36周目なので、そう書いています |
| /deep/rules/vsc/ | 別名「バーチャルセーフティーカー」 |
| /deep/rules/driver-count/（新しい用語） | 「F1のドライバーの人数」：2026年は11チーム22台・正ドライバー22人、1チームが使えるのは4人まで、交代と代役、リザーブとテストドライバー、若手のFP1/FP2走行 |

- active-aero は、「## DRSとの違い」がもう本文にあり、drs にもつながっていたので変えていません。

## 3. 気づいたこと・相談
- **条文の版**：pit-lane-start の B3.5.3・B5.3.1・B5.6.4・B5.7.3 は、Issue 09 の PDF が開けず、Issue 07（6/25）で確かめた番号です（rule 欄に版を書いています）。driver-count の A2.1.3 も Section A Issue 02 で確かめたものです。Issue 09／Issue 03 で同じ番号か確かめられたら、版を直します。
- **rookie-fp1**：Issue 09 の B1.7.3 は「FP1 or FP2」ですが、rookie-fp1 は「FP1」だけの書き方です。rule 欄の「1セッション2人まで」も、Issue 09 では B1.7.4 b. にあります。次の週次更新で直します。
- **短い別名**：アントネッリの「キミ」、ハジャーの「アイザック」は、ほかの人（キミ・ライコネンなど）にも当たりうる語です。既存なので残しています。外してよいか教えてください。
- **ハータ**：サンパウロGP の FP1（現地11/6）を走ると「報じた」形で止めています。走ったら short と body を直します。
- ハジャーの出典に F1-Gate が1件残っています（既存の出典なので外していません）。
