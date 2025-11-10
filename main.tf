data "aws_iam_policy_document" "csv_to_parquet_lambda_function" {
  statement {
    sid = "S3ReadSourceWriteDest"
    actions = [
      "s3:ListBucket", "s3:GetObject", "s3:GetBucketLocation", "s3:DeleteObject",
      "s3:PutObject", "s3:AbortMultipartUpload", "s3:ListBucketMultipartUploads"
    ]
    resources = [
      "${module.s3_concept_data_uploads_bucket.bucket.arn}",
      "${module.s3_concept_data_uploads_bucket.bucket.arn}/*",
      "${module.s3_concept_data_output_bucket.bucket.arn}",
      "${module.s3_concept_data_output_bucket.bucket.arn}/*",
    ]
  }

  statement {
    sid = "KMSEncryptDecrypt"
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey",
      "kms:ReEncrypt*",
      "kms:DescribeKey",
    ]
    resources = [
      "${module.s3_concept_data_uploads_bucket.bucket.arn}",
      "${module.s3_concept_data_uploads_bucket.bucket.arn}/*",
      "${module.s3_concept_data_output_bucket.bucket.arn}",
      "${module.s3_concept_data_output_bucket.bucket.arn}/*",
    ]
  }

  statement {
    sid = "GlueCatalog"
    actions = [
      "glue:GetDatabase", "glue:CreateDatabase", "glue:BatchCreatePartition",
      "glue:GetTable", "glue:CreateTable", "glue:UpdateTable", "glue:DeleteTable"
    ]
    resources = ["*"]
  }

  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["*"]
  }
}

module "csv-to-parquet-export" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda/commit/a7db1252f2c2048ab9a61254869eea061eae1318"

  function_name   = "${var.name}-csv-to-parquet"
  description     = "Lambda to export data for ${var.name}"
  handler         = "main.handler"
  runtime         = "python3.12"
  memory_size     = 4096
  timeout         = 900
  architectures   = ["x86_64"]
  build_in_docker = false

  attach_policy_json = true
  policy_json        = data.aws_iam_policy_document.csv_to_parquet_lambda_function.json

  environment_variables = {
    GLUE_DATABASE = var.name
    LOAD_MODE     = var.load_mode
  }

  source_path = [{
    path = "${path.module}/lambda-functions/csv-to-parquet-export/"
    commands = [
      "pip3.12 install --platform=manylinux2014_x86_64 --only-binary=:all: --no-compile --target=. -r requirements.txt",
      ":zip",
    ]
  }]

  layers = [
    "arn:aws:lambda:${data.aws_region.current.id}:336392948345:layer:AWSSDKPandas-Python312:18"
  ]

}

data "aws_iam_policy_document" "upload_checker_lambda_function" {
  statement {
    // Allow the lambda to read the upload files from the S3 bucket
    actions = [
      "s3:ListBucket",
      "s3:GetObject"
    ]

    resources = [
      "${module.s3_concept_data_uploads_bucket.bucket.arn}",
      "${module.s3_concept_data_uploads_bucket.bucket.arn}/*",
    ]
  }

  // Allow the lambda to start the state machine
  statement {
    actions = [
      "states:StartExecution"
    ]

    resources = [
      aws_sfn_state_machine.csv_to_parquet_export.arn
    ]
  }
}

module "upload_checker" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda/commit/a7db1252f2c2048ab9a61254869eea061eae1318"

  function_name   = "${var.name}-upload-checker"
  description     = "Lambda to check if a file have been uploaded to the S3 bucket"
  handler         = "main.handler"
  runtime         = "python3.12"
  memory_size     = 1024
  timeout         = 10
  architectures   = ["x86_64"]
  build_in_docker = false

  attach_policy_json = true
  policy_json        = data.aws_iam_policy_document.upload_checker_lambda_function.json

  environment_variables = {
    BACKUP_UPLOADS_BUCKET = module.s3_concept_data_uploads_bucket.bucket.id
    STATE_MACHINE_ARN     = aws_sfn_state_machine.csv_to_parquet_export.id
    OUTPUT_BUCKET         = module.s3_concept_data_output_bucket.bucket.id
    NAME                  = var.name
  }

  source_path = [{
    path = "${path.module}/lambda-functions/upload-checker/main.py"
  }]

  tags = var.tags
}

# Lambda function to check if all files have been uploaded to the S3 bucket
resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = module.upload_checker.lambda_function_arn
  principal     = "s3.amazonaws.com"
  source_arn    = module.s3_concept_data_uploads_bucket.bucket.arn
}

# Bucket Notification to trigger Lambda function
resource "aws_s3_bucket_notification" "csv_uploads" {
  bucket = module.s3_concept_data_uploads_bucket.bucket.id

  lambda_function {
    lambda_function_arn = module.upload_checker.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_bucket]
}
