FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN adduser --disabled-password appuser
WORKDIR /code
COPY . .
RUN pip install -r requirements.txt
USER appuser
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
