from io import BytesIO
import json
import logging
import os
from google import genai
from google.genai import types
from PIL import Image
import re
import random
# 設置日誌配置

# 取得目前腳本所在目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 建立 app.log 檔案的完整路徑
log_file_path = os.path.join(BASE_DIR, "app.log")

logging.basicConfig(
    filename=log_file_path,  # 確保日誌存放在正確的目錄
    level=logging.INFO,  # 記錄 INFO 級別及以上的日誌
    format="%(asctime)s - %(levelname)s - %(message)s"  # 日誌格式
)

# 建立 config.json 的完整路徑
config_path = os.path.join(BASE_DIR, "config.json")

try:
    with open(config_path, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)
except Exception as e:
    logging.exception("無法加載 config.json 文件: %s", e)
    raise

GEMINI_KEY = config["AI_API"]["API_KEY"]
IMAGE_PRONPT = config["PROMPTS"]["IMAGE_PROMPT"]

try:
    client = genai.Client(api_key=GEMINI_KEY)
except Exception as e:
    logging.exception("無法初始化 genai 客戶端")
    raise

def generatetxt(promttxt: str):
    try:
        content = config["PROMPTS"][promttxt]
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[content]
        )
        with open(f"{promttxt}.txt", "w", encoding="utf-8") as file:
            text_content = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, "text"))
            file.write(text_content)
        logging.info(f"成功生成文本並保存到 {promttxt}.txt")
    except Exception as e:
        logging.exception(f"生成文本失敗：{promttxt}")

def get_and_remove_first_numbered_sentence(filename: str):
    try:
        # 組合完整路徑
        file_path = os.path.join(os.path.dirname(__file__), f"{filename}.txt")
        
        # 讀取檔案內容
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        # 篩選出有編號的句子（假設編號格式為 "1. 句子" 或 "[1] 句子"）
        numbered_lines = [line for line in lines if re.match(r"^\s*(\d+[\.\]]\s+)", line)]

        if not numbered_lines:
            logging.info(f"{filename}.txt 沒有找到帶編號的句子，重新生成內容")
            generatetxt(filename)

            # 重新讀取檔案，確保 `generatetxt` 真的產生了符合格式的內容
            return get_and_remove_first_numbered_sentence(filename)
        else:
            # 取出第一個編號句子
            first_sentence = numbered_lines[0].strip()

            # 剩下的內容（刪除第一個編號句子）
            updated_lines = [line for line in lines if line.strip() != first_sentence]

            # 將新的內容寫回檔案
            with open(file_path, "w", encoding="utf-8") as file:
                file.writelines(updated_lines)

            return first_sentence
    except Exception as e:
        logging.exception(f"處理文件 {filename}.txt 時發生錯誤: {e}")
        raise

def random_topic():
    try:
        topics = ["CONTENT_PROMPT", "CONTENT_PROMPT_WARM"]
        random_element = random.choice(topics)
        logging.info(f"隨機選擇的主題是：{random_element}")
        return random_element
    except Exception as e:
        logging.exception("隨機選擇主題時發生錯誤")
        raise
    
def pick_topic():
    topic=random_topic()
    sentence=get_and_remove_first_numbered_sentence(topic)
    sentence_content = re.split(r"^\s*\d+[\.\]]\s+", sentence, maxsplit=1)[1]
    return sentence_content

def generate_img(sentence_content):
    try:
    # print(sentence_content)
        content2=sentence_content,IMAGE_PRONPT
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[content2]
        )
        response=response.text
        match = re.search(r'{.*}', response, re.DOTALL)
        
        if match:
            json_string = match.group(0)
            data = json.loads(json_string)
            description = data["description"]
            image_description = data["image_description"]
            logging.info(f"成功生成描述：{description} 和圖片描述：{image_description}")
        else:
            logging.warning("未找到 JSON 格式的描述")
            return None
        contents = image_description
        response2 = client.models.generate_content(
            model="models/gemini-2.0-flash-exp",
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=['Text', 'Image'])
        )

        for part in response2.candidates[0].content.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                #image = Image.open(BytesIO(part.inline_data.data))
                return BytesIO(part.inline_data.data)
                #image.show()
    except json.JSONDecodeError as e:
        logging.exception("JSON 解析錯誤")
    except KeyError as e:
        logging.exception("JSON 中缺少必要的鍵")
    except Exception as e:
        logging.exception("生成圖片時發生錯誤")
        raise

if __name__ == "__main__":
    pass