FROM python:3.11-slim

# ffmpeg wajib ada di image ini
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server_simple.py .
COPY template.jpg .

EXPOSE 8000
CMD ["uvicorn", "server_simple:app", "--host", "0.0.0.0", "--port", "8000"]
