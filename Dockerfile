FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
WORKDIR /workspace
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
COPY . /workspace
EXPOSE 8889
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8889", "--no-browser", "--allow-root", "--ServerApp.root_dir=/workspace"]
