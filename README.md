# Event-Driven CSV Pipeline (AWS)

A serverless pipeline that automatically validates and processes CSV files as soon as they're uploaded to S3.

## How it works

1. A `.csv` file is uploaded to S3
2. This triggers a Lambda function, which validates each row (required fields, positive amount, valid date)
3. Valid rows → **DynamoDB**
4. Invalid rows → **SQS** dead-letter queue, with the reason they failed
5. A summary (succeeded/failed counts) is published to **SNS** and emailed out

## Tech stack

- **AWS:** Lambda, S3, DynamoDB, SQS, SNS
- **Infrastructure:** Terraform (remote state in S3)
- **Testing:** pytest + moto
- **CI/CD:** GitHub Actions — tests + `terraform plan` on every push, auto-deploy on merge to `main`

## Running tests

```bash
pip install -r app/requirements-dev.txt
pytest -v
```

## Deploying

```bash
cd infrastructure
terraform init
terraform apply
```

