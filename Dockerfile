FROM python:3.12-slim

WORKDIR /app

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードコピー
COPY src/ src/
COPY main.py .

# デフォルトエントリーポイント
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
