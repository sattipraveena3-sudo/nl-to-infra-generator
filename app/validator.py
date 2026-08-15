import shutil
import subprocess
import tempfile
from pathlib import Path

from app.models import ValidationResult


def validate_terraform(code: str) -> ValidationResult:
    if not shutil.which("terraform"):
        balanced = code.count("{") == code.count("}")
        resources = 'resource "aws_' in code
        return ValidationResult(valid=balanced and resources, commands=["structural validation"], output="Terraform binary unavailable; completed deterministic brace and resource validation.")
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, "main.tf").write_text(code, encoding="utf-8")
        commands = [["terraform","init","-backend=false","-input=false"],["terraform","validate","-json"]]
        output=[]
        for command in commands:
            result=subprocess.run(command,cwd=directory,text=True,capture_output=True,timeout=120)
            output.append(result.stdout+result.stderr)
            if result.returncode:
                return ValidationResult(valid=False,commands=[" ".join(c) for c in commands],output="\n".join(output))
        return ValidationResult(valid=True,commands=[" ".join(c) for c in commands],output="\n".join(output))
