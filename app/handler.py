import csv
import io
import os
import json
from datetime import datetime

import boto3

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")
sns = boto3.client("sns")

TABLE_NAME = os.environ["TABLE_NAME"]
DLQ_QUEUE_URL = os.environ["DLQ_QUEUE_URL"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

REQUIRED_FIELDS = ["date", "product", "amount"]


def validate_row(row):
    for field in REQUIRED_FIELDS:
        if not row.get(field):
            return False, f"Missing required field: {field}"

    try:
        amount = float(row["amount"])
        if amount <= 0:
            return False, f"Amount must be positive, got: {row['amount']}"
    except ValueError:
        return False, f"Amount is not a valid number: {row['amount']}"

    try:
        datetime.strptime(row["date"], "%Y-%m-%d")
    except ValueError:
        return False, f"Date is not in YYYY-MM-DD format: {row['date']}"

    return True, None


def send_to_dlq(row, reason, file_key):
    """Sends a failed row to the dead-letter queue, along with why it failed."""
    message = {
        "source_file": file_key,
        "row": row,
        "reason": reason,
    }
    sqs.send_message(
        QueueUrl=DLQ_QUEUE_URL,
        MessageBody=json.dumps(message),
    )


def write_to_dynamodb(row, file_key):
    """Writes one validated row into the DynamoDB table."""
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(
        Item={
            "date": row["date"],
            "product": row["product"],
            "amount": row["amount"],
            "source_file": file_key,
        }
    )


def publish_summary(file_key, success_count, failure_count):
    """Publishes a summary message to SNS once the file is fully processed."""
    message = (
        f"Processed file: {file_key}\n"
        f"Succeeded: {success_count}\n"
        f"Failed: {failure_count}"
    )
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="CSV pipeline processing summary",
        Message=message,
    )


def lambda_handler(event, context):
    results = []

    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        response = s3.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")

        reader = csv.DictReader(io.StringIO(content))

        success_count = 0
        failure_count = 0

        for row in reader:
            is_valid, reason = validate_row(row)

            if is_valid:
                write_to_dynamodb(row, key)
                success_count += 1
            else:
                send_to_dlq(row, reason, key)
                failure_count += 1

        publish_summary(key, success_count, failure_count)

        results.append({
            "file": key,
            "succeeded": success_count,
            "failed": failure_count,
        })

    return {
        "statusCode": 200,
        "body": json.dumps(results),
    }