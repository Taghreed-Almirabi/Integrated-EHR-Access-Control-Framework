FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY system_demo.py .
COPY performance_evaluation.py .

RUN mkdir -p data results \
    && useradd --create-home ehruser \
    && chown -R ehruser:ehruser /app

USER ehruser

VOLUME ["/app/data"]

CMD ["python", "system_demo.py"]