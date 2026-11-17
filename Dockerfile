FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV DATABASE_PATH=/data/network.db
RUN mkdir -p /data && chown -R 10001:10001 /data /app
USER 10001
EXPOSE 5000
CMD ["flask", "--app", "app:app", "run", "--host=0.0.0.0", "--port=5000"]
