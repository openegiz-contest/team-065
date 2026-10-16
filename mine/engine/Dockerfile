# Kyzyl-Tas mine simulation engine. Base image already pulled by the OpenEgiz stack
# (examples/mine/Dockerfile uses the same python:3.12-slim), so this adds ~0 extra pull size.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
# Non-root, matching the reference examples/mine/Dockerfile convention.
USER nobody

CMD ["python", "engine.py"]
