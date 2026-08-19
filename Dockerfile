FROM python:3.11-slim
WORKDIR /app
ARG TERRAFORM_VERSION=1.15.9
ARG TARGETARCH=amd64
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip ca-certificates \
    && cd /tmp \
    && curl -fsSLO "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TARGETARCH}.zip" \
    && curl -fsSLO "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_SHA256SUMS" \
    && grep " terraform_${TERRAFORM_VERSION}_linux_${TARGETARCH}.zip$" "terraform_${TERRAFORM_VERSION}_SHA256SUMS" | sha256sum -c - \
    && unzip "terraform_${TERRAFORM_VERSION}_linux_${TARGETARCH}.zip" -d /usr/local/bin \
    && terraform version \
    && rm -rf /var/lib/apt/lists/* /tmp/terraform_*
COPY . .
RUN pip install --no-cache-dir .
HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=5 CMD curl -fsS http://localhost:8000/health || exit 1
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
