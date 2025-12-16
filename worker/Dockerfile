FROM python:3.11-slim

WORKDIR /worker

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código do worker
COPY worker.py .
COPY ai_agent.py .
COPY notifications.py .

# Variáveis de ambiente padrão
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV LLM_PROVIDER=google
ENV PYTHONUNBUFFERED=1

# Comando de execução
CMD ["python", "-u", "worker.py"]