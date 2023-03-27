import datetime
import re
import subprocess
import traceback
import requests
import json
from flask import Flask, request
import os
import openai
from google.cloud import translate_v2 as translate
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

app = Flask(__name__)

# Replace YOUR_BOT_TOKEN with your actual bot token
# ChatGPTbyJerryBot
bot_token = "YOUR_BOT_TOKEN" ############## REDACTED

# OpenAI API Key
openai_apikey = "YOUR_OPENAI_API_KEY" ############## REDACTED
openai.api_key = openai_apikey

# Firebase Realtime Database initialization
firebase_db = None
try:
    import firebase_admin
    from firebase_admin import credentials, db
    if "FIREBASE_SA_KEY" in os.environ:
        cred = credentials.Certificate(os.environ['FIREBASE_SA_KEY'])
    else:
        cred = credentials.Certificate('YOUR_FIREBASE_SA_KEY_PATH_IF_YOU_WANT') ############## REDACTED
    firebase_admin.initialize_app(cred, {
        'databaseURL: YOUR_FIREBASE_DATABASE_URL' ############## REDACTED
    })
    firebase_db = db.reference('/')
    logging.info("Firebase Realtime Database initialized")
except Exception as e:
    logging.info("Firebase Realtime Database initialization failed: {}".format(e))

# Params for openai api
params = {}
saved_history = {
}

# allowed chatid
allowed_chatid = [ALLOWED_CHATID_1, ALLOWED_CHATID_2, ... as number] ############## REDACTED

def get_system_info():
    # get last updated time of 'webhook.py' file in KST
    # Get the timestamp of the file in UTC
    timestamp = datetime.datetime.fromtimestamp(os.path.getmtime('webhook.py'))
    # Convert the UTC timestamp to KST timezone
    kst_timestamp = timestamp.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
    last_updated = kst_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    message = "Last updated: {}".format(last_updated)
    # get file creation time of '/proc/1'
    # Get the timestamp of the file in UTC
    timestamp = datetime.datetime.fromtimestamp(os.path.getctime('/proc/1'))
    # Convert the UTC timestamp to KST timezone
    kst_timestamp = timestamp.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
    started = kst_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    message += ", Boot time: {}".format(started)
    return message

def params_get(chatid):
    global firebase_db, params
    chatid = str(chatid)
    if firebase_db is not None:
        try:
            # create if 'params' exists
            if firebase_db.child('params').get() is None:
                firebase_db.child('params').set({})
            return firebase_db.child('params').child(chatid).get()
        except Exception as e:
            full_stack_error_msg = traceback.format_exc()
            logging.error(full_stack_error_msg)
    else:
        if chatid not in params:
            params[chatid] = {}
        return params[chatid]

def params_set(chatid, value):
    global firebase_db, params
    chatid = str(chatid)
    if firebase_db is not None:
        try:
            # create if 'params' exists
            if firebase_db.child('params').get() is None:
                firebase_db.child('params').set({})
            firebase_db.child('params').child(chatid).set(value)
        except Exception as e:
            full_stack_error_msg = traceback.format_exc()
            logging.error(full_stack_error_msg)
    else:
        if chatid not in params:
            params[chatid] = None
        params[chatid] = value

def save_history(chatid, title):
    global firebase_db, saved_history
    chatid = str(chatid)
    # timestamp as GMT+9
    timestamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
    if firebase_db is not None:
        try:
            firebase_db.child('saved_history').child(chatid).child(timestamp).set({
                "title": title,
                "params": params_get(chatid)
            })
        except Exception as e:
            full_stack_error_msg = traceback.format_exc()
            logging.error(full_stack_error_msg)
    else:
        if chatid not in saved_history:
            saved_history[chatid] = {}
        saved_history[chatid][timestamp] = {
            "title": title,
            "params": params_get(chatid)
        }

def get_saved_history(chatid):
    global firebase_db, saved_history
    chatid = str(chatid)
    if firebase_db is not None:
        try:
            return firebase_db.child('saved_history').child(chatid).get()
        except Exception as e:
            full_stack_error_msg = traceback.format_exc()
            logging.error(full_stack_error_msg)
    else:
        if chatid not in saved_history:
            return None
        return saved_history[chatid]

def load_history(chatid, key):
    global firebase_db, saved_history
    chatid = str(chatid)
    if firebase_db is not None:
        try:
            history = firebase_db.child('saved_history').child(chatid).child(key).get()
            params_set(chatid, history['params'])
        except Exception as e:
            full_stack_error_msg = traceback.format_exc()
            logging.error(full_stack_error_msg)
    else:
        params_set(chatid, saved_history[chatid][key]['params'])

@app.route('/webhook', methods=['POST'])
def webhook():
    global openai_apikey, allowed_chatid, bot_token

    # Extract the message from the incoming request
    update = request.json
    logging.info(update)

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
        debug = "on"
        stt_text = None
        try:
            update_id = update['update_id']
            if 'channel_post' in update:
                chatid = update['channel_post']['chat']['id']
                message = update['channel_post']
            elif 'edited_message' in update:
                chatid = update['edited_message']['chat']['id']
                message = update['edited_message']
            else:
                chatid = update['message']['chat']['id']
                message = update['message']


            message = message['text']
        except Exception as e:
            full_stack_error_msg = traceback.format_exc()
            logging.error("Error: {}".format(full_stack_error_msg))
            logging.error(json.dumps(update, indent=4))

            return "OK"

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

        message_trimed = None

        # Allow only specific chat id to prevent abusing of your openai budget !!!!
        if chatid in allowed_chatid:
            logging.info("chatid: {}, allowed_chatid: {}".format(chatid, allowed_chatid))
            if chatid < 0:
                if message.startswith("[gpt]"):
                    message = message[5:].strip()
                    logging.info("channel chat into GPT: {}".format(message))
                else:
                    return "OK"
            params = params_get(chatid)
            if params is None or params == {}:
                params = {
                    'model': 'gpt-3.5-turbo',
                    'max_tokens': 2048 FOR gpt-3.5-turbo AND 4096 FOR gpt-4, ############## REDACTED
                    'frequency_penalty': 0.5,
                    'presence_penalty': 0.5,
                    'temperature': 0.5,
                    'translate_target': "None",
                    'debug': 'off',
                    'timeout': 120,
                    'trim': 'on',
                    'messages': [
                        {'role': 'system', 'content': 'You are a helpful assistant'}
                    ]
                }

            # logging.info("params: {}".format(params))

            model = params['model']
            frequency_penalty = params['frequency_penalty']
            presence_penalty = params['presence_penalty']
            max_tokens = params['max_tokens']
            temperature = params['temperature']
            translate_target = params['translate_target']
            messages = params['messages'].copy()
            debug = params['debug']
            timeout = params['timeout']
            trim = params['trim']

            if debug == "on":
                logging.info(json.dumps(update, indent=4))

            # Prevent same update_id retry (mostly caused by openai API timeout) - works
            if 'last_update_id' in params and update_id == params['last_update_id']:
                logging.info("Same update_id: {}. Ignore".format(update_id))
                send_message(chatid, "Same update_id. Ignore")
                return "OK"

            params['last_update_id'] = update_id
            params_set(chatid, params)

            if stt_text is not None:
                send_message(chatid, "STT: {}".format(stt_text))

            if translate_target != "None":
                tclient = translate.Client()

            update_msg = True
            saveHistory = False

            # Bot's / command parsing and handling
            if message.startswith("%%"):
                message = message.replace("%%", "/")
            if message.startswith("/") or message == "--" or message == "++":
                if message == "/clear" or message == "/c" or message == "--":
                    messages = [
                        {'role': 'system', 'content': 'You are a helpful assistant'}
                    ]
                    params['messages'] = messages
                    params_set(chatid, params)
                    send_message(chatid, "Clear messages")
                    return 'OK'
                elif message == "/topic" or message == "/topics" or message == "/t":
                    message = "list up topics we have discussed"
                    update_msg = False
                elif message == "/save" or message == "/s":
                    message = "what is a title based on our conversation?"
                    update_msg = False
                    saveHistory = True
                elif message == "/list" or message == "/l":
                    history = get_saved_history(chatid)
                    if history is None or history == {}: 
                        message = "No saved history"
                    else:
                        message = "Saved history:\n"
                        idx = 1
                        for key in history:
                            message += "{}: {} at {}\n".format(idx, history[key]['title'], key)
                            idx += 1
                    send_message(chatid, message)
                    return 'OK'
                elif message.startswith("/load"):
                    history = get_saved_history(chatid)
                    if history is None or history == {}: 
                        message = "No saved history"
                    else:
                        if message == "/load":
                            message = "which history do you want to load? (1, 2, 3, ...)"
                        else:
                            try:
                                idx = int(message[6:].strip())
                                print("idx: {}, len: {}".format(idx, len(history)))
                                if idx > 0 and idx <= len(history):
                                    key = list(history.keys())[idx-1]
                                    load_history(chatid, key)
                                    message = "Loaded history: {}".format(history[key]['title'])
                                else:
                                    message = "Invalid index"
                            except Exception as e:
                                logging.exception(e)
                                message = "Invalid index"
                    send_message(chatid, message)
                    return 'OK'
                elif message.startswith("/params"):
                    if message == "/params":
                        message = "frequency_penalty: {}\npresence_penalty: {}\nmax_tokens: {}\ntemperature: {}\nmodel: {}".format(frequency_penalty, presence_penalty, max_tokens, temperature, model)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("frequency_penalty"):
                        frequency_penalty = float(message[8:].split(" ")[1])
                        params['frequency_penalty'] = frequency_penalty
                        params_set(chatid, params)
                        message = "frequency_penalty: {}".format(frequency_penalty)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("presence_penalty"):
                        presence_penalty = float(message[8:].split(" ")[1])
                        params['presence_penalty'] = presence_penalty
                        params_set(chatid, params)
                        message = "presence_penalty: {}".format(presence_penalty)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("max_tokens"):
                        max_tokens = int(message[8:].split(" ")[1])
                        params['max_tokens'] = max_tokens
                        params_set(chatid, params)
                        message = "max_tokens: {}".format(max_tokens)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("temperature"):
                        temperature = float(message[8:].split(" ")[1])
                        params['temperature'] = temperature
                        params_set(chatid, params)
                        message = "temperature: {}".format(temperature)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("model"):
                        model = message[8:].split(" ")[1]
                        params['model'] = model
                        params_set(chatid, params)
                        message = "Model is {}".format(model)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:] == "reset":
                        params_set(chatid, None)
                        message = "Reset parameters. Check current params with /params command"
                        send_message(chatid, message)
                        return 'OK'
                    else:
                        send_message(chatid, "Unknown params")
                        send_message(chatid, "Available params are: frequency_penalty, presence_penalty, max_tokens, temperature, model, reset")
                        return 'OK'
                elif message.startswith("/system"):
                    if message == "/system":
                        message = "System message is {}".format(messages[0])
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:] == "reset":
                        messages[0]['content'] = "You are a helpful assistant"
                        params['messages'] = messages
                        params_set(chatid, params)
                        send_message(chatid, "Reset system message as {}".format(messages[0]))
                        return 'OK'
                    else:
                        messages[0]['content'] = message[8:]
                        params['messages'] = messages
                        params_set(chatid, params)
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
                            translate_target = "None"
                        else:
                            translate_target = language
                        
                        params['translate_target'] = translate_target
                        params_set(chatid, params)
                        message = "Translate target language is {}".format(translate_target)

                        send_message(chatid, message)
                        return 'OK'
                elif message == "/history" or message == "/h" or message == "++":
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
                        params['model'] = model
                        params_set(chatid, params)
                        message = "Model is {}".format(model)
                        send_message(chatid, message)
                        return 'OK'
                elif message.startswith("/debug"):
                    if message == "/debug":
                        message = "Debug mode is {}".format(debug)
                        send_message(chatid, message)
                        return 'OK'
                    else:
                        debug = message[7:].strip().lower()
                        if debug not in ["on", "off"]:
                            send_message(chatid, "Debug mode should be on or off")
                            return 'OK'
                        params['debug'] = debug
                        params_set(chatid, params)
                        message = "Debug mode is {}".format(debug)
                        send_message(chatid, message)
                        return 'OK'
                elif message.startswith("/timeout"):
                    if message == "/timeout":
                        message = "Timeout is {}".format(timeout)
                        send_message(chatid, message)
                        return 'OK'
                    else:
                        timeout = int(message[9:].strip())
                        params['timeout'] = timeout
                        params_set(chatid, params)
                        message = "Timeout is {}".format(timeout)
                        send_message(chatid, message)
                        return 'OK'
                elif message.startswith("/trim"):
                    if message == "/trim":
                        message = "Trim is {}".format(trim)
                        send_message(chatid, message)
                        return 'OK'
                    else:
                        trim = message[6:].strip()
                        if trim not in ["on", "off"]:
                            send_message(chatid, "Trim should be on or off")
                            return 'OK'
                        params['trim'] = trim
                        params_set(chatid, params)
                        message = "Trim is {}".format(trim)
                        send_message(chatid, message)
                        return 'OK'
                elif message == "/info" or message == "/version":
                    send_message(chatid, get_system_info())
                    return 'OK'
                elif message == "/gpt3":
                    model = "gpt-3.5-turbo"
                    max_tokens = 2048
                    params['model'] = model
                    params['max_tokens'] = max_tokens
                    params_set(chatid, params)
                    message = "Model is {} and max_tokens is {}".format(model, max_tokens)
                    send_message(chatid, message)
                    return 'OK'
                elif message == "/gpt4":
                    model = "gpt-4"
                    max_tokens = 4096
                    params['model'] = model
                    params['max_tokens'] = max_tokens
                    params_set(chatid, params)
                    message = "Model is {} and max_tokens is {}".format(model, max_tokens)
                    send_message(chatid, message)
                    return 'OK'
                elif message == "/reset":
                    params_set(chatid, None)
                    message = "Reset parameters. Check current params with /params and /model command"
                    send_message(chatid, message)
                    return 'OK'
                else:
                    help_message = "Available commands are: /help, /clear, /topic, /params, /system, /translate, /history, /model, ... \nhttps://javalove93.github.io/telegram-gptbot/index.html"
                    if message == "/help":
                        send_message(chatid, help_message)
                        return 'OK'

                    send_message(chatid, "Unknown command")
                    send_message(chatid, help_message)
                    return 'OK'
            
            # Process the message and send a response
            if translate_target != "None":
                message = tclient.translate(message, target_language='en')['translatedText']
            messages.append({'role': 'user', 'content': message})
            if debug == "on":
                logging.info(json.dumps(messages, indent=4))

            while True:
                try:
                    api_or_rest = "rest"
                    if api_or_rest == "api":
                        response = openai.ChatCompletion.create(
                            model=model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            top_p=1,
                            frequency_penalty=frequency_penalty,
                            presence_penalty=presence_penalty,
                            stop=None,
                            timeout=timeout         # seconds - doesn't work
                        )
                    else:
                        headers = {
                            "Content-Type": "application/json",
                            "Authorization": "Bearer " + openai_apikey
                        }
                        body = {
                            "model": model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "top_p": 1,
                            "frequency_penalty": frequency_penalty,
                            "presence_penalty": presence_penalty,
                            "stop": None
                        }
                        if debug == "on":
                            logging.info("------ REST API Request Body ------")
                            logging.info(json.dumps(body, indent=4))
                        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=timeout)
                        if response.status_code != 200:
                            # throw exception
                            raise Exception("OpenAI API error: {}, {}".format(response.status_code, response.text))
                        
                        response = response.json()
                    break
                except Exception as e:
                    logging.exception(e)

                    full_stack_error_msg = traceback.format_exc()
                    # ERROR:root:This model's maximum context length is 4097 tokens. However, you requested 5913 tokens (3865 in the messages, 2048 in the completion). 
                    # Please reduce the length of the messages or completion.
                    too_many_tokens_error = "This model's maximum context length is"
                    if str(e).find(too_many_tokens_error) != -1:
                        # Since max_tokens exceed error, retry after trim unnecessary history and message
                        # remove the second array element of messages
                        messages.pop(1)
                        message_trimed = "*** Old history is trimmed. ***"
                        if len(messages) < 2:
                            # remove the last line of message
                            message = message[:message.rfind('\n')]
                            messages.append({'role': 'user', 'content': message})
                            # number of line size of message
                            message_line_size = len(message.splitlines())
                            message_trimed = "*** Later part of the message is trimmed: {}. ***".format(message_line_size)

                        continue

                    send_message(chatid, "OpenAI API error: {}".format(e))
                    return 'OK'

            if debug == "on":
                logging.info(json.dumps(response, indent=4))

            message = response['choices'][0]['message']['content']
            if translate_target != "None":
                message = tclient.translate(message, target_language=translate_target)['translatedText']
            messages.append({'role': 'assistant', 'content': message})
            if update_msg:
                params['messages'] = messages
                params_set(chatid, params)
            if saveHistory:
                # get quotated string from message into title and remove quote mark
                title = re.findall(r'"([^"]*)"', message)[0]
                save_history(chatid, title)
                message = "History saved as title, \"{}\"".format(title)
            if debug == "on":
                response_text = get_system_info() + "\n" + message
            else:
                response_text = message
        else:
            response_text = "GPT: You're not welcomed to use this bot. {}".format(chatid)

        if message_trimed is not None:
            response_text = message_trimed + "\n" + response_text
        send_message(chatid, response_text)
    except Exception as e:
        logging.exception(e)
        
        full_stack_error_msg = traceback.format_exc()
        logging.error(full_stack_error_msg)
        if debug == "on":
            send_message(chatid, full_stack_error_msg)
            logging.error(json.dumps(update, indent=4))
        else:
            send_message(chatid, "Error: {}".format(str(e)))

    return 'OK'

def send_message(chatid, text):
    try:
        # Send a message to the user using the Telegram Bot API
        url = "https://api.telegram.org/bot{}/sendMessage".format(bot_token)
        data = {
            "chat_id": chatid,
            "text": text
        }
        logging.info("Sending message to {}: {}".format(chatid, text))
        response = requests.post(url, json=data)
        response.raise_for_status()
    except Exception as e:
        logging.exception(e)
        full_stack_error_msg = traceback.format_exc()
        logging.error(full_stack_error_msg)

        logging.info("data: {}".format(json.dumps(data, indent=4)))

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

