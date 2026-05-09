FROM python:3.12-slim
WORKDIR /app
COPY backend /app/backend
RUN pip install fastapi uvicorn pydantic
ENV PYTHONPATH=/app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
