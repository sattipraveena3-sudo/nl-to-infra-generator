from pydantic import BaseModel, Field


class InfraRequest(BaseModel):
    request: str = Field(min_length=5, max_length=2000)


class ResourceSpec(BaseModel):
    s3_bucket: bool = False
    lambda_function: bool = False
    dynamodb_table: bool = False
    iam_role: bool = False
    s3_trigger: bool = False


class ValidationResult(BaseModel):
    valid: bool
    commands: list[str]
    output: str
    corrected: bool = False


class InfraResponse(BaseModel):
    specification: ResourceSpec
    terraform: str
    validation: ValidationResult
