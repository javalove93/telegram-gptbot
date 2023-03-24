# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.8-slim

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
RUN pip install Flask gunicorn openai google-cloud-translate transformers firebase-admin

ENV GOOGLE_APPLICATION_CREDENTIALS=/app/sa-key.json

# Run the web service on container startup. Here we use the gunicorn
# webserver, with only one worker process and only one thread per worker.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind :8080 --workers 4 --threads 1 --timeout 0 webhook:app
