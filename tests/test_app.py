import shutil
import pytest
from fastapi.testclient import TestClient
from app.generator import generate_project
from app.main import app
from app.parser import deterministic_parse
from app.validator import correct_project,security_scan,validate_project

def test_parser_extracts_dependencies_and_parameters():
    spec=deterministic_parse("S3 bucket and Lambda triggered on upload with 512 MB and timeout 45 in us-west-2","demo-stack")
    assert spec.s3_bucket and spec.lambda_function and spec.s3_trigger and spec.iam_role
    assert spec.lambda_memory_mb==512 and spec.lambda_timeout_seconds==45 and spec.region=="us-west-2"
def test_project_contains_secure_modular_resources():
    files=generate_project(deterministic_parse("S3 Lambda upload DynamoDB","demo-stack"))
    assert {"versions.tf","variables.tf","main.tf","outputs.tf","lambda/handler.py"}<=files.keys()
    assert "aws_s3_bucket_public_access_block" in files["main.tf"] and "server_side_encryption" in files["main.tf"]
    assert security_scan(files)==[]
def test_security_scan_flags_unsafe_configuration(): assert security_scan({"main.tf":'resource "aws_s3_bucket" "x" { acl="public-read" }'})
def test_structural_validator_rejects_broken_project(monkeypatch):
    monkeypatch.setattr(shutil,"which",lambda _:None);assert not validate_project({"main.tf":'resource "aws_s3_bucket" "x" {'},False).valid
def test_api_returns_zip_and_files(monkeypatch):
    monkeypatch.setattr(shutil,"which",lambda _:None)
    with TestClient(app) as client:
        r=client.post('/generate',json={'request':'create encrypted S3 bucket and DynamoDB','project_name':'advanced-demo','parser':'deterministic','run_plan':False})
        assert r.status_code==200;body=r.json();assert body['validation']['valid'] and body['bundle_base64'] and 'main.tf' in body['files']
@pytest.mark.skipif(not shutil.which("terraform"),reason="Terraform binary unavailable")
def test_real_terraform_fmt_init_validate():
    files=generate_project(deterministic_parse("S3 bucket","integration-demo"))
    first=validate_project(files,run_plan=False)
    corrected,_=correct_project(files,first)
    result=validate_project(corrected,run_plan=False)
    combined="\n".join(step.output for step in result.steps)
    if "Failed to load plugin schemas" in combined:
        pytest.skip("Host sandbox cannot execute downloaded Terraform providers")
    assert result.valid,result.model_dump()
