## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 6.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_csv-to-parquet-export"></a> [csv-to-parquet-export](#module\_csv-to-parquet-export) | git::https://github.com/terraform-aws-modules/terraform-aws-lambda | a7db1252f2c2048ab9a61254869eea061eae1318 |
| <a name="module_s3_concept_data_output_bucket"></a> [s3\_concept\_data\_output\_bucket](#module\_s3\_concept\_data\_output\_bucket) | github.com/ministryofjustice/modernisation-platform-terraform-s3-bucket | v9.0.0 |
| <a name="module_s3_concept_data_uploads_bucket"></a> [s3\_concept\_data\_uploads\_bucket](#module\_s3\_concept\_data\_uploads\_bucket) | github.com/ministryofjustice/modernisation-platform-terraform-s3-bucket | v9.0.0 |
| <a name="module_upload_checker"></a> [upload\_checker](#module\_upload\_checker) | git::https://github.com/terraform-aws-modules/terraform-aws-lambda | a7db1252f2c2048ab9a61254869eea061eae1318 |

## Resources

| Name | Type |
|------|------|
| [aws_iam_role.state_machine](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy.lambda_kms](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy.sfn_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_lambda_permission.allow_bucket](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_permission) | resource |
| [aws_lambda_permission.allow_sfn_invoke](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_permission) | resource |
| [aws_s3_bucket_notification.csv_uploads](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_notification) | resource |
| [aws_sfn_state_machine.csv_to_parquet_export](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sfn_state_machine) | resource |
| [aws_caller_identity.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity) | data source |
| [aws_iam_policy_document.csv_to_parquet_lambda_function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.lambda_kms](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.sfn_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.upload_checker_lambda_function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_environment"></a> [environment](#input\_environment) | Deployment environment (e.g., dev, test, staging, prod). Used for resource naming, tagging, and conditional settings. | `string` | n/a | yes |
| <a name="input_kms_key_arn"></a> [kms\_key\_arn](#input\_kms\_key\_arn) | The ARN of the KMS key to use for CSV export | `string` | n/a | yes |
| <a name="input_lambda_memory_size"></a> [lambda\_memory\_size](#input\_lambda\_memory\_size) | n/a | `number` | `4096` | no |
| <a name="input_load_mode"></a> [load\_mode](#input\_load\_mode) | n/a | `string` | `"incremental"` | no |
| <a name="input_name"></a> [name](#input\_name) | n/a | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Common tags to be used by all resources | `map(string)` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_lambda_function_arn"></a> [lambda\_function\_arn](#output\_lambda\_function\_arn) | n/a |
| <a name="output_lambda_function_name"></a> [lambda\_function\_name](#output\_lambda\_function\_name) | n/a |
| <a name="output_s3_concept_data_output_bucket"></a> [s3\_concept\_data\_output\_bucket](#output\_s3\_concept\_data\_output\_bucket) | n/a |
| <a name="output_s3_concept_data_uploads_bucket"></a> [s3\_concept\_data\_uploads\_bucket](#output\_s3\_concept\_data\_uploads\_bucket) | n/a |
| <a name="output_state_machine_arn"></a> [state\_machine\_arn](#output\_state\_machine\_arn) | n/a |

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 6.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_csv-to-parquet-export"></a> [csv-to-parquet-export](#module\_csv-to-parquet-export) | git::https://github.com/terraform-aws-modules/terraform-aws-lambda | a7db1252f2c2048ab9a61254869eea061eae1318 |
| <a name="module_s3_concept_data_output_bucket"></a> [s3\_concept\_data\_output\_bucket](#module\_s3\_concept\_data\_output\_bucket) | github.com/ministryofjustice/modernisation-platform-terraform-s3-bucket | v9.0.0 |
| <a name="module_s3_concept_data_uploads_bucket"></a> [s3\_concept\_data\_uploads\_bucket](#module\_s3\_concept\_data\_uploads\_bucket) | github.com/ministryofjustice/modernisation-platform-terraform-s3-bucket | v9.0.0 |
| <a name="module_upload_checker"></a> [upload\_checker](#module\_upload\_checker) | git::https://github.com/terraform-aws-modules/terraform-aws-lambda | a7db1252f2c2048ab9a61254869eea061eae1318 |

## Resources

| Name | Type |
|------|------|
| [aws_iam_role.state_machine](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy.lambda_kms](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy.sfn_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_lambda_permission.allow_bucket](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_permission) | resource |
| [aws_lambda_permission.allow_sfn_invoke](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_permission) | resource |
| [aws_s3_bucket_notification.csv_uploads](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_notification) | resource |
| [aws_sfn_state_machine.csv_to_parquet_export](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sfn_state_machine) | resource |
| [aws_caller_identity.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity) | data source |
| [aws_iam_policy_document.csv_to_parquet_lambda_function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.lambda_kms](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.sfn_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.upload_checker_lambda_function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_allow_type_conversions"></a> [allow\_type\_conversions](#input\_allow\_type\_conversions) | Allow automatic type conversions in the module | `bool` | `false` | no |
| <a name="input_environment"></a> [environment](#input\_environment) | Deployment environment (e.g., dev, test, staging, prod). Used for resource naming, tagging, and conditional settings. | `string` | n/a | yes |
| <a name="input_kms_key_arn"></a> [kms\_key\_arn](#input\_kms\_key\_arn) | The ARN of the KMS key to use for CSV export | `string` | n/a | yes |
| <a name="input_lambda_memory_size"></a> [lambda\_memory\_size](#input\_lambda\_memory\_size) | n/a | `number` | `4096` | no |
| <a name="input_load_mode"></a> [load\_mode](#input\_load\_mode) | n/a | `string` | `"overwrite"` | no |
| <a name="input_name"></a> [name](#input\_name) | n/a | `string` | n/a | yes |
| <a name="input_table_naming"></a> [table\_naming](#input\_table\_naming) | How to derive a table name from the csv filename. Options are: use\_full\_filename, split\_at\_last\_underscore | `string` | `"use_full_filename"` | no |
| <a name="input_tags"></a> [tags](#input\_tags) | Common tags to be used by all resources | `map(string)` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_lambda_function_arn"></a> [lambda\_function\_arn](#output\_lambda\_function\_arn) | n/a |
| <a name="output_lambda_function_name"></a> [lambda\_function\_name](#output\_lambda\_function\_name) | n/a |
| <a name="output_s3_concept_data_output_bucket"></a> [s3\_concept\_data\_output\_bucket](#output\_s3\_concept\_data\_output\_bucket) | n/a |
| <a name="output_s3_concept_data_uploads_bucket"></a> [s3\_concept\_data\_uploads\_bucket](#output\_s3\_concept\_data\_uploads\_bucket) | n/a |
| <a name="output_state_machine_arn"></a> [state\_machine\_arn](#output\_state\_machine\_arn) | n/a |
<!-- END_TF_DOCS -->