#coding: UTF-8
import sys
import requests
import json
from time import sleep
from lib import TVOC_Sense
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

print("スクリプトを開始します。")

# .envファイルから環境変数を読み込む
load_dotenv()
print(".envファイルを読み込みました。")

# --- 環境変数の読み込み ---
spreadsheet_url = os.getenv("SPREADSHEET_URL")
service_account_file = os.getenv("SERVICE_ACCOUNT_FILE")
sheet_name = os.getenv("SPREADSHEET_SHEET_NAME") # シート名を読み込む
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_group_id = os.getenv("LINE_GROUP_ID")

print(f"スプレッドシートURL: {spreadsheet_url}")
print(f"サービスアカウントファイル: {service_account_file}")
print(f"スプレッドシート名: {sheet_name if sheet_name else 'デフォルト（最初のシート）'}")
print(f"LINE Channel Access Token: {'設定済み' if line_channel_access_token else '未設定'}")
print(f"LINE Group ID: {'設定済み' if line_group_id else '未設定'}")

if not all([spreadsheet_url, service_account_file, line_channel_access_token, line_group_id]):
    print("エラー: .envファイルに必要な設定が不足しています。詳細は.env.exampleを確認してください。")
    sys.exit(1)

# --- Google Sheets APIのセットアップ ---
try:
    print("Google APIの認証を開始します...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(service_account_file, scope)
    client = gspread.authorize(creds)
    print("Google APIの認証に成功しました。")
    
    print("スプレッドシートを開いています...")
    spreadsheet = client.open_by_url(spreadsheet_url)
    
    # シートの選択または作成
    if sheet_name:
        try:
            sheet = spreadsheet.worksheet(sheet_name)
            print(f"指定されたシート '{sheet_name}' を開きました。")
        except gspread.exceptions.WorksheetNotFound:
            print(f"シート '{sheet_name}' が見つかりません。新しいシートを作成します。")
            sheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="2")
    else:
        sheet = spreadsheet.sheet1
        print(f"デフォルトのシート '{sheet.title}' を開きました。")

except Exception as e:
    print(f"Google Sheetsのセットアップ中にエラーが発生しました: {e}")
    sys.exit(1)

# --- TVOCセンサーのセットアップ (変更なし) ---
try:
    print("TVOCセンサーを初期化しています...")
    def detect_model():
        try:
            with open('/proc/device-tree/model') as f: model = f.read().strip()
            return model
        except FileNotFoundError: return "Testing Environment"
    model_info = detect_model()
    if "Raspberry Pi 5" in model_info or "Raspberry Pi Compute Module 5" in model_info:
        tvoc = TVOC_Sense.TVOC_Sense('/dev/ttyAMA0', 115200)
    else:
        tvoc = TVOC_Sense.TVOC_Sense('/dev/ttyS0', 115200)
    print("TVOCセンサーの初期化が完了しました。")
except Exception as e:
    print(f"TVOCセンサーの初期化中にエラーが発生しました: {e}")
    sys.exit(1)

# --- LINE通知関数 (変更なし) ---
def send_line_push_message(message):
    print(f"LINEプッシュメッセージを送信します: {message}")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {line_channel_access_token}"}
    payload = {"to": line_group_id, "messages": [{"type": "text", "text": message}]}
    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        print("LINEプッシュメッセージの送信に成功しました。")
    except requests.exceptions.RequestException as e:
        print(f"LINEプッシュメッセージの送信に失敗しました: {e}")
        if e.response: print(f"Response Body: {e.response.text}")

# --- メインロジック (変更なし) ---
def log_tvoc_data():
    print("センサーをクエリモードに設定します。")
    tvoc.TVOC_Set_Device_Query_Mode()
    if not sheet.get_all_values():
        print("シートが空のため、ヘッダー行を追加します。")
        sheet.append_row(["Timestamp", "TVOC (ppm)"])
    last_cleanup_time = None
    last_notification_time = None
    high_tvoc_start_time = None
    TVOC_THRESHOLD = 0.6
    NOTIFICATION_INTERVAL_SECONDS = 10
    COOLDOWN_MINUTES = 30
    print("データの取得と記録を開始します... (Ctrl+Cで停止)")
    while True:
        try:
            if last_cleanup_time is None or (datetime.now() - last_cleanup_time).days >= 1:
                cleanup_old_data()
                last_cleanup_time = datetime.now()
            data = tvoc.TVOC_Get_Query_Device_Data()
            if data is not None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sheet.append_row([timestamp, data])
                print(f"記録成功: {timestamp}, TVOC = {data:.3f} ppm")
                if data > TVOC_THRESHOLD:
                    if high_tvoc_start_time is None: high_tvoc_start_time = datetime.now()
                    if (datetime.now() - high_tvoc_start_time).total_seconds() >= NOTIFICATION_INTERVAL_SECONDS:
                        if last_notification_time is None or (datetime.now() - last_notification_time).total_seconds() > COOLDOWN_MINUTES * 60:
                            message = f"\n[警告] TVOC値が閾値({TVOC_THRESHOLD}ppm)を超えました。\n現在値: {data:.3f} ppm\n速やかに換気を行ってください。"
                            send_line_push_message(message)
                            last_notification_time = datetime.now()
                else:
                    high_tvoc_start_time = None
            else:
                print("センサーからデータが返されませんでした (None)。")
        except Exception as e:
            print(f"ループ内でエラーが発生しました: {e}")
        sleep(10)

# --- データクリーンアップ関数 (変更なし) ---
def cleanup_old_data():
    try:
        print("\n--- 1日1回のデータクリーンアップを開始します ---")
        all_data = sheet.get_all_values()
        if len(all_data) > 1:
            one_month_ago = datetime.now() - timedelta(days=30)
            rows_to_keep = [all_data[0]]
            for row in all_data[1:]:
                try:
                    if datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") > one_month_ago: rows_to_keep.append(row)
                except (ValueError, IndexError): rows_to_keep.append(row)
            if len(rows_to_keep) < len(all_data):
                print(f"{len(all_data) - len(rows_to_keep)}件の古いデータを削除します。")
                sheet.clear()
                sheet.append_rows(rows_to_keep, value_input_option='USER_ENTERED')
            else:
                print("削除対象の古いデータはありませんでした。")
        print("--- データクリーンアップを完了しました ---\n")
    except Exception as e:
        print(f"データクリーンアップ中にエラーが発生しました: {e}")

if __name__ == "__main__":
    try:
        log_tvoc_data()
    except KeyboardInterrupt:
        print("\nロギングを停止しました。")