. ./00.setenv.sh
gcloud --project $PROJECT run deploy --image gcr.io/$PROJECT/$MODULE --platform managed --allow-unauthenticated --region asia-northeast3 $MODULE

URL=`gcloud --project $PROJECT run services list | grep $MODULE | awk '{print $4}'`

curl -X POST -d "url=$URL" $URL/setWebhook
