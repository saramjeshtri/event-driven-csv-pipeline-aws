import json
import boto3
from moto import mock_aws

from handler import validate_row, lambda_handler

def test_valid_row_passes():
    row = {"date": "2026-07-08", "product": "coffee", "amount": "4.50"}
    is_valid, reason = validate_row(row)
    assert is_valid is True
    assert reason is None


def test_missing_field_fails():
    row = {"date": "2026-07-08", "product": "coffee"}  # amount missing
    is_valid, reason = validate_row(row)
    assert is_valid is False
    assert "Missing required field" in reason


def test_negative_amount_fails():
    row = {"date": "2026-07-08", "product": "coffee", "amount": "-2.00"}
    is_valid, reason = validate_row(row)
    assert is_valid is False
    assert "must be positive" in reason


def test_zero_amount_fails():
    row = {"date": "2026-07-08", "product": "coffee", "amount": "0"}
    is_valid, reason = validate_row(row)
    assert is_valid is False
    assert "must be positive" in reason


def test_non_numeric_amount_fails():
    row = {"date": "2026-07-08", "product": "coffee", "amount": "abc"}
    is_valid, reason = validate_row(row)
    assert is_valid is False
    assert "not a valid number" in reason


def test_invalid_date_format_fails():
    row = {"date": "07-08-2026", "product": "coffee", "amount": "4.50"}
    is_valid, reason = validate_row(row)
    assert is_valid is False
    assert "not in YYYY-MM-DD format" in reason

@mock_aws
def test_lambda_handler_full_flow():
    # 1. Set up fake AWS resources
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-table",
        KeySchema=[
            {"AttributeName": "date", "KeyType": "HASH"},
            {"AttributeName": "product", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "date", "AttributeType": "S"},
            {"AttributeName": "product", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    sqs = boto3.client("sqs", region_name="us-east-1")
    dlq = sqs.create_queue(QueueName="test-dlq")
    dlq_url = dlq["QueueUrl"]

    sns = boto3.client("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="test-topic")
    topic_arn = topic["TopicArn"]

    import handler
    handler.s3 = s3
    handler.dynamodb = dynamodb
    handler.sqs = sqs
    handler.sns = sns
    handler.TABLE_NAME = "test-table"
    handler.DLQ_QUEUE_URL = dlq_url
    handler.SNS_TOPIC_ARN = topic_arn

    csv_content = (
        "date,product,amount\n"
        "2026-07-08,coffee,4.50\n"
        "2026-07-08,bagel,-2.00\n"
    )
    s3.put_object(Bucket="test-bucket", Key="test_sales.csv", Body=csv_content)

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "test_sales.csv"},
                }
            }
        ]
    }

    result = lambda_handler(event, None)

    body = json.loads(result["body"])
    assert body[0]["succeeded"] == 1
    assert body[0]["failed"] == 1

    table = dynamodb.Table("test-table")
    items = table.scan()["Items"]
    assert len(items) == 1
    assert items[0]["product"] == "coffee"

    messages = sqs.receive_message(QueueUrl=dlq_url, MaxNumberOfMessages=5)
    assert len(messages["Messages"]) == 1
    dlq_body = json.loads(messages["Messages"][0]["Body"])
    assert dlq_body["reason"] == "Amount must be positive, got: -2.00"