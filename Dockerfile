FROM python:3.10-alpine

LABEL maintainer="avtobusikstoy@gmail.com"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN apk update && \
    apk add make && \
    python -m pip install -U pip && \
    pip install --no-cache-dir -r requirements.txt

ENV IN_DOCKER=true

COPY . .

ENTRYPOINT ["python", "run.py"]

VOLUME ["/vault", "/db_data"]
