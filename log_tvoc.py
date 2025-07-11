#coding: UTF-8
import sys
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

spreadsheet_url = os.getenv("SPREADSHEET_URL")
service_account_file = os.getenv("SERVICE_ACCOUNT_FILE")

print(f"スプレッドシートURL: {spreadsheet_url}")
print(f"サービスアカウントファイル: {service_account_file}")

if not spreadsheet_url or not service_account_file:
    print("エラー: .envファイルにSPREADSHEET_URLまたはSERVICE_ACCOUNT_FILEが設定されていません。")
    sys.exit(1)

try:
    # Googleスプレッドシートの認証
    print("Google APIの認証を開始します...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(service_account_file, scope)
    client = gspread.authorize(creds)
    print("Google APIの認証に成功しました。")

    # スプレッドシートを開く
    print("スプレッドシートを開いています...")
    spreadsheet = client.open_by_url(spreadsheet_url)
    sheet = spreadsheet.sheet1
    print(f"スプレッドシート '{spreadsheet.title}' のシート '{sheet.title}' を開きました。")

except gspread.exceptions.SpreadsheetNotFound:
    print("エラー: スプレッドシートが見つかりません。URLが正しいか、サービスアカウントに共有設定がされているか確認してください。")
    sys.exit(1)
except Exception as e:
    print(f"認証またはスプレッドシートを開く際にエラーが発生しました: {e}")
    sys.exit(1)


# Function to detect the Raspberry Pi model
def detect_model():
    try:
        with open('/proc/device-tree/model') as f:
            model = f.read().strip()
        print(f"Raspberry Piのモデルを検出しました: {model}")
        return model
    except FileNotFoundError:
        print("Raspberry Piではない環境で実行しています（テスト環境）。")
        return "Testing Environment"

# Detect the Raspberry Pi model and initialize the TVOC_Sense object
model_info = detect_model()
try:
    print("TVOCセンサーを初期化しています...")
    if "Raspberry Pi 5" in model_info or "Raspberry Pi Compute Module 5" in model_info:
        tvoc = TVOC_Sense.TVOC_Sense('/dev/ttyAMA0', 115200)
    else:
        tvoc = TVOC_Sense.TVOC_Sense('/dev/ttyS0', 115200)
    print("TVOCセンサーの初期化が完了しました。")
except Exception as e:
    print(f"TVOCセンサーの初期化中にエラーが発生しました: {e}")
    sys.exit(1)


def log_tvoc_data():
    """
    Logs TVOC data to the Google Sheet every 10 seconds.
    Also removes data older than one month.
    """
    print("センサーをクエリモードに設定します。")
    tvoc.TVOC_Set_Device_Query_Mode()
    
    # Add header row if the sheet is empty
    if not sheet.get_all_values():
        print("シートが空のため、ヘッダー行を追加します。")
        sheet.append_row(["Timestamp", "TVOC (ppb)"])

    print("データの取得と記録を開始します... (Ctrl+Cで停止)")
    while True:
        try:
            # Get data from sensor
            print("センサーからデータをクエリしています...")
            data = tvoc.TVOC_Get_Query_Device_Data()
            
            if data is not None:
                print(f"センサーからデータを取得しました: {data}")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                tvoc_value = data
                
                print(f"スプレッドシートに行を追加しています: {[timestamp, tvoc_value]}")
                sheet.append_row([timestamp, tvoc_value])
                print(f"記録成功: {timestamp}, {tvoc_value} ppb")

                # Clean up old data
                cleanup_old_data()
            else:
                print("センサーからデータが返されませんでした (None)。")

        except Exception as e:
            print(f"ループ内でエラーが発生しました: {e}")

        print("10秒待機します...")
        sleep(10)

def cleanup_old_data():
    """
    Removes rows from the sheet that are older than one month.
    """
    try:
        all_data = sheet.get_all_values()
        if len(all_data) > 1:
            one_month_ago = datetime.now() - timedelta(days=30)
            
            rows_to_keep = [all_data[0]]
            for row in all_data[1:]:
                try:
                    timestamp = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                    if timestamp > one_month_ago:
                        rows_to_keep.append(row)
                except (ValueError, IndexError):
                    rows_to_keep.append(row)

            if len(rows_to_keep) < len(all_data):
                print("古いデータをクリーンアップしています...")
                sheet.clear()
                sheet.append_rows(rows_to_keep)
                print("クリーンアップが完了しました。")
    except Exception as e:
        print(f"データクリーンアップ中にエラーが発生しました: {e}")


if __name__ == "__main__":
    try:
        log_tvoc_data()
    except KeyboardInterrupt:
        print("ロギングを停止しました。")