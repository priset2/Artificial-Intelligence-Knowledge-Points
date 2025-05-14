import _thread as thread
import base64
import datetime
import hashlib
import hmac
import json
from urllib.parse import urlparse
import ssl
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
import websocket
import os
import signal
import sys

# 从环境变量获取星火 API 凭证
APP_ID = os.getenv("SPARK_APP_ID", "")
API_SECRET = os.getenv("SPARK_API_SECRET", "")
API_KEY = os.getenv("SPARK_API_KEY", "")

# 星火 API WebSocket 地址
SPARK_API_URL = os.getenv("SPARK_API_URL", "")

# 可配置的参数
INPUT_FILENAME = "questions.txt"
OUTPUT_FILENAME = "answers.md"
MAX_RETRIES = 3
RETRY_DELAY = 5

class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, Spark_url):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.host = urlparse(Spark_url).netloc
        self.path = urlparse(Spark_url).path
        self.Spark_url = Spark_url

    # 生成url
    def create_url(self):
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + self.host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + self.path + " HTTP/1.1"

        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'

        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }
        # 拼接鉴权参数，生成url
        url = self.Spark_url + '?' + urlencode(v)
        return url

# 收到websocket错误的处理
def on_error(ws, error):
    print("### error:", error)

# 收到websocket关闭的处理
def on_close(ws, one, two):
    print(" ")

# 收到websocket连接建立的处理
def on_open(ws):
    thread.start_new_thread(run, (ws,))

def run(ws, *args):
    data = json.dumps(gen_params(appid=ws.appid, domain=ws.domain, question=ws.question))
    ws.send(data)

# 收到websocket消息的处理
def on_message(ws, message):
    data = json.loads(message)
    code = data['header']['code']
    content = ''
    if code != 0:
        print(f'请求错误: {code}, {data}')
        ws.close()
    else:
        choices = data["payload"]["choices"]
        status = choices["status"]
        text = choices['text'][0]
        if 'content' in text and text['content'] != '':
            content = text["content"]
            print(content, end="")
            ws.answer += content
        if status == 2:
            ws.close()

def gen_params(appid, domain, question):
    """
    通过appid和用户的提问来生成请参数
    """
    data = {
        "header": {
            "app_id": appid,
            "uid": "1234",
        },
        "parameter": {
            "chat": {
                "domain": domain,
                "temperature": 0.5,
                "max_tokens": 32768
            }
        },
        "payload": {
            "message": {
                "text": question
            }
        }
    }
    return data

def ask_spark(question):
    """
    向星火大模型提问并返回结果
    """
    wsParam = Ws_Param(APP_ID, API_KEY, API_SECRET, SPARK_API_URL)
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close,
                              on_open=on_open)
    ws.appid = APP_ID
    ws.question = question
    ws.domain = "x1"
    ws.answer = ""
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    return ws.answer

def signal_handler(signum, frame):
    """
    处理Ctrl+C信号
    """
    print("\n\n收到中断信号，正在优雅退出...")
    sys.exit(0)

def process_questions(input_file, output_file):
    """
    读取问题文件，向星火大模型提问，并将结果保存到 Markdown 文件中
    支持从中断处继续处理问题
    """
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    prompt = "你是一名 python 和人工智能领域的专家。现在需要你对给出的问题给出详细的回答。我会一次性给出一个问题，请对每个问题分别做出回答并尽可能回答详细，内容丰富。回答的内容请包含：问题、知识点、答案、拓展四个部分。请使用标准 markdown 格式回答。"

    if not os.path.exists(input_file):
        print(f"错误: 输入文件 '{input_file}' 未找到。")
        return

    if not all([APP_ID, API_SECRET, API_KEY]):
        print("错误: 请设置正确的星火 API 凭证 (APP_ID, API_SECRET, API_KEY)。")
        return

    try:
        # 首先读取所有非空问题，计算总数
        with open(input_file, 'r', encoding='utf-8') as f_in:
            questions = [line.strip() for line in f_in if line.strip()]
            total_questions = len(questions)

        # 确保输出文件存在，如果不存在则创建
        if not os.path.exists(output_file):
            open(output_file, 'w', encoding='utf-8').close()
            last_processed_index = 0
        else:
            # 读取已有的markdown文件，找到最后处理的问题
            last_processed_index = 0
            try:
                with open(output_file, 'r', encoding='utf-8') as f_out:
                    content = f_out.read()
                    for i, question in enumerate(questions):
                        if question in content:
                            last_processed_index = i + 1
            except Exception as e:
                print(f"读取输出文件时发生错误: {e}")
                print("将从头开始处理问题...")

        remaining_questions = total_questions - last_processed_index
        if remaining_questions > 0:
            print(f"\n共发现 {total_questions} 个问题，从第 {last_processed_index + 1} 个问题继续处理，剩余 {remaining_questions} 个问题...\n")
        else:
            print("所有问题已处理完成，无需继续。")
            return

        # 从上次处理的位置继续处理问题
        for i in range(last_processed_index, total_questions):
            question = questions[i]
            current_index = i + 1
            print(f"[{current_index}/{total_questions}] 正在处理问题: {question}")
            print("等待模型回答中...")
            
            try:
                full_question = [{"role": "user", "content": f"{prompt}\n\n{question}"}]
                answer = ask_spark(full_question)
                
                markdown_output = f"## 问题\n{question}\n\n## 知识点\n\n## 答案\n{answer}\n\n## 拓展\n"
                
                # 使用追加模式打开文件，确保每个问题处理完就立即保存
                with open(output_file, 'a', encoding='utf-8') as f_out:
                    f_out.write(markdown_output + "\n---\n")
                    f_out.flush()  # 确保内容立即写入磁盘
                
                print(f"✓ 问题 {current_index}/{total_questions} 处理完成")
                print("-" * 50 + "\n")
                
            except Exception as e:
                print(f"处理问题 '{question}' 时发生错误: {e}")
                print("继续处理下一个问题...\n")
                continue

    except FileNotFoundError:
        print(f"错误: 文件 '{input_file}' 未找到。")
    except Exception as e:
        print(f"处理文件时发生未知错误: {e}")
        print("请检查输入文件格式是否正确，以及网络连接是否正常。")

if __name__ == "__main__":
    process_questions(INPUT_FILENAME, OUTPUT_FILENAME)
    print(f"\n处理完成。答案已保存到文件: {OUTPUT_FILENAME}")


   