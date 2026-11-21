FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 APP_ENV=production
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# run as an unprivileged user; the app only needs to write the feedback database
RUN useradd --create-home app && mkdir -p instance && chown -R app /app/instance
USER app
EXPOSE 8000
# One worker keeps the in-memory rate limiter consistent; threads handle concurrency.
# SECRET_KEY (and optionally ADMIN_PASSWORD_HASH) must be passed at run time:
#   docker run -p 8000:8000 --env-file .env movie-recommender
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:8000", "server:app"]
