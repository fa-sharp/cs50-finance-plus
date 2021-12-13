FROM python:3.9.7-slim

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt --no-deps

COPY ./app /app/

WORKDIR /app

RUN useradd flask
USER flask

EXPOSE 5000

ENTRYPOINT ["bash", "/app/bin/run.sh"]