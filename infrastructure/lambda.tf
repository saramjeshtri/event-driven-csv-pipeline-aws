# Zip the Lambda code automatically on every apply
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../app"
  output_path = "${path.module}/lambda_function.zip"
}

# The Lambda function itself
resource "aws_lambda_function" "csv_processor" {
  function_name = "csv-pipeline-processor"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      TABLE_NAME    = aws_dynamodb_table.csv_pipeline_table.name
      DLQ_QUEUE_URL = aws_sqs_queue.csv_pipeline_dlq.url
      SNS_TOPIC_ARN = aws_sns_topic.csv_pipeline_summary.arn
    }
  }
}

# Let S3 invoke this Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.csv_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.csv_pipeline_uploads.arn
}

# Trigger the Lambda whenever a .csv file is uploaded
resource "aws_s3_bucket_notification" "csv_upload_trigger" {
  bucket = aws_s3_bucket.csv_pipeline_uploads.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.csv_processor.arn
    events               = ["s3:ObjectCreated:*"]
    filter_suffix        = ".csv"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}