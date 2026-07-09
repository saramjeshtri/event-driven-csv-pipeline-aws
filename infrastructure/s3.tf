resource "aws_s3_bucket" "csv_pipeline_uploads" {
  bucket = "csv-pipeline-uploads-${data.aws_caller_identity.current.account_id}"
}

data "aws_caller_identity" "current" {}