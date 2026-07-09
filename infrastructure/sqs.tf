resource "aws_sqs_queue" "csv_pipeline_dlq" {
  name                      = "csv-pipeline-dlq"
  message_retention_seconds = 1209600  # 14 days (SQS max)
}