from textwrap import dedent

from app.models import ResourceSpec


def _block(enabled: bool, value: str) -> str:
    return dedent(value).strip() if enabled else ""


def generate_project(spec: ResourceSpec) -> dict[str, str]:
    versions = dedent(
        f'''\
        terraform {{
          required_version = ">= 1.6.0"

          required_providers {{
            aws = {{
              source  = "hashicorp/aws"
              version = "~> 5.0"
            }}
            archive = {{
              source  = "hashicorp/archive"
              version = "~> 2.4"
            }}
          }}
        }}

        provider "aws" {{
          region                      = var.aws_region
          access_key                  = var.aws_access_key
          secret_key                  = var.aws_secret_key
          skip_credentials_validation = var.use_localstack
          skip_metadata_api_check     = var.use_localstack
          skip_requesting_account_id  = var.use_localstack
          s3_use_path_style           = var.use_localstack

          endpoints {{
            dynamodb = var.use_localstack ? var.localstack_endpoint : null
            iam      = var.use_localstack ? var.localstack_endpoint : null
            lambda   = var.use_localstack ? var.localstack_endpoint : null
            s3       = var.use_localstack ? var.localstack_endpoint : null
            sts      = var.use_localstack ? var.localstack_endpoint : null
          }}
        }}
        '''
    )

    variables = dedent(
        f'''\
        variable "aws_region" {{
          description = "AWS region for generated resources."
          type        = string
          default     = "{spec.region}"
        }}

        variable "use_localstack" {{
          description = "Disable AWS account checks for the local validation stack."
          type        = bool
          default     = true
        }}

        variable "localstack_endpoint" {{
          description = "LocalStack edge endpoint."
          type        = string
          default     = "http://localstack:4566"
        }}

        variable "aws_access_key" {{
          type      = string
          default   = "test"
          sensitive = true
        }}

        variable "aws_secret_key" {{
          type      = string
          default   = "test"
          sensitive = true
        }}

        variable "name_prefix" {{
          description = "Prefix used for resource names."
          type        = string
          default     = "{spec.project_name}"
        }}
        '''
    )

    resources = [
        dedent(
            '''\
            locals {
              common_tags = {
                Project     = var.name_prefix
                ManagedBy   = "Terraform"
                Environment = "demo"
              }
            }
            '''
        ).strip()
    ]
    outputs: list[str] = []

    s3 = _block(
        spec.s3_bucket,
        '''
        resource "aws_s3_bucket" "uploads" {
          bucket        = "${var.name_prefix}-uploads"
          force_destroy = true
          tags          = local.common_tags
        }

        resource "aws_s3_bucket_public_access_block" "uploads" {
          bucket                  = aws_s3_bucket.uploads.id
          block_public_acls       = true
          block_public_policy     = true
          ignore_public_acls      = true
          restrict_public_buckets = true
        }
        ''',
    )
    if s3:
        resources.append(s3)
        outputs.append(
            'output "bucket_name" {\n  value = aws_s3_bucket.uploads.id\n}'
        )

    versioning = _block(
        spec.s3_bucket and spec.bucket_versioning,
        '''
        resource "aws_s3_bucket_versioning" "uploads" {
          bucket = aws_s3_bucket.uploads.id

          versioning_configuration {
            status = "Enabled"
          }
        }
        ''',
    )
    if versioning:
        resources.append(versioning)

    encryption = _block(
        spec.s3_bucket and spec.bucket_encryption,
        '''
        resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
          bucket = aws_s3_bucket.uploads.id

          rule {
            apply_server_side_encryption_by_default {
              sse_algorithm = "AES256"
            }
          }
        }
        ''',
    )
    if encryption:
        resources.append(encryption)

    iam = _block(
        spec.iam_role,
        '''
        resource "aws_iam_role" "lambda" {
          name = "${var.name_prefix}-lambda-role"
          assume_role_policy = jsonencode({
            Version = "2012-10-17"
            Statement = [{
              Action    = "sts:AssumeRole"
              Effect    = "Allow"
              Principal = { Service = "lambda.amazonaws.com" }
            }]
          })
          tags = local.common_tags
        }

        resource "aws_iam_role_policy" "lambda_logs" {
          name = "${var.name_prefix}-logs"
          role = aws_iam_role.lambda.id
          policy = jsonencode({
            Version = "2012-10-17"
            Statement = [{
              Effect = "Allow"
              Action = [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
              ]
              Resource = "arn:aws:logs:*:*:*"
            }]
          })
        }
        ''',
    )
    if iam:
        resources.append(iam)

    environment = ""
    if spec.dynamodb_table:
        environment = dedent(
            '''
            environment {
              variables = {
                TABLE_NAME = aws_dynamodb_table.records.name
              }
            }
            '''
        ).rstrip()

    lambda_resource = _block(
        spec.lambda_function,
        f'''
        data "archive_file" "lambda" {{
          type        = "zip"
          source_file = "${{path.module}}/lambda/handler.py"
          output_path = "${{path.module}}/lambda/function.zip"
        }}

        resource "aws_lambda_function" "processor" {{
          filename         = data.archive_file.lambda.output_path
          function_name    = "${{var.name_prefix}}-processor"
          role             = aws_iam_role.lambda.arn
          handler          = "handler.handler"
          runtime          = "python3.11"
          memory_size      = {spec.lambda_memory_mb}
          timeout          = {spec.lambda_timeout_seconds}
          source_code_hash = data.archive_file.lambda.output_base64sha256
          {environment}
          tags = local.common_tags
        }}
        ''',
    )
    if lambda_resource:
        resources.append(lambda_resource)
        outputs.append(
            'output "lambda_name" {\n  value = aws_lambda_function.processor.function_name\n}'
        )

    dynamodb = _block(
        spec.dynamodb_table,
        '''
        resource "aws_dynamodb_table" "records" {
          name         = "${var.name_prefix}-records"
          billing_mode = "PAY_PER_REQUEST"
          hash_key     = "id"

          attribute {
            name = "id"
            type = "S"
          }

          point_in_time_recovery {
            enabled = true
          }

          server_side_encryption {
            enabled = true
          }

          tags = local.common_tags
        }
        ''',
    )
    if dynamodb:
        resources.append(dynamodb)
        outputs.append(
            'output "table_name" {\n  value = aws_dynamodb_table.records.name\n}'
        )

    notification = _block(
        spec.s3_trigger,
        '''
        resource "aws_lambda_permission" "allow_s3" {
          statement_id  = "AllowS3Invoke"
          action        = "lambda:InvokeFunction"
          function_name = aws_lambda_function.processor.function_name
          principal     = "s3.amazonaws.com"
          source_arn    = aws_s3_bucket.uploads.arn
        }

        resource "aws_s3_bucket_notification" "uploads" {
          bucket = aws_s3_bucket.uploads.id

          lambda_function {
            lambda_function_arn = aws_lambda_function.processor.arn
            events              = ["s3:ObjectCreated:*"]
          }

          depends_on = [aws_lambda_permission.allow_s3]
        }
        ''',
    )
    if notification:
        resources.append(notification)

    handler = dedent(
        '''\
        import json


        def handler(event, context):
            records = [
                {
                    "bucket": item.get("s3", {}).get("bucket", {}).get("name"),
                    "key": item.get("s3", {}).get("object", {}).get("key"),
                }
                for item in event.get("Records", [])
            ]
            return {
                "statusCode": 200,
                "body": json.dumps({"processed": records}),
            }
        '''
    )

    return {
        "versions.tf": versions,
        "variables.tf": variables,
        "main.tf": "\n\n".join(resources) + "\n",
        "outputs.tf": "\n\n".join(outputs) + "\n",
        "terraform.tfvars.example": dedent(
            '''\
            use_localstack     = true
            localstack_endpoint = "http://localhost:4566"
            '''
        ),
        "lambda/handler.py": handler,
    }


def generate_terraform(spec: ResourceSpec) -> str:
    files = generate_project(spec)
    return "\n".join(
        files[name]
        for name in ("versions.tf", "variables.tf", "main.tf", "outputs.tf")
    )
