# Outlook / Microsoft 365 Graph Mail Setup Guide

見積アプリから顧客マスタ承認依頼・承認結果通知メールをMicrosoft Outlookで送信するため、Microsoft Graph API sendMail を利用しています。

## 目的

- 顧客マスタ申請時：管理者へ承認依頼メールを送信
- 顧客マスタ承認時：申請者へ承認結果メールを送信
- 顧客マスタ却下時：申請者へ却下結果メールを送信

## 必要な準備

### 1. Microsoft Entra ID（Azure AD）アプリ登録

社内IT部門またはMicrosoft 365管理者に以下の手順を実施いただく必要があります。

#### 手順

1. **Azure ポータルで新規アプリ登録**
   - https://portal.azure.com/ にアクセス
   - "Microsoft Entra ID" → "アプリの登録" → "新規登録"
   - アプリ名：例） "見積アプリ メール送信"
   - アカウントの種類：「この組織ディレクトリのみ」を選択

2. **ClientID と TenantID を取得**
   - アプリ登録後、以下をメモ：
     - Client ID（アプリケーション ID）
     - Directory ID（テナント ID）

3. **Client Secret を作成**
   - 左側メニュー "証明書とシークレット" → "シークレット"
   - "新しいクライアント シークレット" を作成
   - 説明：例） "見積アプリ メール送信"
   - 有効期限：組織ポリシーに従う（推奨：2年）
   - **シークレット値をメモ（画面を閉じると二度と表示されません）**

4. **Microsoft Graph API 権限を設定**
   - 左側メニュー "API のアクセス許可"
   - "権限を追加" → "Microsoft Graph"
   - "Application permissions" を選択
   - "Mail" → "Mail.Send" をチェック
   - "権限を追加" をクリック

5. **管理者の同意を付与**
   - 権限一覧で "Mail.Send" が表示されることを確認
   - "（テナント名）に対して管理者の同意を付与します" をクリック
   - 確認ダイアログで "はい" をクリック

### 2. 送信元メールボックスを決定

メール送信元として使用するメールアドレスを決定します。

推奨オプション：
- **共有メールボックス**（例：quotation-app@company.co.jp）
- **サービス用メールボックス**
- 特定の担当者メールボックス（非推奨）

**注意**：
- アプリが代わりにメール送信するため、監査ログを確認しやすい専用アドレスを推奨
- 個人用メールボックスは使用しないでください

### 3. 送信元メールボックスにアプリ権限を付与

社内IT部門で以下を実施：

- アプリの登録情報で "Mailbox.Migration" または "Mail.Send" をアプリに割り当て
- または、送信元メールボックスのプロパティで、登録済みアプリにメール送信権限を付与
  （具体的な手順は組織のIT部門に確認してください）

## 環境変数設定

上記で取得した情報を、アプリの環境変数に設定します。

### .env ファイルの作成

プロジェクトルートに `.`.env`` ファイルを作成：

```bash
MAIL_PROVIDER=graph

GRAPH_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
GRAPH_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
GRAPH_CLIENT_SECRET=your-client-secret-value
GRAPH_SENDER_USER=quotation-app@your-company.co.jp
```

### 各値の説明

| キー | 説明 | 例 |
|------|------|-----|
| MAIL_PROVIDER | メール送信方式（"graph" で Graph API使用） | graph |
| GRAPH_TENANT_ID | Microsoft Entra ID テナントID | 12345678-1234-1234-1234-123456789abc |
| GRAPH_CLIENT_ID | アプリ登録の Client ID | abcdef01-2345-6789-abcd-ef0123456789 |
| GRAPH_CLIENT_SECRET | クライアント シークレット（強い権限！） | xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
| GRAPH_SENDER_USER | 送信元メールアドレス | quotation-app@company.co.jp |

**セキュリティ注意**：
- `.env` は **絶対にGitにコミットしないでください**
- `.gitignore` に `.env` が含まれていることを確認
- Client Secret は漏洩に注意（定期的にローテーション）

## テスト手順

### 1. メール送信テストページでの確認

管理者ログイン後、以下にアクセス：

```
http://your-app/admin/mail-test
```

- 自分のメールアドレスを入力
- "テストメール送信" ボタンをクリック
- Outlookで該当メールを受信できれば成功

### 2. 顧客マスタ申請での確認

1. 一般ユーザーで新規顧客マスタを申請
2. 管理者のメールボックスに承認依頼メールが到着
   - From：GRAPH_SENDER_USER（quotation-app@company.co.jp）
   - Subject：「【見積アプリ】顧客マスタ承認依頼」

### 3. 顧客マスタ承認での確認

1. 管理者で顧客マスタを承認
2. 申請者のメールボックスに承認結果メールが到着
   - From：GRAPH_SENDER_USER
   - Subject：「【見積アプリ】顧客マスタ申請結果：承認」

## トラブルシューティング

### メール送信テストで失敗する場合

1. **環境変数が正しく読み込まれているか確認**
   - アプリケーションログで "[GRAPH MAIL]" で検索
   - エラーメッセージを確認

2. **Microsoft Graph APIの権限を確認**
   - Azure ポータルでアプリ登録 → API のアクセス許可
   - "Mail.Send" が "許可済み（管理者の同意）" になっているか確認

3. **Client Secret の有効期限を確認**
   - Azure ポータルで証明書とシークレット → シークレット
   - 有効期限が切れていないか確認

4. **GRAPH_SENDER_USER が正しいか確認**
   - メールアドレスのフォーマットが正しい
   - そのメールボックスが実在する

### ネットワーク接続を確認

- アプリサーバーから Microsoft Graph API エンドポイントへのHTTPS接続が可能か
- ファイアウォール・プロキシ設定を確認

### ログを確認

アプリケーションログで以下のキーワードで検索：

- `[GRAPH MAIL]` - Graph API関連のログ
- `token acquisition failed` - トークン取得失敗
- `status=` - HTTP エラーステータス

## トラブルシューティング後の確認

- アプリを再起動
- 再度メール送信テストを実施
- 問題が解決しない場合は、ログを収集して社内IT部門に相談

## 参考資料

- [Microsoft Graph sendMail API リファレンス](https://docs.microsoft.com/en-us/graph/api/user-sendmail)
- [MSAL for Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Azure アプリ登録ガイド](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)

---

**最終更新**：2026年5月
**作成者**：見積アプリ開発チーム
