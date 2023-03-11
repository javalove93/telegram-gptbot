. ./00.setenv.sh
cd src
gcloud --project $PROJECT builds submit --tag gcr.io/$PROJECT/$MODULE
