import requests
import json
from flask import Flask, request
import os
import openai

app = Flask(__name__)

# Replace YOUR_BOT_TOKEN with your actual bot token
bot_token = "YOUR TELEGRAM BOT TOKEN"

# OpenAI API Key
openai.api_key = "YOUR OpenAI API KEY"

# messages history
messages = [
    {'role': 'system', 'content': 'You are a helpful assistant'}
]

# parameters for openai api
frequency_penalty = 0.5
presence_penalty = 0.5
max_tokens = 2048
temperature = 0.5

@app.route('/webhook', methods=['POST'])
def webhook():
    global messages, frequency_penalty, presence_penalty, max_tokens, temperature

    # Extract the message from the incoming request
    update = request.json
    print(json.dumps(update, indent=4))

    # 1:1 chat message sample
    ''' 
        {
            "update_id": 295491250,
            "message": {                        # edited_message 인 경우가 있음 if message is edited
                "message_id": 51,
                "from": {
                    "id": 6086869870,
                    "is_bot": false,
                    "first_name": "..",
                    "last_name": "..",
                    "language_code": "ko"
                },
                "chat": {
                    "id": 6086869870,
                    "first_name": "..",
                    "last_name": "..",
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
                    "id": -1001762165470,
                    "title": "..",
                    "type": "channel"
                },
                "chat": {
                    "id": -1001762165470,
                    "title": "..",
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
        if chatid == 6086869870:
            # Bot's / command parsing and handling
            if message.startswith("/"):
                if message == "/clear":
                    messages = [
                        {'role': 'system', 'content': 'You are a helpful assistant'}
                    ]
                    send_message(chatid, "Clear messages")
                    return 'OK'
                elif message == "/topic" or message == "/topics":
                    message = "list up topics we are talking so far"
                elif message.startswith("/params"):
                    if message == "/params":
                        message = "frequency_penalty: {}\npresence_penalty: {}\nmax_tokens: {}\ntemperature: {}".format(frequency_penalty, presence_penalty, max_tokens, temperature)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("frequency_penalty"):
                        frequency_penalty = float(message[8:].split(" ")[1])
                        message = "frequency_penalty: {}".format(frequency_penalty)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("presence_penalty"):
                        presence_penalty = float(message[8:].split(" ")[1])
                        message = "presence_penalty: {}".format(presence_penalty)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("max_tokens"):
                        max_tokens = int(message[8:].split(" ")[1])
                        message = "max_tokens: {}".format(max_tokens)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:].startswith("temperature"):
                        temperature = float(message[8:].split(" ")[1])
                        message = "temperature: {}".format(temperature)
                        send_message(chatid, message)
                        return 'OK'
                    elif message[8:] == "reset":
                        frequency_penalty = 0.5
                        presence_penalty = 0.5
                        max_tokens = 2048
                        temperature = 0.5
                        message = "Reset parameters as frequency_penalty: 0.5, presence_penalty: 0.5, max_tokens: 2048, temperature: 0.5"
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
                        send_message(chatid, "Reset system message as {}".format(messages[0]))
                        return 'OK'
                    else:
                        messages[0]['content'] = message[8:]
                        send_message(chatid, "Set system message as {}".format(messages[0]))
                        return 'OK'
                elif message == "/help":
                    message = "Available commands are: /help, /clear, /topic, /params /system"
                    send_message(chatid, message)
                    return 'OK'
                else:
                    send_message(chatid, "Unknown command")
                    send_message(chatid, "Available commands are: /help, /clear, /topic, /params /system")
                    return 'OK'
            
            # Process the message and send a response
            model = "gpt-3.5-turbo"
            messages.append({'role': 'user', 'content': message})
            print("=========================================================")
            print(json.dumps(messages, indent=4))
            print("=========================================================")

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
                max_tokens=max_tokens,            # 최대 2048 in davinci
                top_p=1,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stop=None
            )

            message = response['choices'][0]['message']['content']
            messages.append({'role': 'assistant', 'content': message})
            response_text = message
        else:
            response_text = "GPT: You're not welcomed to use this bot. {}".format(chatid)

        send_message(chatid, response_text)
    except Exception as e:
        print(e)
        send_message('6086869879', 'Error')

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

