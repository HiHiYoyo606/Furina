FROM python:3.13-slim
WORKDIR /app
COPY . .
EXPOSE 8080
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
