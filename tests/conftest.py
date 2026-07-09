import os

os.environ["TABLE_NAME"] = "test-table"
os.environ["DLQ_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/123456789012/test-dlq"
os.environ["SNS_TOPIC_ARN"] = "arn:aws:sns:us-east-1:123456789012:test-topic"