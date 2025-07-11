# TVOCセンサーロガー for Raspberry Pi

## 概要

このプロジェクトは、Raspberry Piを使用してTVOC（総揮発性有機化合物）センサーの値を監視し、Googleスプレッドシートに記録するためのアプリケーションです。設定した閾値を超えた場合には、LINEのグループに警告メッセージを送信する機能を持ちます。

Raspberry Piの電源投入時に自動的に実行されるよう、systemdサービスとして動作させることを前提として設計されています。

## 主な機能

-   **定周期でのデータ記録**: 10秒ごとにTVOCセンサーの値をppm単位で取得し、記録します。
-   **Googleスプレッドシートへの記録**: 取得したデータをタイムスタンプと共に指定のGoogleスプレッドシートに追記します。
-   **自動データクリーンアップ**: スプレッドシート上のデータが30日以上経過した場合、1日1回の頻度で自動的に削除し、常に最新1ヶ月分のデータを保持します。
-   **LINE警告通知**: TVOCの値が設定した閾値(0.6ppm)を10秒以上継続して超えた場合、LINE Messaging API (Push API) を通じて指定のグループに警告を送信します。
-   **通知クールダウン**: 一度通知を送信した後、30分間は再通知を行わないクールダウン機能を搭載し、通知の頻発を防ぎます。
-   **外部ファイルによる設定**: APIキー、シートURL、シート名などの設定は、すべて`.env`ファイルで管理します。
-   **サービスの自動起動**: `systemd`サービスとして登録することで、Raspberry Piの起動時に自動で監視を開始します。

## 必要なハードウェア

-   Raspberry Pi 本体 (Raspberry Pi OSがインストール済み)
-   TVOCセンサー (本プロジェクトの`lib/TVOC_Sense.py`と互換性のあるもの)
-   接続用のジャンパーワイヤー

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone <this-repository-url>
cd tvoc-raspberry
```

### 2. APIの準備

本プロジェクトではGoogleとLINEのAPIを使用します。それぞれ以下の準備を完了させてください。

#### Google Sheets API

1.  **Google Cloudプロジェクトを作成**し、**Google Drive API**と**Google Sheets API**を有効化します。
2.  **サービスアカウントを作成**し、「編集者」のロールを付与します。
3.  サービスアカウントの**キー（JSON形式）を作成・ダウンロード**し、プロジェクトのルートディレクトリに`service_account.json`という名前で配置します。
4.  記録先となる**Googleスプレッドシートを作成**します。
5.  スプレッドシートの「共有」設定で、サービスアカウントのJSONファイルに記載されている`client_email`（例: `...gserviceaccount.com`）を追加し、「編集者」の権限を与えます。

#### LINE Messaging API

1.  **[LINE Developersコンソール](https://developers.line.biz/ja/)**で、新規プロバイダーと**Messaging APIチャンネル**を作成します。
2.  作成したチャンネルの「Messaging API設定」タブで、**チャンネルアクセストークン（長期）**を発行し、控えておきます。
3.  LINEで通知を受け取りたい**グループを作成**し、作成したLINE Botをそのグループに招待します。
4.  そのグループの**グループID**を取得します。 (Botがグループに参加した際のWebhook等から取得)

### 3. ソフトウェアのインストール

```bash
# 仮想環境の作成
python3 -m venv .venv

# 仮想環境のアクティベート
source .venv/bin/activate

# 必要なライブラリのインストール
pip install -r requirements.txt
```

`requirements.txt`には、`gspread`, `python-dotenv`, `oauth2client`, `pyserial`, `gpiozero`, `RPi.GPIO` が含まれていることを確認してください。

### 4. 環境設定ファイルの作成

サンプルファイルをコピーして、実際の設定を記述します。

```bash
# .env.exampleをコピーして.envファイルを作成
cp .env.example .env

# nanoやvimなどのエディタで.envファイルを編集
nano .env
```

ファイル内の`YOUR_...`の部分を、ステップ2で準備した実際のキーやURL、IDに書き換えてください。

### 5. ユーザー権限の確認

`pi`ユーザーがシリアルポートやGPIOにアクセスするための適切な権限を持っているか確認します。通常はデフォルトで設定されていますが、念のため実行してください。

```bash
sudo usermod -a -G dialout,gpio pi
```

## 使い方

### 手動実行（テスト用）

設定が正しく行われているかを確認するために、手動でスクリプトを実行できます。

```bash
source .venv/bin/activate
python3 log_tvoc.py
```

### 自動実行（systemdサービスとして登録）

Raspberry Pi起動時に自動で実行するには、`systemd`にサービスとして登録します。

1.  **サービスファイルの配置**:
    サンプルファイルを`/etc/systemd/system/`にコピーします。
    ```bash
    sudo cp tvoc-logger.service.example /etc/systemd/system/tvoc-logger.service
    ```
    ※ファイル内のパス(`/home/pi/tvoc`)は、実際のプロジェクトのパスに合わせて適宜修正してください。

2.  **サービスの有効化と開始**:
    ```bash
    # systemdにサービスを認識させる
    sudo systemctl daemon-reload

    # OS起動時の自動起動を有効化
    sudo systemctl enable tvoc-logger.service

    # 今すぐサービスを開始
    sudo systemctl start tvoc-logger.service
    ```

### サービスの動作確認

```bash
# サービスのステータス確認
sudo systemctl status tvoc-logger.service

# リアルタイムログの確認 (-fオプション)
journalctl -u tvoc-logger.service -f
```

## 設定項目 (`.env`ファイル)

| 変数名                      | 説明                                                                                             | 例                                                                 |
| --------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `SPREADSHEET_URL`           | 記録先GoogleスプレッドシートのURL。                                                              | `https://docs.google.com/spreadsheets/d/123.../edit`               |
| `SERVICE_ACCOUNT_FILE`      | Googleサービスアカウントの認証情報JSONファイル名。                                               | `service_account.json`                                             |
| `SPREADSHEET_SHEET_NAME`    | (任意) 記録先のシート名。指定しない場合は最初のシートが使われます。存在しない場合は自動作成されます。 | `リビング`                                                         |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging APIのチャンネルアクセストークン。                                                 | `abc...`                                                           |
| `LINE_GROUP_ID`             | 通知を送信するLINEグループのID。                                                                 | `C123...`                                                           |