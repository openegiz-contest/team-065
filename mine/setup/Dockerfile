FROM python:3.12-slim
WORKDIR /app
COPY model.json setup_twins.py ./
USER nobody
CMD ["python", "setup_twins.py"]
