from fastapi.testclient import TestClient
from app.generator import generate_terraform
from app.main import app
from app.parser import parse_request
from app.validator import validate_terraform

def test_parser_recognizes_supported_resources():
    spec=parse_request("S3 bucket with Lambda on upload and DynamoDB")
    assert spec.s3_bucket and spec.lambda_function and spec.dynamodb_table and spec.s3_trigger
def test_generated_hcl_contains_resources():
    code=generate_terraform(parse_request("bucket and serverless function"))
    assert 'aws_s3_bucket' in code and 'aws_lambda_function' in code
def test_validator_rejects_broken_hcl(): assert not validate_terraform('resource "aws_s3_bucket" "x" {').valid
def test_api():
    with TestClient(app) as client:
        r=client.post('/generate',json={'request':'create an S3 bucket'})
        assert r.status_code==200 and r.json()['validation']['valid']
