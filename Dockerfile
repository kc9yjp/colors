FROM python:3.12-alpine
WORKDIR /app
COPY index.html .
COPY server.py .
COPY style.css .
COPY script.js .
RUN mkdir -p /data
EXPOSE 80
CMD ["python", "server.py"]
