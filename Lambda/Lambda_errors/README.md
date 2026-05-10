# Lambda Error Alert Enrichment

This Lambda receives alert events from Datadog EventBridge, and can also handle CloudWatch alarm payloads. It sends an SNS email notification with the affected Lambda function, account, region, error count, monitor state, Datadog snapshot link, CloudWatch Logs link, and recent log evidence.

## What It Does

- Detects whether the alert source is Datadog or CloudWatch.
- Extracts the Lambda function name, AWS account, region, metric, monitor state, and error count.
- Sends different email text for active alerts and recovered alerts.
- For active alerts, queries the affected Lambda log group:
  - `/aws/lambda/<function_name>`
- Adds recent useful log evidence to the email, including:
  - error lines
  - `INIT_START` runtime line
  - `REPORT` duration
  - billed duration
  - memory size
  - max memory used
- Adds a direct CloudWatch Logs URL to the affected log group.

## Required Configuration

Set one of these Lambda environment variables to the target SNS topic ARN:

```text
sns_topic_arn
```

or:

```text
SNS_TOPIC_ARN
```

The SNS topic must have confirmed email subscriptions.

## Required IAM Permissions

The Lambda execution role needs permission to publish to SNS:

```json
{
  "Effect": "Allow",
  "Action": "sns:Publish",
  "Resource": "<SNS_TOPIC_ARN>"
}
```

It also needs permission to read Lambda CloudWatch logs:

```json
{
  "Effect": "Allow",
  "Action": "logs:FilterLogEvents",
  "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/*"
}
```

## Datadog Notes

For Datadog alerts, the function prefers values from the monitor group, for example:

```text
aws_account:<account_id>,functionname:<function_name>,region:<region>
```

This is important because the EventBridge event region may not always be the same as the region of the Lambda function that triggered the alert.

The log lookup window uses Datadog's alert window:

```text
from_js_ts -> to_js_ts
```

The function adds 5 minutes after the end of the window to catch delayed CloudWatch log delivery.

## CloudWatch Notes

For CloudWatch alarms, the function extracts details from the alarm payload and builds a CloudWatch alarm URL. Log lookup uses a smaller window around the alarm state change time.

## Testing Checklist

After deploying, trigger a Datadog test notification and confirm:

- The Lambda runs without errors.
- SNS publishes successfully.
- The email includes:
  - function name
  - account
  - region
  - error count
  - monitor state
  - Datadog snapshot URL
  - CloudWatch Logs URL
  - recent Lambda log evidence
- The CloudWatch Logs URL opens the expected log group.

## Main File

The Lambda handler is implemented in:

```text
lambda-errors-test.py
```
