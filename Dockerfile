FROM python:3.11-slim

WORKDIR /app

# Prevent python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000

# Copy application files
COPY . /app

# Expose web server ports (Koyeb/Docker default 8000, fallback 5070)
EXPOSE 8000 5070

CMD ["python3", "server.py"]
