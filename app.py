from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

#======python的函數庫==========
import tempfile, os

import traceback

import requests
#======python的函數庫==========

from azure.core.credentials import AzureKeyCredential
from azure.ai.language.questionanswering import QuestionAnsweringClient

# OPENAI API Key初始化設定
endpoint = os.getenv('END_POINT')
open_ai_api_key = os.getenv('OpenAI_API_KEY')
open_ai_endpoint = os.getenv('OpenAI_ENDPOINT')
deployment_name = os.getenv('OpenAI_DEPLOY_NAME')
openai.api_base = open_ai_endpoint
headers = {
    "Content-Type": "application/json",
    "api-key": open_ai_api_key,
}

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))


endpoint = os.getenv('END_POINT')
credential = AzureKeyCredential(os.getenv('AZURE_KEY'))
knowledge_base_project = os.getenv('PROJECT')
deployment = 'production'


def QA_response(text):
    client = QuestionAnsweringClient(endpoint, credential)
    with client:
        question=text
        output = client.get_answers(
            question = question,
            project_name=knowledge_base_project,
            deployment_name=deployment
        )
    return output.answers[0].answer


# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def Chatgpt_response(prompt):   

    # Define the payload for the request
    # You can modify the system message and the user prompt as needed
    payload = {
        "model": "gpt-4o-mini",  # You can switch between "gpt-4" or "gpt-3.5-turbo"
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},  # Context setting
            {"role": "user", "content": prompt}  # Replace with your actual prompt
        ],
        "temperature": 0.7,  # Modify this value to adjust the creativity level of the model
        "max_tokens": 1000,  # Control the length of the response
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0
    }
    
    # Send the request to OpenAI's API
    response = requests.post(open_ai_endpoint, headers=headers, json=payload)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse and print the response from GPT
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        # Print the error if the request was unsuccessful
        print(f"Error {response.status_code}: {response.text}")


# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text

    try:
        QA_answer = QA_response(msg)
        print(QA_answer)
        if QA_answer!='No good match found in KB':
            line_bot_api.reply_message(event.reply_token, TextSendMessage(QA_answer))
        else:
             QA_answer = Chatgpt_response(msg)
             line_bot_api.reply_message(event.reply_token, TextSendMessage(QA_answer))
    except:
        print(traceback.format_exc())
        line_bot_api.reply_message(event.reply_token, TextSendMessage('QA Error'))
        

@handler.add(PostbackEvent)
def handle_message(event):
    print(event.postback.data)


@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)
        
        
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
