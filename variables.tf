variable "name" {
  type = string
}

variable "kms_key_arn" {
  description = "The ARN of the KMS key to use for CSV export"
  type        = string
}

variable "load_mode" {
  type    = string
  default = "incremental"
  validation {
    condition     = contains(["incremental", "overwrite"], var.load_mode)
    error_message = "load_mode must be one of: incremental, overwrite"
  }
}

variable "lambda_memory_size" {
  type    = number
  default = 4096
}

variable "tags" {
  type        = map(string)
  description = "Common tags to be used by all resources"
}

variable "environment" {
  type        = string
  description = "Deployment environment (e.g., dev, test, staging, prod). Used for resource naming, tagging, and conditional settings."
}

variable "region_replication" {
  type        = string
  description = "AWS Region code for the replication target."
}
