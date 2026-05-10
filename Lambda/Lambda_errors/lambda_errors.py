import json
import logging
import os
import re
import time
from datetime import datetime

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)

sns_client = None
logs_clients = {}
topic_arn = os.getenv("sns_topic_arn") or os.getenv("SNS_TOPIC_ARN")

CLIENT_NAME = "TEST-CLIENT"
RECOVERED_STATES = {"Recovered", "CLOSED", "OK"}
MAX_LOG_SCAN_EVENTS = 100
MAX_ERROR_LINES_IN_EMAIL = 5


def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", "N/A")

    if "Records" in event and event["Records"][0].get("EventSource") == "aws:sns":
        event = json.loads(event["Records"][0]["Sns"]["Message"])
        event["source"] = "aws.cloudwatch"

    account = event.get("account") or event.get("AWSAccountId")
    region = get_region(event)
    source = event.get("source")

    if source and "datadog" in source.lower():
        payload = extract_datadog_payload(event, account, region)
    elif source == "aws.cloudwatch":
        payload = extract_cloudwatch_payload(event, account, region)
    else:
        logger.warning("Unsupported event source - skipping | source=%s", source,)
        return

    if payload["monitor_state"] not in RECOVERED_STATES:
        payload["log_evidence"] = get_lambda_log_evidence(payload, request_id)

    if payload["monitor_state"] in RECOVERED_STATES:
        send_recovered_notification(payload)
    else:
        send_notification(payload)

    return payload


def send_notification(payload):
    function_name = payload["function_name"] or "N/A"
    account = payload["account"] or "N/A"
    region = payload["region"] or "N/A"
    error_count = payload["error_count"] if payload["error_count"] is not None else "0"
    monitor_state = payload["monitor_state"] or "N/A"
    metric = payload["metric"] or "N/A"
    snap = payload["snap"] or "N/A"
    log_group_url = get_payload_log_group_url(payload)
    log_evidence = format_log_evidence(payload.get("log_evidence"), log_group_url)

    subject = (
        f"[{payload['monitor_state']}]: Lambda errors detected for "
        f"{function_name}"
    )

    message = (
        "Hello, \n"
        "\nThis is an automated email from the SRE CloudOps team."
        f"\nOur monitoring system has detected an increase in Lambda errors for {function_name} function in account {account}."
        f"\n\n - Function name: {function_name}"
        f"\n - Account: {account}"
        f"\n - Region: {region}"
        f"\n - Error count: {error_count}"
        f"\n - Monitor state: {monitor_state}"
        f"\n - Metric type: {metric}"
        f"\n - Event snapshot URL: {snap}"
        f"\n - CloudWatch Logs URL: {log_group_url}"
        f"{log_evidence}"
        f"\n\nIf you need additional information or assistance, please contact our 24/7 on-call engineers by e-mail at {CLIENT_NAME}-info@domain.com or by phone at:"
        "\n - Israel: +972 (52) 3762048"
        "\n - USA: +1 (201) 7318925"
        "\n\nBest Regards,"
        "\nCloudOps Team"
    )

    return publish_email(message, subject)


def send_recovered_notification(payload):
    function_name = payload["function_name"] or "N/A"
    account = payload["account"] or "N/A"
    region = payload["region"] or "N/A"
    monitor_state = payload["monitor_state"] or "N/A"
    snap = payload["snap"] or "N/A"

    subject = (
        f"[Recovered]: Lambda errors recovered for "
        f"{function_name}"
    )

    message = (
        "Hello, \n"
        "\nThis is an automated email from the SRE CloudOps team."
        f"\nThe Lambda error alert for function {function_name} in account {account} has recovered."
        f"\n\n - Function name: {function_name}"
        f"\n - Account: {account}"
        f"\n - Region: {region}"
        f"\n - Monitor state: {monitor_state}"
        f"\n - Event snapshot URL: {snap}"
        f"\n\nIf you need additional information or assistance, please contact our 24/7 on-call engineers by e-mail at {CLIENT_NAME}-info@domain.com or by phone at:"
        "\n - Israel: +972 (52) 3762048"
        "\n - USA: +1 (201) 7318925"
        "\n\nBest Regards,"
        "\nCloudOps Team"
    )

    return publish_email(message, subject)


def publish_email(message, subject):
    if not topic_arn:
        logger.error("SNS topic ARN is not configured. Set sns_topic_arn or SNS_TOPIC_ARN.")
        return None

    try:
        response = get_sns_client().publish(TopicArn=topic_arn, Message=message, Subject=subject)
        logger.info("SNS message published. message_id=%s", response.get("MessageId"))
        return response
    except Exception:
        logger.exception("Failed to publish SNS notification.")
        return None


def get_sns_client():
    global sns_client

    if sns_client is None:
        sns_client = boto3.client("sns")

    return sns_client


def get_logs_client(region):
    if region not in logs_clients:
        logs_clients[region] = boto3.client("logs", region_name=region)

    return logs_clients[region]


def get_lambda_log_evidence(payload, request_id):
    function_name = normalize_lambda_function_name(payload.get("function_name"))
    region = payload.get("region")

    if not function_name or not region:
        logger.warning(
            "Skipping Lambda log lookup - missing function or region | request_id=%s | function_name=%s | region=%s",
            request_id,
            function_name,
            region,
        )
        return {"status": "skipped", "reason": "missing function name or region"}

    log_group = f"/aws/lambda/{function_name}"
    start_ms, end_ms = get_log_window(payload)

    logger.info(
        "Querying Lambda log group | request_id=%s | log_group=%s | region=%s | start_ms=%s | end_ms=%s",
        request_id,
        log_group,
        region,
        start_ms,
        end_ms,
    )

    try:
        events = fetch_lambda_log_events(region, log_group, start_ms, end_ms)
    except Exception:
        logger.exception(
            "Failed to fetch Lambda log evidence | request_id=%s | log_group=%s | region=%s",
            request_id,
            log_group,
            region,
        )
        return {
            "status": "failed",
            "log_group": log_group,
            "log_group_url": cloudwatch_log_group_url(region, log_group),
            "region": region,
        }

    evidence = summarize_lambda_log_events(events, log_group, region, start_ms, end_ms)

    logger.info(
        "Lambda log evidence collected | request_id=%s | status=%s | events=%s | errors=%s | reports=%s",
        request_id,
        evidence["status"],
        evidence["event_count"],
        len(evidence["error_events"]),
        len(evidence["reports"]),
    )

    return evidence


def get_log_window(payload):
    start_ms = payload.get("log_window_start_ms")
    end_ms = payload.get("log_window_end_ms")

    if start_ms and end_ms:
        return int(start_ms), int(end_ms) + 5 * 60 * 1000

    now_ms = int(time.time() * 1000)
    return now_ms - 60 * 60 * 1000, now_ms


def fetch_lambda_log_events(region, log_group, start_ms, end_ms):
    logs_client = get_logs_client(region)
    filter_pattern = '?ERROR ?Exception ?Traceback ?"Task timed out" ?"Runtime.ExitError" ?REPORT ?INIT_START'
    return fetch_log_events_with_pattern(logs_client, log_group, start_ms, end_ms, filter_pattern)


def fetch_log_events_with_pattern(logs_client, log_group, start_ms, end_ms, filter_pattern=None):
    events = []
    next_token = None

    while len(events) < MAX_LOG_SCAN_EVENTS:
        params = {
            "logGroupName": log_group,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": MAX_LOG_SCAN_EVENTS - len(events),
        }

        if filter_pattern:
            params["filterPattern"] = filter_pattern

        if next_token:
            params["nextToken"] = next_token

        try:
            response = logs_client.filter_log_events(**params)
        except ClientError as err:
            error_code = err.response.get("Error", {}).get("Code")
            if filter_pattern and error_code == "InvalidParameterException":
                logger.warning("CloudWatch Logs filter pattern was rejected; retrying without filter pattern.")
                return fetch_log_events_with_pattern(logs_client, log_group, start_ms, end_ms)
            raise

        events.extend(response.get("events", []))
        next_token = response.get("nextToken")

        if not next_token:
            break

    return events


def normalize_lambda_function_name(function_name):
    if not function_name:
        return function_name

    if function_name.startswith("arn:"):
        function_name = function_name.split(":function:", 1)[-1]

    return function_name.split(":", 1)[0]


def cloudwatch_log_group_url(region, log_group):
    encoded_log_group = log_group.replace("/", "$252F")

    return (
        f"https://{region}.console.aws.amazon.com/cloudwatch/home"
        f"?region={region}#logsV2:log-groups/log-group/{encoded_log_group}"
    )


def get_payload_log_group_url(payload):
    evidence = payload.get("log_evidence") or {}
    if evidence.get("log_group_url"):
        return evidence["log_group_url"]

    function_name = normalize_lambda_function_name(payload.get("function_name"))
    region = payload.get("region")

    if not function_name or not region:
        return "N/A"

    return cloudwatch_log_group_url(region, f"/aws/lambda/{function_name}")


def summarize_lambda_log_events(events, log_group, region, start_ms, end_ms):
    evidence = {
        "status": "ok",
        "log_group": log_group,
        "region": region,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "event_count": len(events),
        "error_events": [],
        "reports": [],
        "runtime_events": [],
    }

    for event in sorted(events, key=lambda item: item.get("timestamp", 0)):
        message = normalize_log_message(event.get("message", ""))

        if "REPORT RequestId:" in message:
            report = parse_report_line(message)
            if report:
                evidence["reports"].append(report)
            continue

        if "INIT_START" in message:
            evidence["runtime_events"].append(trim_log_message(message))
            continue

        evidence["error_events"].append(trim_log_message(message))

    return evidence


def parse_report_line(message):
    report = {"raw": trim_log_message(message)}

    duration_match = re.search(r"Duration:\s*([0-9.]+)\s*ms", message)
    billed_match = re.search(r"Billed Duration:\s*([0-9.]+)\s*ms", message)
    memory_match = re.search(r"Memory Size:\s*([0-9.]+)\s*MB", message)
    max_memory_match = re.search(r"Max Memory Used:\s*([0-9.]+)\s*MB", message)

    if duration_match:
        report["duration_ms"] = duration_match.group(1)
    if billed_match:
        report["billed_duration_ms"] = billed_match.group(1)
    if memory_match:
        report["memory_size_mb"] = memory_match.group(1)
    if max_memory_match:
        report["max_memory_used_mb"] = max_memory_match.group(1)

    return report


def format_log_evidence(evidence, fallback_log_group_url="N/A"):
    if not evidence:
        return ""

    if evidence.get("status") == "skipped":
        return (
            "\n\nRecent Lambda log findings:"
            f"\n - CloudWatch Logs URL: {fallback_log_group_url}"
            f"\n - Log lookup skipped: {evidence.get('reason', 'N/A')}"
        )

    if evidence.get("status") == "failed":
        return (
            "\n\nRecent Lambda log findings:"
            f"\n - Log group: {evidence.get('log_group', 'N/A')}"
            f"\n - Region: {evidence.get('region', 'N/A')}"
            f"\n - CloudWatch Logs URL: {evidence.get('log_group_url') or fallback_log_group_url}"
            "\n - Log lookup failed. Please review the Lambda execution logs directly."
        )

    lines = [
        "\n\nRecent Lambda log findings:",
        f" - Log group: {evidence.get('log_group', 'N/A')}",
        f" - Matching log events: {evidence.get('event_count', 0)}",
    ]

    latest_report = evidence.get("reports", [])[-1] if evidence.get("reports") else None
    if latest_report:
        lines.extend(
            [
                f" - Duration: {latest_report.get('duration_ms', 'N/A')} ms",
                f" - Billed duration: {latest_report.get('billed_duration_ms', 'N/A')} ms",
                f" - Memory size: {latest_report.get('memory_size_mb', 'N/A')} MB",
                f" - Max memory used: {latest_report.get('max_memory_used_mb', 'N/A')} MB",
            ]
        )

    runtime_events = evidence.get("runtime_events", [])
    if runtime_events:
        lines.append(f" - Runtime: {runtime_events[-1]}")

    error_events = evidence.get("error_events", [])
    if error_events:
        lines.append("\nRecent error log lines:")
        for message in error_events[-MAX_ERROR_LINES_IN_EMAIL:]:
            lines.append(f" - {message}")
    else:
        lines.append(" - No error log lines matched in the alert window.")

    return "\n".join(lines)


def normalize_log_message(message):
    return " ".join(message.split())


def trim_log_message(message, max_length=500):
    if len(message) <= max_length:
        return message

    return f"{message[:max_length]}..."


def extract_datadog_payload(event, account, region):
    detail = event.get("detail", {})
    meta = detail.get("meta", {})
    transition = meta.get("transition", {})
    result = meta.get("result", {})
    metadata = result.get("metadata", {})
    tags = detail.get("tags") or []

    monitor_state = transition.get("trans_name")
    snap = metadata.get("snap_url")
    metric = metadata.get("metric")

    monitor = meta.get("monitor", {})
    monitor_text = get_datadog_monitor_text(detail, monitor, metadata)
    parsed_values = parse_datadog_monitor_text(monitor_text)
    group_values = parse_datadog_group(result.get("group"))

    return {
        "source": "datadog",
        "monitor_state": monitor_state,
        "snap": snap,
        "account": group_values.get("aws_account") or account or tag_value(tags, "account") or tag_value(tags, "aws_account") or tag_value(tags, "aws_account_id") or parsed_values.get("account"),
        "region": group_values.get("region") or tag_value(tags, "region") or tag_value(tags, "aws_region") or parsed_values.get("region") or region,
        "function_name": group_values.get("functionname") or get_datadog_function_name(detail, metadata, tags) or parsed_values.get("function_name"),
        "error_count": get_datadog_error_count(detail, result, metadata, monitor_text),
        "metric": metric,
        "monitor": monitor,
        "result": result,
        "log_window_start_ms": metadata.get("from_js_ts"),
        "log_window_end_ms": metadata.get("to_js_ts"),
    }


def extract_cloudwatch_payload(event, account, region):
    trigger = event.get("Trigger", {})
    alarm_name = event.get("AlarmName")
    metric = trigger.get("MetricName")
    event_time_ms = parse_event_time_ms(event.get("StateChangeTime") or event.get("time"))

    snap = (
        f"https://{region}.console.aws.amazon.com/cloudwatch/home"
        f"?region={region}#alarmsV2:alarm/{alarm_name}"
    )

    return {
        "source": "cloudwatch",
        "monitor_state": event.get("NewStateValue"),
        "snap": snap,
        "account": account,
        "region": region,
        "function_name": dimension_value(trigger, "FunctionName") or dimension_value(trigger, "Resource"),
        "error_count": event.get("error_count") or trigger.get("EvaluationPeriods"),
        "metric": metric,
        "monitor": {},
        "result": {},
        "log_window_start_ms": event_time_ms - 15 * 60 * 1000 if event_time_ms else None,
        "log_window_end_ms": event_time_ms + 5 * 60 * 1000 if event_time_ms else None,
    }


def get_region(event):
    if event.get("region"):
        return event.get("region")

    alarm_arn = event.get("AlarmArn", "")
    arn_parts = alarm_arn.split(":")
    if len(arn_parts) > 3:
        return arn_parts[3]

    return None


def parse_event_time_ms(value):
    if not value:
        return None

    try:
        normalized = value.replace("Z", "+00:00")
        return int(datetime.fromisoformat(normalized).timestamp() * 1000)
    except ValueError:
        logger.warning("Could not parse event time: %s", value)
        return None


def get_datadog_function_name(detail, metadata, tags):
    return (
        tag_value(tags, "functionname")
        or tag_value(tags, "function_name")
        or tag_value(tags, "lambda_function")
        or tag_value(tags, "aws_lambda_functionname")
        or detail.get("function_name")
        or metadata.get("function_name")
        or metadata.get("lambda_function")
        or metadata.get("aws_lambda_functionname")
    )


def get_datadog_error_count(detail, result, metadata, monitor_text):
    return (
        detail.get("error_count")
        or result.get("error_count")
        or result.get("count")
        or result.get("value")
        or result.get("last_value")
        or metadata.get("error_count")
        or metadata.get("count")
        or metadata.get("value")
        or error_count_from_text(detail.get("body"))
        or error_count_from_text(detail.get("message"))
        or error_count_from_text(detail.get("title"))
        or metric_value_from_text(monitor_text)
    )


def get_datadog_monitor_text(detail, monitor, metadata):
    values = [
        detail.get("title"),
        detail.get("message"),
        detail.get("body"),
        monitor.get("name"),
        monitor.get("message"),
        metadata.get("title"),
        metadata.get("message"),
    ]

    return "\n".join(str(value) for value in values if value)


def parse_datadog_monitor_text(text):
    if not text:
        return {}

    match = re.search(
        r"Lambda error count on\s+(?P<function_name>.*?)\s+"
        r"in\s+(?P<region>[a-z]{2}-[a-z]+-\d)\s+"
        r"in\s+(?P<account>\d{12})",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return {}

    return {
        "function_name": match.group("function_name").strip(),
        "region": match.group("region").strip(),
        "account": match.group("account").strip(),
    }


def parse_datadog_group(group):
    if not group:
        return {}

    values = {}
    for item in group.split(","):
        if ":" not in item:
            continue

        key, value = item.split(":", 1)
        values[key.strip()] = value.strip()

    return values


def tag_value(tags, key):
    for tag in tags:
        if not isinstance(tag, str) or ":" not in tag:
            continue

        tag_key, value = tag.split(":", 1)
        if tag_key.lower() == key.lower():
            return value

    return None


def dimension_value(trigger, name):
    for dimension in trigger.get("Dimensions", []):
        if not isinstance(dimension, dict):
            continue

        dimension_name = dimension.get("name") or dimension.get("Name")
        dimension_value = dimension.get("value") or dimension.get("Value")
        if dimension_name == name:
            return dimension_value

    return None


def error_count_from_text(text):
    if not text:
        return None

    match = re.search(r"\b(\d+)\s+errors?\b", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def metric_value_from_text(text):
    if not text:
        return None

    match = re.search(r"\bMetric value:\s*([0-9]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE)
    if not match:
        return None

    value = float(match.group(1))
    if value.is_integer():
        return int(value)

    return value
