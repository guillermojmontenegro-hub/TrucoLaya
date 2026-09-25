FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY truco ./truco
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir .
ENV HF_HOME=/models
EXPOSE 8000
CMD ["uvicorn", "truco.api:app", "--host", "0.0.0.0", "--port", "8000"]
