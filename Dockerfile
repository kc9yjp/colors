FROM python:3.12-alpine
WORKDIR /app
COPY index.html .
COPY server.py .
RUN mkdir -p /data
EXPOSE 80
CMD ["python", "server.py"]
