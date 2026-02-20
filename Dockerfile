FROM python:3.13-alpine

LABEL maintainer="avtobusikstoy@gmail.com"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN python -m pip install -U pip && \
    pip install --no-cache-dir -r requirements.txt

ENV IN_DOCKER=true

COPY . .

ENTRYPOINT ["python", "run.py"]

VOLUME ["/labs", "/vault", "/db_data", "/logging"]
