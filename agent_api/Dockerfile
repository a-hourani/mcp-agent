FROM python:3.10-slim

WORKDIR /app
COPY . /app

# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1
EXPOSE 7000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7000"]
