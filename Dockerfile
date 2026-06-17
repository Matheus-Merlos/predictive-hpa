FROM python:3.10.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 hpa-group && \
    useradd -u 1000 -g hpa-group -s /bin/bash -m hpa-user

WORKDIR /predictive-hpa

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/* /predictive-hpa/

RUN mkdir -p /var/lib/predictive-hpa/duckdb && \
    chown -R hpa-user:hpa-group /predictive-hpa /var/lib/predictive-hpa/duckdb

USER 1000

CMD [ "python3", "main.py" ]
