import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from app.models import ValidationResult, ValidationStep


def security_scan(files):
    code = "\n".join(files.values())
    findings = []
    if 'acl="public' in code.replace(" ", ""):
        findings.append("public S3 ACL detected")
    if 'Action="*"' in code.replace(" ", ""):
        findings.append("wildcard IAM action detected")
    if 'aws_s3_bucket"' in code and "aws_s3_bucket_public_access_block" not in code:
        findings.append("S3 public-access block missing")
    if "aws_dynamodb_table" in code and "server_side_encryption" not in code:
        findings.append("DynamoDB encryption missing")
    return findings


def _run(name, command, cwd, env=None):
    started = time.perf_counter()
    try:
        r = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, timeout=180)
        output = (r.stdout + r.stderr)[-12000:]
        return ValidationStep(
            name=name,
            command=" ".join(command),
            success=r.returncode == 0,
            exit_code=r.returncode,
            output=output,
            duration_seconds=round(time.perf_counter() - started, 3),
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return ValidationStep(
            name=name,
            command=" ".join(command),
            success=False,
            exit_code=124,
            output=str(e),
            duration_seconds=round(time.perf_counter() - started, 3),
        )


def validate_project(files, run_plan=True):
    findings = security_scan(files)
    if not shutil.which("terraform"):
        code = "\n".join(v for k, v in files.items() if k.endswith(".tf"))
        ok = code.count("{") == code.count("}") and 'resource "aws_' in code
        step = ValidationStep(
            name="structural",
            command="built-in structural validator",
            success=ok,
            exit_code=0 if ok else 1,
            output="Terraform unavailable; checked balanced blocks and AWS resource presence.",
            duration_seconds=0,
        )
        return ValidationResult(
            valid=ok and not findings, mode="structural", steps=[step], security_findings=findings
        )
    with tempfile.TemporaryDirectory() as directory:
        for name, content in files.items():
            path = Path(directory, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_DEFAULT_REGION": "us-east-1",
            }
        )
        commands = [
            ("fmt", ["terraform", "fmt", "-check", "-recursive"]),
            ("init", ["terraform", "init", "-backend=false", "-input=false", "-no-color"]),
            ("validate", ["terraform", "validate", "-no-color"]),
        ]
        if run_plan:
            commands.append(
                (
                    "plan",
                    [
                        "terraform",
                        "plan",
                        "-refresh=false",
                        "-lock=false",
                        "-input=false",
                        "-no-color",
                        "-out=plan.tfplan",
                    ],
                )
            )
        steps = []
        for name, command in commands:
            step = _run(name, command, directory, env)
            steps.append(step)
            if not step.success:
                break
        return ValidationResult(
            valid=all(s.success for s in steps) and not findings,
            mode="terraform",
            steps=steps,
            security_findings=findings,
        )


def correct_project(files, result):
    corrected = dict(files)
    summary = []
    if any(s.name == "fmt" and not s.success for s in result.steps) and shutil.which("terraform"):
        with tempfile.TemporaryDirectory() as directory:
            for name, content in corrected.items():
                path = Path(directory, name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            subprocess.run(
                ["terraform", "fmt", "-recursive"], cwd=directory, capture_output=True, timeout=30
            )
            for name in list(corrected):
                corrected[name] = Path(directory, name).read_text(encoding="utf-8")
        summary.append("formatted Terraform files")
    return corrected, "; ".join(summary) or "no safe automatic correction available"


def validate_terraform(code):
    return validate_project({"main.tf": code}, run_plan=False)
