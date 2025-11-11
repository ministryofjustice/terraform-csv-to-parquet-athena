resource "aws_sfn_state_machine" "csv_to_parquet_export" {
  # checkov:skip=CKV_AWS_284: x-ray tracing not required for now
  # checkov:skip=CKV_AWS_285: Logging not required for now. TODO: Add this in the future
  name     = "${var.name}-csv-to-parquet-export" 
  role_arn = aws_iam_role.state_machine.arn

  definition = templatefile("${path.module}/state_machine.asl.json.tpl", {
    lambda_arn = module.csv-to-parquet-export.lambda_function_arn
  })
}
