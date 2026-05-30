# Imagem base oficial enxuta do Python
FROM python:3.12-slim

# Evita arquivos .pyc e garante logs sem buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala dependências primeiro (melhor aproveitamento de cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY gerar_certificado.py app.py ./
COPY templates ./templates

# Porta da interface web
EXPOSE 5000

# Inicia a interface web (Flask)
CMD ["python", "app.py"]
