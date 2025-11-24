variable "name" {
  type = string
}

variable "kms_key_arn" {
  description = "The ARN of the KMS key to use for CSV export"
  type        = string
}

variable "load_mode" {
  type    = string
  default = "overwrite"
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

variable "table_naming" {
  type    = string
  default = "use_full_filename"

  description = "How to derive a table name from the csv filename. Options are: use_full_filename, split_at_last_underscore"
  validation {
    condition     = contains(["use_full_filename", "split_at_last_underscore"], var.table_naming)
    error_message = "Options are: use_full_filename, split_at_last_underscore"
  }
}

variable "allow_type_conversions" {
  type        = bool
  description = "Allow automatic type conversions in the module"
  default     = false
}