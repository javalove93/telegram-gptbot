import requests
import json
from flask import Flask, request
import os
import openai
from google.cloud import translate_v2 as translate
import logging

if os.environ['GOOGLE_APPLICATION_CREDENTIALS'] == '':
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '../sa-key.json'
app = Flask(__name__)

# Replace YOUR_BOT_TOKEN with your actual bot token
# ChatGPTbyJerryBot
bot_token = "YOUR_BOT_TOKEN" ############## REDACTED

# OpenAI API Key
openai.api_key = "YOUR_OPENAI_API_KEY" ############## REDACTED

# allowed chatid
allowed_chatid = [ALLOWED_CHATID_1, ALLOWED_CHATID_2, ... as number] ############## REDACTED

# Params for openai api
params = {}

# parameters for openai api

@app.route('/webhook', methods=['POST'])
def webhook():
    global allowed_chatid, params

    # Extract the message from the incoming request
    update = request.json
    logging.debug(json.dumps(update, indent=4))

    # 1:1 chat message sample
    ''' 
        {
            "update_id": 295491250,
            "message": {                        # edited_message 인 경우가 있음 if message is edited
                "message_id": 51,
                "from": {
                    "id": CHAT_ID, ############## REDACTED
                    "is_bot": false,
                    "first_name": "\uba85\ud6c8",
                    "last_name": "\uc815",
                    "language_code": "ko"
                },
                "chat": {
                    "id": CHAT_ID, ############## REDACTED
                    "first_name": "\uba85\ud6c8",
                    "last_name": "\uc815",
                    "type": "private"
                },
                "date": 1678285290,
                "text": "hi"
            }
        }   
    '''

    # channel chat message sample
    ''' 
        {
            "update_id": 295491251,
            "channel_post": {
                "message_id": 131,
                "sender_chat": {
                    "id": CHAT_ID, ############## REDACTED
                    "title": "Jerry's Topics",
                    "type": "channel"
                },
                "chat": {
                    "id": CHAT_ID, ############## REDACTED
                    "title": "Jerry's Topics",
                    "type": "channel"
                },
                "date": 1678285353,
                "text": "test"
            }
        }
    '''

    try:
        if 'channel_post' in update:
            chatid = update['channel_post']['chat']['id']
            message = update['channel_post']['text']
        elif 'edited_message' in update:
            chatid = update['edited_message']['chat']['id']
            message = update['edited_message']['text']
        else:
            chatid = update['message']['chat']['id']
            message = update['message']['text']

        # Allow only specific chat id to prevent abusing of your openai budget !!!!
        if chatid in allowed_chatid:
            if chatid not in params or params[chatid] is None:
                params[chatid] = {
                    "model": DEFAULT gpt-3.5-turbo, OPTIONAL gpt-4, ############## REDACTED
                    "max_tokens": 2048 FOR gpt-3.5-turbo AND 4096 FOR gpt-4, ############## REDACTED
                    "frequency_penalty": 0.5,
                    "presence_penalty": 0.5,
                    "temperature": 0.5,
                    "translate_target": None,
                    "timeout_min": 60,
                    "last_message_time": None,
                    # messages history
                    "messages": [
                        {'role': 'system', 'content': 'You are a helpful assistant'}
                    ]
                }

            model = params[chatid]['model']
            frequency_penalty = params[chatid]['frequency_penalty']
            presence_penalty = params[chatid]['presence_penalty']
            max_tokens = params[chatid]['max_tokens']
            temperature = params[chatid]['temperature']
            translate_target = params[chatid]['translate_target']
            messages = params[chatid]['messages']

            # Remove timeout handling
            """
            import time
            timeout_min = params[chatid]['timeout_min']
            last_message_time = params[chatid]['last_message_time']
            if last_message_time is not None:
                if time.time() - last_message_time > timeout_min * 60:
                    messages = [
                        {'role': 'system', 'content': 'You are a helpful assistant'}
                    ]
                    params[chatid]['messages'] = messages
                    send_message(chatid, "{} minutes timed out. Clear messages".format(timeout_min))
                    logging.info("{} minutes timed out. Clear messages".format(timeout_min))
            last_message_time = time.time()
            params[chatid]['last_message_time'] = last_message_time
            """

            tclient = translate.Client()

            update_msg = True

            # Bot's / command parsing and handling
            if message.startswith("/"):
                if message == "/clear":
                    messages = [
                        {'role': 'system', 'content': 'You are a helpful assistant'}
                    ]
                    params[chatid]['messages'] = messages
                    send_message(chatid, "Clear messages")
                    return 'OK'
                elif message == "/topic" or message == "/topics":
                    message = "list up topics we have discussed"
                    update_msg = False
                elif message.startswith("/params"):
                    if message == "/params":
                        message = "frequency_penalty: {}\npresence_penalty: {}\nmax_tokens: {}\ntemperature: {}".format(frequency_penalty, presence_penalty, max_tokens, temperature)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("frequency_penalty"):
                        frequency_penalty = float(message[8:].split(" ")[1])
                        params[chatid]['frequency_penalty'] = frequency_penalty
                        message = "frequency_penalty: {}".format(frequency_penalty)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("presence_penalty"):
                        presence_penalty = float(message[8:].split(" ")[1])
                        params[chatid]['presence_penalty'] = presence_penalty
                        message = "presence_penalty: {}".format(presence_penalty)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("max_tokens"):
                        max_tokens = int(message[8:].split(" ")[1])
                        params[chatid]['max_tokens'] = max_tokens
                        message = "max_tokens: {}".format(max_tokens)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("temperature"):
                        temperature = float(message[8:].split(" ")[1])
                        params[chatid]['temperature'] = temperature
                        message = "temperature: {}".format(temperature)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:] == "reset":
                        params[chatid] = None
                        message = "Reset parameters. Check current params with /params command"
                        send_message(chatid, message)
                        return 'OK'
                    else:
                        send_message(chatid, "Unknown params")
                        send_message(chatid, "Available params are: frequency_penalty, presence_penalty, max_tokens, temperature, reset")
                        return 'OK'
                elif message.startswith("/system"):
                    if message == "/system":
                        message = "System message is {}".format(messages[0])
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:] == "reset":
                        messages[0]['content'] = "You are a helpful assistant"
                        params[chatid]['messages'] = messages
                        send_message(chatid, "Reset system message as {}".format(messages[0]))
                        return 'OK'
                    else:
                        messages[0]['content'] = message[8:]
                        params[chatid]['messages'] = messages
                        send_message(chatid, "Set system message as {}".format(messages[0]))
                        return 'OK'
                elif message.startswith("/translate"):
                    if message == "/translate":
                        message = "Translate target language is {}".format(translate_target if translate_target else "None")
                        send_message(chatid, message)
                        return 'OK'
                    else:
                        language = message[10:].strip()
                        if language.lower() == "none":
                            translate_target = None
                        else:
                            translate_target = language
                        
                        params[chatid]['translate_target'] = language
                        message = "Translate target language is {}".format(translate_target)

                        send_message(chatid, message)
                        return 'OK'
                elif message == "/history":
                    message = "History messages are: \n"
                    for msg in messages:
                        message += "{}: {}\n".format(msg['role'], msg['content'])
                    send_message(chatid, message)
                    return 'OK'
                elif message.startswith("/model"):
                    if message == "/model":
                        message = "Model is {}".format(model)
                        send_message(chatid, message)
                        return 'OK'
                    else:
                        model = message[7:].strip()
                        params[chatid]['model'] = model
                        message = "Model is {}".format(model)
                        send_message(chatid, message)
                        return 'OK'
                else:
                    help_message = "Available commands are: /help, /clear, /topic, /params, /system, /translate, /history, /model \nhttps://javalove93.github.io/telegram-gptbot/index.html"
                    if message == "/help":
                        send_message(chatid, help_message)
                        return 'OK'

                    send_message(chatid, "Unknown command")
                    send_message(chatid, help_message)
                    return 'OK'
            
            # Process the message and send a response
            if translate_target:
                message = tclient.translate(message, target_language='en')['translatedText']
            messages.append({'role': 'user', 'content': message})
            logging.info(json.dumps(messages, indent=4))

            # frequency_penalty: 0.5
            """
            PT: The `frequency_penalty` parameter in OpenAI's GPT-3 API can be set to any value between 0.0 and 1.0, with 0.0 indicating no penalty for repetition and 1.0 indicating the strongest possible penalty for repetition. 

            Here's an overview of what different values of `frequency_penalty` might result in:

            - 0.0: No penalty for repetition. The model may generate more repetitive output.
            - 0.5: Moderate penalty for repetition. The model will try to avoid repeating words or phrases too often.
            - 1.0: Strong penalty for repetition. The model will avoid repeating words or phrases as much as possible, which may result in more diverse output but could also make the output less coherent or grammatically correct.

            The optimal value for `frequency_penalty` will depend on the specific use case and the desired output. A higher value may be more appropriate for generating creative or novel output, while a lower value may be more appropriate for generating more coherent or structured output.
            """

            # presence_penalty: 0.5
            """
            GPT: `presence_penalty` is a parameter in OpenAI's GPT-3 language model that controls the model's tendency to generate repeated phrases or sentences. It is used to penalize the model for generating text that is too similar to the input text or previously generated text. 

            The presence penalty value ranges from 0 to 1, with 0 indicating no penalty and 1 indicating the maximum penalty. A higher presence penalty value results in the model being more cautious about generating text that is similar to the input or previous outputs. 

            This parameter is useful in preventing the model from generating repetitive or redundant text and can be adjusted based on the specific use case and desired output.
            """

            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stop=None
            )

            message = response['choices'][0]['message']['content']
            if translate_target:
                message = tclient.translate(message, target_language=translate_target)['translatedText']
            messages.append({'role': 'assistant', 'content': message})
            if update_msg:
                params[chatid]["messages"] = messages
            response_text = message
        else:
            response_text = "GPT: You're not welcomed to use this bot. {}".format(chatid)

        send_message(chatid, response_text)
    except Exception as e:
        logging.exception(e)
        send_message(chatid, 'Error')

    return 'OK'

def send_message(chatid, text):
    # Send a message to the user using the Telegram Bot API
    url = "https://api.telegram.org/bot{}/sendMessage".format(bot_token)
    data = {
        "chat_id": chatid,
        "text": text
    }
    response = requests.post(url, json=data)
    response.raise_for_status()

@app.route('/channels', methods=['GET'])
def channels():
    channel_id = request.args.get('chat_id')

    def get_channel_updates(offset=None):
        # Get updates from the Telegram Bot API
        url = "https://api.telegram.org/bot{}/getUpdates".format(bot_token)
        params = {'chat_id': channel_id, 'offset': offset}
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f'Error retrieving updates: {response.status_code} {response.text}')
        return response.json().get('result', [])

    # delete webhook
    url = "https://api.telegram.org/bot{}/deleteWebhook".format(bot_token)
    response = requests.post(url)
    response.raise_for_status()

    latest_message_id = None

    while True:
        updates = get_channel_updates(offset=latest_message_id)
        for update in updates:
            message = update.get('message', {})
            message_id = message.get('message_id')
            text = message.get('text')
            # process the message as needed
            print(f'Received message {message_id}: {text}')
            if message_id:
                latest_message_id = message_id + 1

    # set webhook again
    url = os.environ.get('URL')
    url = "https://api.telegram.org/bot{}/setWebhook?url={}/webhook".format(bot_token, url)
    response = requests.post(url)
    response.raise_for_status()

@app.route('/setWebhook', methods=['POST'])
def set_webhook():
    global bot_token

    # set webhook
    url = request.form.get('url')
    url = "https://api.telegram.org/bot{}/setWebhook?url={}/webhook".format(bot_token, url)
    response = requests.post(url)
    response.raise_for_status()

    return 'OK'

if __name__ == '__main__':
    # Configure the webhook for your bot
    # if URL exists
    if os.environ.get('URL'):
        url = os.environ.get('URL')
        url = "https://api.telegram.org/bot{}/setWebhook?url={}/webhook".format(bot_token, url)
        response = requests.post(url)
        response.raise_for_status()

    # Start the Flask app
    app.run()

