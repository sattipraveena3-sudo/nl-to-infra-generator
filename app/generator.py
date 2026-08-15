from app.models import ResourceSpec


HEADER = '''terraform {
  required_version = ">= 1.6.0"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.0" } }
}

provider "aws" {
  region = "us-east-1"
  access_key = "test"
  secret_key = "test"
  skip_credentials_validation = true
  skip_metadata_api_check = true
  skip_requesting_account_id = true
  s3_use_path_style = true
  endpoints {
    s3 = "http://localstack:4566"
    lambda = "http://localstack:4566"
    dynamodb = "http://localstack:4566"
    iam = "http://localstack:4566"
  }
}
'''


def generate_terraform(spec: ResourceSpec) -> str:
    blocks = [HEADER]
    if spec.s3_bucket:
        blocks.append('resource "aws_s3_bucket" "uploads" { bucket = "portfolio-upload-events" }')
    if spec.iam_role:
        blocks.append('''resource "aws_iam_role" "lambda" {
  name = "portfolio-lambda-role"
  assume_role_policy = jsonencode({Version="2012-10-17",Statement=[{Action="sts:AssumeRole",Effect="Allow",Principal={Service="lambda.amazonaws.com"}}]})
}''')
    if spec.lambda_function:
        blocks.append('''data "archive_file" "lambda" { type="zip" source_content="def handler(event, context): return {'statusCode': 200}" source_content_filename="handler.py" output_path="/tmp/lambda.zip" }
resource "aws_lambda_function" "processor" { filename=data.archive_file.lambda.output_path function_name="upload-processor" role=aws_iam_role.lambda.arn handler="handler.handler" runtime="python3.11" source_code_hash=data.archive_file.lambda.output_base64sha256 }''')
    if spec.dynamodb_table:
        blocks.append('''resource "aws_dynamodb_table" "records" { name="portfolio-records" billing_mode="PAY_PER_REQUEST" hash_key="id" attribute { name="id" type="S" } }''')
    if spec.s3_trigger:
        blocks.append('''resource "aws_lambda_permission" "s3" { statement_id="AllowS3Invoke" action="lambda:InvokeFunction" function_name=aws_lambda_function.processor.function_name principal="s3.amazonaws.com" source_arn=aws_s3_bucket.uploads.arn }
resource "aws_s3_bucket_notification" "upload" { bucket=aws_s3_bucket.uploads.id lambda_function { lambda_function_arn=aws_lambda_function.processor.arn events=["s3:ObjectCreated:*"] } depends_on=[aws_lambda_permission.s3] }''')
    return "\n\n".join(blocks) + "\n"
