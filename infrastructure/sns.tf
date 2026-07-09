resource "aws_sns_topic" "csv_pipeline_summary" {
  name = "csv-pipeline-summary"
}

resource "aws_sns_topic_subscription" "email_alert" {
  topic_arn = aws_sns_topic.csv_pipeline_summary.arn
  protocol  = "email"
  endpoint  = "saramjeshtri18@gmail.com"
}