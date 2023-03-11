. ./00.setenv.sh

docker pull gcr.io/$PROJECT/$MODULE
docker run --rm --name $MODULE -d -p 8080:8080 gcr.io/$PROJECT/$MODULE

ps -ef | grep ngrok | grep -v grep | awk '{print "kill " $2}' | sh -x
sleep 2
rm nohup.out
nohup ../ngrok http 8080 --log=stdout &
sleep 2
URL=`cat nohup.out  | grep https | awk '{print $8}' | sed -e 's/url=//g'`

sleep 1
docker logs -f $MODULE &
curl -X POST -d "url=$URL" http://localhost:8080/setWebhook 
echo ""

sleep 1
echo Enter to stop...
read a

docker stop $MODULE

