terraform {
  required_providers {
    aws = {
      version = "~> 6.0"
      source  = "hashicorp/aws"
    }
  }
  required_version = "~> 1.0"
}

# provider "aws" {
#   alias  = "bucket-replication"
#   region = var.region_replication
# }