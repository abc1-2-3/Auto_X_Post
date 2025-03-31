from io import BytesIO
import os
import requests
import base64
from PIL import Image
from requests_oauthlib import OAuth1
import time
import json
import datetime
import logging

# 取得當前檔案的目錄
BASE_DIR = os.path.dirname(__file__)

# 確保 config.json 的路徑正確
config_path = os.path.join(BASE_DIR, "config.json")

# 讀取 config.json
with open(config_path, "r", encoding="utf-8") as config_file:
    config = json.load(config_file)

X_API_KEY = config["X_API"]["API_KEY"]
X_API_SECRET = config["X_API"]["API_SECRET"]
X_ACCESS_TOKEN = config["X_API"]["ACCESS_TOKEN"]
X_ACCESS_SECRET = config["X_API"]["ACCESS_SECRET"]
BEARER_TOKEN = config["X_API"]["BEARER_TOKEN"]
SIGNATURE = config["CONTENT_SIGNATURE"]["SIGNATURE_HANGFIRE"]
# OAuth 1.0a 驗證
auth = OAuth1(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)

#上傳圖片
def upload_media(image_data):
    try:
        url = "https://upload.twitter.com/1.1/media/upload.json"  # 使用 v1.1 的上傳端點
        total_bytes = len(image_data.getvalue())
        print(total_bytes)
        init_params = {
            "media_type": "image/PNG",  # 根據你的圖片類型調整
            "total_bytes": total_bytes,
            "command": "INIT"
        }
        files = {
            "media": image_data.getvalue() # 圖片的二進制數據
        }
        # 使用 OAuth 1.0a 驗證
        init_response = requests.post(url, data=init_params, auth=auth)
        if init_response.status_code != 202: # `202 Accepted` 表示初始化成功
            logging.error(f"INIT 失敗，錯誤碼 {init_response.status_code}")
            logging.error(f"伺服器返回內容：{init_response.text}")
            return None
        media_id = init_response.json()["media_id_string"]
        # Step 2: APPEND (上傳圖片數據)
        append_params = {
            "command": "APPEND",
            "media_id": media_id,
            "segment_index": 0# 單張圖片可以用 0，若有多個片段，需依序增加
        }
        #files = {"media": image_data.getvalue()}  # 這裡要傳送二進制數據
        time.sleep(1)
        append_response = requests.post(url, data=append_params, files=files, auth=auth)
        if append_response.status_code != 204:# `204 No Content` 表示 APPEND 成功
            logging.error(f"APPEND 失敗，錯誤碼 {append_response.status_code}")
            logging.error(f"伺服器返回內容：{append_response.text}")
            return None
        # Step 3: FINALIZE (完成上傳)
        finalize_params = {
            "command": "FINALIZE",
            "media_id": media_id
        }
        time.sleep(1)
        finalize_response = requests.post(url, data=finalize_params, auth=auth)
        if finalize_response.status_code not in [200, 201]:  # 201 也是成功
            logging.error(f"FINALIZE 失敗，錯誤碼 {finalize_response.status_code}")
            logging.error(f"伺服器返回內容：{finalize_response.text}")
            return None
        finalize_data = finalize_response.json()
        print("FINALIZE 成功！")

        # 4️⃣ `STATUS` 等待圖片處理完成
        if "processing_info" in finalize_data:
            state = finalize_data["processing_info"]["state"]
            while state not in ["succeeded", "failed"]:
                print(f"等待圖片處理中... (當前狀態: {state})")
                time.sleep(2)  # 等待 2 秒後重新查詢

                status_params = {"command": "STATUS", "media_id": media_id}
                status_response = requests.get(url, params=status_params, auth=auth)

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    state = status_data["processing_info"]["state"]
                else:
                    logging.error(f"STATUS 查詢失敗，錯誤碼 {status_response.status_code}")
                    logging.error(f"伺服器返回內容：{status_response.text}")
                    return None

            if state == "failed":
                logging.error("圖片處理失敗！")
                return None

            print("圖片處理完成！")
        return media_id
    except Exception as e:
        logging.exception("上傳圖片時發生異常")
        return None


def post_tweet(text, media_id=None):
    try:
        url = "https://api.twitter.com/2/tweets"
        headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}",  # 這裡要用 Bearer Token
            "Content-Type": "application/json"
        }
        payload = {"text": text}

        if media_id:
            payload["media"] = {"media_ids": [media_id]}  # 附加圖片 ID

        response = requests.post(url, json=payload, auth=auth)

        if response.status_code == 201:
            logging.info("推文發送成功！")
            logging.info(response.json())
        else:
            logging.error(f"推文發送失敗，錯誤碼 {response.status_code}")
            logging.error(f"伺服器返回內容：{response.text}")
    except Exception as e:
        logging.exception("發送推文時發生異常")


def upload_and_post(text,pic):
    try:
        now = datetime.datetime.now()
        formatted_time = now.strftime("%Y-%m-%d %H:%M")  # 年-月-日 時:分:秒
        tweet_text = "【"+formatted_time+"】"+"\n\n"+text+"\n\n"+SIGNATURE  # 取得文字內容
        print(tweet_text)
        media_id = upload_media(pic)  # 上傳圖片

        if media_id:
            post_tweet(tweet_text, media_id)
        else:
            logging.error("圖片上傳失敗，無法發送推文")
    except Exception as e:
        logging.exception("上傳圖片並發送推文時發生異常")