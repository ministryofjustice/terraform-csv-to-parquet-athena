terraform {
  required_providers {
    aws = {
      version = "~> 6.0"
      source  = "hashicorp/aws"
    }
  }
  required_version = "~> 1.0"
}
provider "aws" {
  region = data.aws_region.current  # e.g., "eu-west-2"
}