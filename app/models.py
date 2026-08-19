from typing import Literal

from pydantic import BaseModel, Field, model_validator


class InfraRequest(BaseModel):
    request: str = Field(min_length=8, max_length=4000)
    project_name: str = Field(default="generated-infrastructure", pattern=r"^[a-z][a-z0-9-]{2,39}$")
    parser: Literal["auto", "deterministic", "ollama"] = "auto"
    run_plan: bool = True


class ResourceSpec(BaseModel):
    project_name: str
    region: str = "us-east-1"
    s3_bucket: bool = False
    lambda_function: bool = False
    dynamodb_table: bool = False
    iam_role: bool = False
    s3_trigger: bool = False
    bucket_versioning: bool = True
    bucket_encryption: bool = True
    lambda_memory_mb: int = Field(default=256, ge=128, le=10240)
    lambda_timeout_seconds: int = Field(default=30, ge=1, le=900)

    @model_validator(mode="after")
    def dependencies(self):
        if self.s3_trigger and not (self.s3_bucket and self.lambda_function):
            raise ValueError("S3 trigger requires S3 and Lambda")
        if self.lambda_function:
            self.iam_role = True
        return self


class ValidationStep(BaseModel):
    name: str
    command: str
    success: bool
    exit_code: int
    output: str
    duration_seconds: float


class ValidationResult(BaseModel):
    valid: bool
    mode: str
    steps: list[ValidationStep]
    security_findings: list[str]
    corrected: bool = False
    correction_summary: str | None = None


class InfraResponse(BaseModel):
    specification: ResourceSpec
    parser_used: str
    files: dict[str, str]
    validation: ValidationResult
    bundle_base64: str
