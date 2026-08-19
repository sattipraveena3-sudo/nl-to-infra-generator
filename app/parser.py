import json
import os
import re

import httpx

from app.models import ResourceSpec

SYSTEM_PROMPT = (
    "Return JSON only for a supported AWS plan with these fields: project_name, region, "
    "s3_bucket, lambda_function, dynamodb_table, iam_role, s3_trigger, "
    "bucket_versioning, bucket_encryption, lambda_memory_mb, and "
    "lambda_timeout_seconds. Supported resources are S3, Lambda, DynamoDB, IAM, and S3 "
    "notifications. Use secure defaults."
)


def deterministic_parse(text, project_name):
    v = text.lower()
    s3 = bool(re.search(r"\b(s3|bucket|object storage)\b", v))
    lam = bool(re.search(r"\b(lambda|serverless function|function)\b", v))
    dynamo = bool(re.search(r"\b(dynamodb|dynamo db|nosql)\b", v))
    trigger = (
        s3 and lam and bool(re.search(r"\b(upload|object created|trigger|event|notification)\b", v))
    )
    memory = re.search(r"(\d+)\s*(?:mb|megabytes?)", v)
    timeout = re.search(r"timeout(?:\s+of|\s*=|\s+)?\s*(\d+)", v)
    region = re.search(
        r"\b(us-(?:east|west)-[12]|eu-(?:west|central)-[123]|ap-(?:south|southeast|northeast)-[123])\b",
        v,
    )
    return ResourceSpec(
        project_name=project_name,
        region=region.group(1) if region else "us-east-1",
        s3_bucket=s3,
        lambda_function=lam,
        dynamodb_table=dynamo,
        iam_role=lam,
        s3_trigger=trigger,
        bucket_versioning="disable versioning" not in v,
        bucket_encryption="disable encryption" not in v,
        lambda_memory_mb=int(memory.group(1)) if memory else 256,
        lambda_timeout_seconds=int(timeout.group(1)) if timeout else 30,
    )


def ollama_parse(text, project_name):
    response = httpx.post(
        os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/") + "/api/chat",
        json={
            "model": os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b"),
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"project_name={project_name}\nrequest={text}"},
            ],
            "options": {"temperature": 0},
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = json.loads(response.json()["message"]["content"])
    payload["project_name"] = project_name
    return ResourceSpec.model_validate(payload)


def parse_request(text, project_name, parser="auto"):
    if parser == "deterministic":
        return deterministic_parse(text, project_name), "deterministic"
    try:
        return ollama_parse(text, project_name), "ollama"
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValueError):
        if parser == "ollama":
            raise
        return deterministic_parse(text, project_name), "deterministic-fallback"
