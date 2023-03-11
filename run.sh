# Run python source locally

ps -ef | grep ngrok | grep -v grep | awk '{print "kill " $2}' | sh -x
sleep 2
rm nohup.out
nohup ../ngrok http 5000 --log=stdout &
sleep 2
URL=`cat nohup.out  | grep https | awk '{print $8}' | sed -e 's/url=//g'`
export URL
python src/webhook.py
