resource "aws_dynamodb_table" "csv_pipeline_table" {
  name         = "csv-pipeline-sales"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "date"
  range_key = "product"

  attribute {
    name = "date"
    type = "S"
  }

  attribute {
    name = "product"
    type = "S"
  }
}