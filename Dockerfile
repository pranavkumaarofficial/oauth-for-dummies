FROM python:3.12-slim

LABEL maintainer="pranavkumaarofficial"
LABEL description="OAuth for Dummies — Learn OAuth 2.0 the easy way"

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
