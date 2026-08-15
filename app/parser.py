import re

from app.models import ResourceSpec


def parse_request(text: str) -> ResourceSpec:
    value = text.lower()
    s3 = bool(re.search(r"\b(s3|bucket|object storage)\b", value))
    lam = bool(re.search(r"\b(lambda|serverless function|function)\b", value))
    dynamo = bool(re.search(r"\b(dynamodb|dynamo db|key.value table|nosql)\b", value))
    trigger = s3 and lam and bool(re.search(r"\b(upload|object created|trigger|event)\b", value))
    return ResourceSpec(
        s3_bucket=s3,
        lambda_function=lam,
        dynamodb_table=dynamo,
        iam_role=lam,
        s3_trigger=trigger,
    )
