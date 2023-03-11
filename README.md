# telegram-gptbot

ChatGPT를 편하게 불러쓸수 있게 텔레그램 봇에 openai API를 연동해서 개인적으로 쓰기 위한 Python 기반의 프로그램입니다.\
메신저로 아무때나 쉽게 쓸수 있고 필요하면 다른 챗/채널에도 연결할 수 있어 편리합니다.\
우선은 OpenAI에 가셔서 API 사용을 위한 유료 가입을 하셔야 합니다. API 비용은 API 호출당 charging으로 chatgpt용 모델의 경우 많이 저렴합니다.\
제가 사용해 보니 비용은 ChatGPT 유료의 거의 1/10 수준인데 응답속도는 ChatGPT 프리미엄급입니다. 다만, ChatGPT 처럼 한자씩 typing 하는 효과는 없습니다.\
간만에 코딩도 잼있있고 해서 혹시 궁금하신 분들을 위해 봇 소스 github에 공유합니다.\
봇의 런타임은 Google Cloud의 Cloud Run에서 돌립니다. 서버 없이 바로 사용할 수 있어 편리하고, 컨테이너는 바로 HTTPS(SSL) endpoint를 만들 수 있으므로 봇 운영에 편리합니다.

## 소스 및 사용 방법 설명

0. Google Cloud 생성
* 따로 안내는 하지 않겠습니다.
* 봇의 webhook 호출을 받기 위한 서비스 목적으로, 만약 개인적으로 운영하는 서버가 있으면 ngrok으로 포트포워딩 하셔도 됩니다.

1. 텔레그램 챗봇 생성
* 구글링 해 보면 너무 많습니다. BotFather 님에게 생성 요청하시면 됩니다.
* 생성된 봇 Token을 소스에 넣으면 됩니다.

2. OpenAI API Key
* 역시 구글링 해 보시면 가입하는 방법 나옵니다.

3. 소스
* 단 하나의 소스 src/webhook.py 로 이루어져 있습니다.
* 아주 심플한 Flask 웹프로그램에 심지어 코딩도 Copilot 친구의 도움 받아서 했기 때문에 중복 코드 등도 많습니다 ^^;;
* 텔레그램 봇의 Token과 OpenAI API Key을 각자 받아서 넣으시면 됩니다.
* 봇의 abusing을 막기 위해 제 텔레그램 Chat ID를 if 문으로 체크하는 부분이 있는데, 각자 ID가 다르므로 일반 remark로 막고 확인 후에 변경하시면 됩니다.

4. 실행 방법 - 01 ~ 03 차례로 실행하면 됩니다.
* 00.setenv.sh - 컨테이너 이름, GCP Project ID 등 지정
* 01.build.sh - 컨테이너 빌드(Cloud Build 사용)
* 02.test_local.sh - 컨테이너를 Cloud Run으로 올리지 않고 개발 환경에서 바로 테스트하고자 할 경우
* 03.deploy.sh - 컨테이너를 Cloud Run으로 배포 후에 텔레그램에 webhook endpoint로 셋업
* run.sh  - 컨테이너 없이 바로 Python 코드로 테스트 하고자 할 경우 사용하는 스크립트
