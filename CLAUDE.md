# S-CART-Quotation（見積アプリ）

武蔵精密工業 S-CART（AGV/AMR）の概算見積アプリ。Flask + SQLite、Jinja2 + バニラJS。
開発の主担当は Claude Code。会話をまたぐと記憶は残らないため、方針・決定事項はこのファイルに書く。

## 方針（最重要）
- **工数と仕様はシミュレーター(`C:\Users\3950\RCS Simulator`)だけが算出する。** 見積アプリは係数で工数を計算しない。
  シミュレーターが出した項目別工数(h) × 賃率 を明細にして見積書にする役に徹する。
- 連携は一方向。金額・原価はシミュレーター側に持たせない。シミュレーターUIに「見積」の語を出さない。
- **自動で作る明細は「設計費／現地セットアップ費」の工数行だけ。** 機種・台数・オプションは自動連携しない（製品マスタは手動で登録・削除でき、シミュレーターと紐づけない）。`vehicles.model/count/spec_text` は参考表示と書面の前提のみ。
- 賃率: 原価 6,820円/h・販売 12,000円/h（`V2CalculationSetting` の行 id=1。既存DBは `scripts/set_v2_rates.py` で反映）。
- 工数項目はシミュレーターが実際に出せるものだけ。S9「設備連携・I/O試験」は、シミュレーターの仮想設備シミュレーション(ロードマップ07)実装まで入れない。
- 初回スコープは概算見積のみ。正式見積は従来フロー。

## 取り込みの仕組み
- 契約: `scart-sim-result/1`（JSON、クリップボード貼り付け。ファイルは作らない）。定義と検証は `app/sim_import.py`。
- `POST /quotation/sim-import/preview`（`app/routes/quotation.py`）が検証し、工数×賃率の明細行を返す。画面は `app/static/js/quotation/sim_import.js`。
- 工数行は既存V2行と同じ形式で保存（数量1・金額/原価は合計。数量は整数に丸められるため時間は説明文に入れる）。
- 保存形式: `quotations.v2_input_json = {"source","sim","rates","lines"}`。`lines` は `{kind,item_id,item,hours,basis,orig_hours,reason,source}`。
- シミュレーター由来の行は元の値から変えるとき**理由必須**（サーバー側でも検証）。手入力行は理由不要。賃率は保存時の値を記録（後の賃率変更で既存見積の金額を変えない）。
- お客様向け書面（印刷・PDF）は項目別の工数を「設計費」「現地セットアップ費」の2行にまとめる（`aggregate_effort_details`）。調整理由・内訳は載せない。備考欄に「シミュレーション前提」を出す。
- 旧V2ウィザード（`v2_core*.js`, `v2_sync.js`, `cost_utils.py`, `/admin/v2-parameters`）は画面から外れて未使用。削除は整理タスクで行う。既存見積の表示・改訂は壊さないこと。

## 運用形態
- 各PCにEXE、**DBは共有フォルダの1つ**（`SCART_DB_PATH`）。複数人が同時に使うため SQLite は WAL を使わない（共有フォルダ越しでは壊れる）。`journal_mode=DELETE`、`busy_timeout=30s`（`app/__init__.py`、`SCART_JOURNAL_MODE` で変更可）。
- DBバックアップ: `python scripts/backup_db.py [先] [保持日数]`（稼働中でも安全）。既存DBを持ち込むときはこれで作ったコピーを使う（`-wal/-shm` を直接コピーしない）。
- `SECRET_KEY` 未設定の本番起動は、DBと同じフォルダに `.secret_key` を作って使い回す。

## コマンド
- 開発起動: `python run.py`（127.0.0.1:5000、`FLASK_DEBUG=1` でデバッグ）
- 本番起動: `python serve.py`（waitress。`SCART_HOST` / `SCART_PORT`）
- テスト: `python -m pytest`（`tests/`。変更のたびに実行。画面操作系の確認は一時DBで `serve.py` を起動して行う）
- EXE: `scart_quotation.spec`（PyInstaller）。`build/` と `dist/` は生成物でコミットしない。
- 初期管理者: `admin` / `admin1234`（空DB起動時に作成。初回ログイン後に必ず変更）

## 構成
- `app/__init__.py` アプリ生成・起動時マイグレーション（生SQL）。`app/routes/quotation.py` 見積の中心（約1,700行、POSTが長い）。
- `app/models/`、`app/services/quotation_pdf_service.py`（ReportLab、固定レイアウト）、`app/templates/quotation_print_direct.html`（A4印刷）。
- 明細の保存は `description[] / unit_price[] / quantity[] / subtotal[] / cost[] / product_id[]` の配列フォーム。`cost[]` の意味が通常行（単価）と工数行（合計）で違う点に注意。

## 作業ルール
- コミット・プッシュ・PR作成は、ユーザーに頼まれたときだけ。コミットはソースのみ（`build/` `dist/` は含めない）。
- 変更したら `python -m pytest` を通す。触る範囲にはテストを足す。
- UIテキストは日本語。既存の書式（CRLF/LF、BOM付きファイルあり）を壊さない。
- シミュレーター側を変更するときは、そちらの `.specify/memory/constitution.md` に従う（先にspec作成、バックアップ手順）。

## 既知の課題
- `quotation.py` が巨大。ルートに検証用PDF・ログ・重複JS/テンプレートが散在。`debug=True` 由来の設定が残る箇所あり。
- 工数式の旧系統（`cost_utils.py`）と旧ウィザードが未使用のまま残っている。
- 印刷画面は明細15行まで、備考欄は固定高さ。前提を載せた状態での1ページ収まりは実機の印刷プレビューで要確認。
