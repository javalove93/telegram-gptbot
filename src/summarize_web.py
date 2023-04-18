import requests
from bs4 import BeautifulSoup
import json
import sys
from langdetect import detect
from flask import Flask, request, jsonify, render_template, url_for, redirect, flash, session
import openai

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# OpenAI API Key
openai_apikey = "YOUR_OPENAI_API_KEY"
openai.api_key = openai_apikey

def read_webpage(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'accpet': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        # 'accept-encoding': 'gzip, deflate, br',
        'referer': 'https://www.google.com/',
        'accept-language': 'ko,en-US;q=0.9,en;q=0.8'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # get the title
        title = soup.select_one('title').get_text().strip()

        # get the language
        meta_tag = soup.find('meta', {'charset': True})
        charset = meta_tag['charset']

        # get the body
        body = soup.select_one('body')
        
        # list the first level children of the body
        children = body.findChildren()
        content = []
        text_content = ''
        for child in children:
            if child.name in ['h1', 'h2', 'h3', 'h4', 'p']:
                content.append({
                    'type': child.name,
                    'text': child.get_text().strip()
                })
                text_content += child.get_text().strip() + '\n'
        
        language = detect(text_content)

        print("Charset: ", charset)
        print("Language: ", language)

        return {
            'result': 'success',
            'language': language,
            'title': title,
            'content': content
        }
    else:
        return {
            'result': 'error',
            'status_code': response.status_code,
            'err_msg': response.text
        }

def complete(messages):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.1,
            max_tokens=1024,
            top_p=1,
            frequency_penalty=0.5,
            presence_penalty=0.5,
            stop=None
        )

        return response['choices'][0]['message']['content']
    except Exception as e:
        print(e)
        return 'Error'

def count_sentences(text):
    length = 0
    for line in text.split('\n'):
        if line.strip() != '':
            for str in line.split('.'):
                if str.strip() != '':
                    length += 1
    return length

def summarize_content(title, content, language='en'):
    MIN_SECTIONS = 5
    SUM_RATIO_KOR = 5
    SUM_RATIO_ENG = 5
    SUM_RATIO_SUMMARY = 3
    MAX_CHUNK_SIZE = 500

    strcuture = {
        'titles': [{'title': title}],
        'sections': []
    }
    
    section_list = {
        'h1': [],
        'h2': [],
        'h3': [],
        'h4': []
    }
    for item in content:
        if item['type'] in ['h1', 'h2', 'h3', 'h4']:
            section_list[item['type']].append(item.copy())
 
    section_tag = None
    if len(section_list['h1']) >= MIN_SECTIONS:
        strcuture['sections'] = section_list['h1']
        section_tag = 'h1'
    elif len(section_list['h2']) >= MIN_SECTIONS:
        strcuture['sections'] = section_list['h2']
        strcuture['titles'].extend(section_list['h1'])
        section_tag = 'h2'
    elif len(section_list['h3']) >= MIN_SECTIONS:
        strcuture['sections'] = section_list['h3']
        strcuture['titles'].extend(section_list['h1'])
        strcuture['titles'].extend(section_list['h2'])
        section_tag = 'h3'
    elif len(section_list['h4']) >= MIN_SECTIONS:
        strcuture['sections'] = section_list['h4']
        strcuture['titles'].extend(section_list['h1'])
        strcuture['titles'].extend(section_list['h2'])
        strcuture['titles'].extend(section_list['h3'])
        section_tag = 'h4'
    else:
        if len(section_list['h1']) > 1:
            strcuture['sections'] = section_list['h1']
            section_tag = 'h1'
        elif len(section_list['h2']) > 1:
            strcuture['sections'] = section_list['h2']
            strcuture['titles'].extend(section_list['h1'])
            section_tag = 'h2'
        elif len(section_list['h3']) > 1:
            strcuture['sections'] = section_list['h3']
            strcuture['titles'].extend(section_list['h1'])
            strcuture['titles'].extend(section_list['h2'])
            section_tag = 'h3'
        elif len(section_list['h4']) > 1:
            strcuture['sections'] = section_list['h4']
            strcuture['titles'].extend(section_list['h1'])
            strcuture['titles'].extend(section_list['h2'])
            strcuture['titles'].extend(section_list['h3'])
            section_tag = 'h4'
    
    messages = [
        {'role': 'system', 'content': 'You are a helpful assistant'}
    ]

    if language == 'ko':
        message = '글의 구조는 title > h1 > h2 > h3 > p 의 순서이다. 하나의 문장으로 제목을 추출하라:\n'
    else:
        message = 'While strcuture is title > h1 > h2 > h3 > h4 > p, please get a title as a sentence from:\n'
    for title in strcuture['titles']:
        if 'title' in title:
            message += "title: {}\n".format(title['title'])
        else:
            message += "{}: {}\n".format(title['type'], title['text'])
    
    messages.append({'role': 'user', 'content': message})
    strcuture['messages'] = messages
    title = complete(messages)
    # if title contains a quotation, extract it
    if title.find('"') != -1:
        # Extract a sentence quoted by "
        import re
        title = re.findall(r'\"(.+?)\"', title)[0]
        strcuture['title'] = title
    else:
        strcuture['title'] = title.split('\n')[0]

    # return {'structure': json.dumps(strcuture, indent=4)}

    print("Found title: {}".format(strcuture['title']))

    if section_tag is not None:
        current_section = -1
        for item in content:
            for section in strcuture['sections']:
                if item['type'] == section['type']:
                    if item['text'] == section['text']:
                        current_section += 1
                        strcuture['sections'][current_section]['content'] = []
                        break
            
            if current_section == -1:
                strcuture['sections'].insert(0, {
                    'type': 'preface',
                    'text': '',
                    'content': []
                })
                current_section = 0
            
            strcuture['sections'][current_section]['content'].append(item.copy())

        print("Found {} sections".format(len(strcuture['sections'])))

        # Firstly, try to summarize all the sections at once
        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant'}
        ]

        if language == 'ko':
            message = '글의 구조는 title > h1 > h2 > h3 > p 의 순서이다\n\n'
        else:
            message = "Text strcuture is title > h1 > h2 > h3 > h4 > p.\n\n"
        message += "title: {}\n".format(strcuture['title'])
        chunk = ''
        for section in strcuture['sections']:
            if section['type'] == 'preface':
                for item in section['content']:
                    if item['type'] == 'p':
                        chunk += "{}: {}\n".format(item['type'], item['text'])
            else:
                chunk += "{}: {}\n".format(section['type'], section['text'])
                for item in section['content']:
                    chunk += "{}: {}\n".format(item['type'], item['text'])
        # Count the number of sentences of message
        length = count_sentences(chunk)

        if language == 'ko':
            length = int(length / SUM_RATIO_KOR / SUM_RATIO_SUMMARY) + 1
            command = "\nPlease summarize the text as a {} sentence long paragraph in Korean:\n".format(length)
        else:
            length = int(length / SUM_RATIO_ENG / SUM_RATIO_SUMMARY) + 1
            command = "\nPlease summarize the text as a {} sentence long paragraph:\n".format(length)

        print("Trying to summarize all sections as {} sentences".format(length))

        messages.append({'role': 'user', 'content': "{}{}{}".format(message, chunk, command)})
        strcuture['messages'] = messages

        # Write structure as json text into a file
        with open('structure.json', 'w') as f:
            f.write(json.dumps(strcuture, indent=4))

        print("Before: {}\n".format(messages[1]['content']))
        summary = complete(messages)
        if summary == 'Error':
            # Secondly, try to summarize each section separately
            for section in strcuture['sections']:
                messages = [
                    {'role': 'system', 'content': 'You are a helpful assistant'}
                ]
                if language == 'ko':
                    message = '글의 구조는 title > h1 > h2 > h3 > p 의 순서이다.\n\n'
                else:
                    message = "Text strcuture is title > h1 > h2 > h3 > h4 > p.\n\n"
                # message += "please summarize the content as maximum {} sentences paragraph from:\n".format(MAX_LINES)
                message += "title: {}\n".format(strcuture['title'])

                chunk = ''
                if section['type'] == 'preface':
                    chunk += "{}: {}\n".format(section_tag, section['text'])
                    for item in section['content']:
                        if item['type'] == 'p':
                            chunk += "{}: {}\n".format(item['type'], item['text'])
                else:
                    chunk += "{}: {}\n".format(section['type'], section['text'])
                    for item in section['content']:
                        chunk += "{}: {}\n".format(item['type'], item['text'])

                # Count the number of sentences of message
                length = count_sentences(chunk)

                if language == 'ko':
                    length = int(length / SUM_RATIO_KOR) + 1
                    command = "\nPlease summarize the content as maximum {} bullets in Korean:\n\n".format(length)
                else:
                    length = int(length / SUM_RATIO_ENG) + 1
                    command = "\nPlease summarize the content as maximum {} bullets:\n\n".format(length)

                print("Trying to summarize section as {} sentences".format(length))
                print('section: {}'.format(section['text']))

                messages.append({'role': 'user', 'content': "{}{}{}".format(message, chunk, command)})
                section['messages'] = messages

                summary = complete(messages)
                if summary == 'Error':
                    # Thirdly, try to summarize each chunk of section separately
                    chunk_array = chunk.split('\n')
                    chunk_index = 0
                    chunk_size = 0
                    chunk_segment = ''
                    previous_summary = ''
                    for chunk_line in chunk_array:
                        chunk_size += len(chunk_line.split(' '))
                        if chunk_size > MAX_CHUNK_SIZE:
                            chunk_size = 0
                            chunk_index += 1

                            messages = [
                                {'role': 'system', 'content': 'You are a helpful assistant'},
                                {'role': 'user', 'content': "Previous summary is:\n{}\n".format(previous_summary)}
                            ]

                            # Count the number of sentences of message
                            length = count_sentences("{}\n{}".format(previous_summary, chunk_segment))

                            if language == 'ko':
                                length = int(length / SUM_RATIO_KOR) + 1
                                command = "\nPlease summarize the content with previous summary as maximum {} bullets in Korean:\n\n".format(length)
                            else:
                                length = int(length / SUM_RATIO_ENG) + 1
                                command = "\nPlease summarize the content with previous summary as maximum {} bullets:\n\n".format(length)

                            print("Trying to summarize each chunk of section as {} sentences".format(length))
                            print('section: {}'.format(section['text']))

                            messages.append({'role': 'user', 'content': "{}{}{}".format(message, chunk_segment, command)})
                            summary = complete(messages)
                            print("previous summary: {}".format(previous_summary))
                            print("chunk summary: {}".format(summary))
                            previous_summary = summary
                            chunk_segment = ''
                        
                        chunk_segment += chunk_line + '\n'

                    if chunk_segment != '':
                        messages = [
                            {'role': 'system', 'content': 'You are a helpful assistant'},
                            {'role': 'user', 'content': "Previous summary is:\n{}\n".format(previous_summary)}
                        ]

                        if language == 'ko':
                            command = "\nPlease summarize the content with previous summary as maximum {} bullets in Korean:\n\n".format(length)
                        else:
                            command = "\nPlease summarize the content with previous summary as maximum {} bullets:\n\n".format(length)

                        print("Trying to summarize each chunk of section as {} sentences".format(length))
                        print('section: {}'.format(section['text']))

                        messages.append({'role': 'user', 'content': "{}{}{}".format(message, chunk_segment, command)})
                        summary = complete(messages)
                        print("previous summary: {}".format(previous_summary))
                        print("chunk summary: {}".format(summary))

                section['summary'] = summary

                print('section: {}'.format(section['text']))
                print("summary: {}".format(summary))
            
            # Finally summarize all the sections
            messages = [
                {'role': 'system', 'content': 'You are a helpful assistant'}
            ]
            if language == 'ko':
                message = 'These are title and sections.\n\n'
            else:
                message = "These are title and sections.\n\n"
            message += "Title: {}\n".format(strcuture['title'])
            chunk = ''
            for section in strcuture['sections']:
                if section['type'] == 'preface':
                    chunk += "Section: {}\n".format(section['text'])
                    chunk += "{}\n".format(section['summary'])
                else:
                    chunk += "Section: {}\n".format(section['text'])
                    chunk += "{}\n".format(section['summary'])
            # Count the number of sentences of message
            length = count_sentences(chunk)

            if language == 'ko':
                length = int(length / SUM_RATIO_SUMMARY) + 1        # Korean summarization ratio is too high, so apply English ratio
                command = "\nPlease summarize all sections as a {} sentence long paragraph in Korean:\n".format(length)
            else:
                length = int(length / SUM_RATIO_SUMMARY) + 1
                command = "\nPlease summarize all sections as a {} sentence long paragraph:\n".format(length)

            print("Trying to summarize section as {} sentences".format(length))

            messages.append({'role': 'user', 'content': "{}{}{}".format(message, chunk, command)})
            strcuture['messages'] = messages

            print("Before: {}\n".format(messages[1]['content']))
            summary = complete(messages)

        print("Final summary: {}".format(summary))
        strcuture['summary'] = summary

    else:
        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant'}
        ]
        if language == 'ko':
            message = '글의 구조는 title > h1 > h2 > h3 > p 의 순서이다.\n\n'
        else:
            message = "Text strcuture is title > h1 > h2 > h3 > h4 > p.\n\n"
        # message += "please summarize the content as maximum {} sentences paragraph from:\n".format(MAX_LINES)
        message += "title: {}\n".format(strcuture['title'])

        chunk = ''
        for item in content:
            chunk += "{}: {}\n".format(item['type'], item['text'])

        # Count the number of sentences of message
        length = count_sentences(chunk)

        if language == 'ko':
            length = int(length / SUM_RATIO_KOR / SUM_RATIO_SUMMARY) + 1
            command = "\nPlease summarize the text as a {} sentence long paragraph in Korean:\n".format(length)
        else:
            length = int(length / SUM_RATIO_ENG / SUM_RATIO_SUMMARY) + 1
            command = "\nPlease summarize the text as a {} sentence long paragraph:\n".format(length)

        print("Trying to summarize all as {} sentences without section".format(length))

        messages.append({'role': 'user', 'content': "{}{}{}".format(message, chunk, command)})
        strcuture['messages'] = messages

        # Write structure as json text into a file
        with open('structure.json', 'w') as f:
            f.write(json.dumps(strcuture, indent=4))

        print("Before: {}\n".format(messages[1]['content']))
        summary = complete(messages)
        print("Final summary: {}".format(summary))
        strcuture['summary'] = summary

    return {
        'title': strcuture['title'],
        'summary': strcuture['summary']
    }

    return {'structure': json.dumps(strcuture, indent=4)}


@app.route('/')
def index():
    if 'url' not in session:
        session['url'] = 'https://edition.cnn.com/2023/04/15/americas/darien-gap-migrants-colombia-panama-whole-story-cmd-intl/index.html'
    return render_template('index.html', url=session.get('url'))

@app.route('/summarize', methods=['POST'])
def summarize():
    url = request.form['url']
    session['url'] = url
    print(url)
    result = read_webpage(url)
    if result['result'] == 'success':
        summary = summarize_content(result['title'], result['content'], result['language'])
        if 'title' in summary:
            return render_template('index.html', url=session.get('url'), title=summary['title'], content=summary['summary'])
        else:
            return render_template('index.html', url=session.get('url'), structure=summary['structure'])
        # return render_template('index.html', title=result['title'], content=json.dumps(result['content'], indent=4))
    else:
        return render_template('index.html', url=session.get('url'), title=result['status_code'], content=result['err_msg'])

if len(sys.argv) > 1:
    # get the url from the command line
    url = sys.argv[1]
    print(url)

    # read the webpage
    result = read_webpage(url)
    if result['result'] == 'success':
        print(result['title'])
        print(json.dumps(result['content'], indent=4))
    else:
        print(result['status_code'])
        print(result['content'])
    
    sys.exit(0)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
