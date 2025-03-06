FROM python:3.10-alpine

LABEL maintainer="avtobusikstoy@gmail.com"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN apk update && \
    python -m venv .venv && \
    .venv/bin/python -m pip install -U pip && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt

ENV IN_DOCKER=true

COPY . .

ENTRYPOINT [".venv/bin/python", "run.py"]

VOLUME ["/labs", "/vault", "/db_data"]
