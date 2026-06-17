FROM python:3.10.12-slim-bookworm

WORKDIR /predictive-hpa
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/* /predictive-hpa/
CMD [ "python3", "main.py" ]
