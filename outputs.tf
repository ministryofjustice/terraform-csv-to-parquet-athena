output "lambda_function_arn" { value = module.csv-to-parquet-export.lambda_function_arn }
output "lambda_function_name" { value = module.csv-to-parquet-export.lambda_function_name }
output "state_machine_arn" { value = aws_sfn_state_machine.csv_to_parquet_export.arn }
output "s3_concept_data_uploads_bucket" { value = module.s3_concept_data_uploads_bucket.bucket.id}
output "s3_concept_data_output_bucket" { value = module.s3_concept_data_output_bucket.bucket.id}