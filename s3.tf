module "s3_concept_data_uploads_bucket" {
  source             = "github.com/ministryofjustice/modernisation-platform-terraform-s3-bucket?ref=v9.0.0"
  bucket_prefix      = "${var.name}-data-uploads-${var.environment}-"
  custom_kms_key     = var.kms_key_arn
  versioning_enabled = true

  # to disable ACLs in preference of BucketOwnership controls as per https://aws.amazon.com/blogs/aws/heads-up-amazon-s3-security-changes-are-coming-in-april-of-2023/ set:
  ownership_controls = "BucketOwnerEnforced"

  lifecycle_rule = [
    {
      id      = "main"
      enabled = "Enabled"
      filter  = { prefix = "" }

      tags = {
        rule      = "log"
        autoclean = "true"
      }

      transition = [
        {
          days          = 90
          storage_class = "STANDARD_IA"
          }, {
          days          = 365
          storage_class = "GLACIER"
        }
      ]

      expiration = {
        days = 730
      }

      noncurrent_version_transition = [
        {
          days          = 90
          storage_class = "STANDARD_IA"
          }, {
          days          = 365
          storage_class = "GLACIER"
        }
      ]

      noncurrent_version_expiration = { days = 730 }
    }
  ]

  tags = var.tags
}

module "s3_concept_data_output_bucket" {
  source             = "github.com/ministryofjustice/modernisation-platform-terraform-s3-bucket?ref=v9.0.0"
  bucket_prefix      = "${var.name}-data-output-${var.environment}-"
  custom_kms_key     = var.kms_key_arn
  versioning_enabled = true

  # to disable ACLs in preference of BucketOwnership controls as per https://aws.amazon.com/blogs/aws/heads-up-amazon-s3-security-changes-are-coming-in-april-of-2023/ set:
  ownership_controls = "BucketOwnerEnforced"

  lifecycle_rule = [
    {
      id      = "main"
      enabled = "Enabled"
      filter  = { prefix = "" }

      tags = {
        rule      = "log"
        autoclean = "true"
      }

      transition = [
        {
          days          = 90
          storage_class = "STANDARD_IA"
          }, {
          days          = 365
          storage_class = "GLACIER"
        }
      ]

      expiration = {
        days = 730
      }

      noncurrent_version_transition = [
        {
          days          = 90
          storage_class = "STANDARD_IA"
          }, {
          days          = 365
          storage_class = "GLACIER"
        }
      ]

      noncurrent_version_expiration = { days = 730 }
    }
  ]

  tags = var.tags
}