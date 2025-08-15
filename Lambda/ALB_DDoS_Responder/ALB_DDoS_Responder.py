from os import getenv
from urllib.parse import urlparse
from botocore.exceptions import *
import boto3
import logging
import gzip
import io
import re 
import sys
import requests
import ipaddress
import csv


SNS_TOPIC_ARN   = getenv("SNS_TOPIC_ARN")
REGION          = getenv("REGION") 
WAF_SCOPE       = getenv("WAF_SCOPE")
WAF_IPSET_NAME  = getenv("WAF_IPSET_NAME")
WAF_IPSET_ID    = getenv("WAF_IPSET_ID")
ABUSE_API_KEY   = getenv("ABUSE_API_KEY")

SNS_CLIENT      = boto3.client("sns")
s3              = boto3.client('s3', region_name=REGION)
paginator       = s3.get_paginator('list_objects_v2')

NUM_OF_LOGS_TO_PARSE      = int(3)
IP_SCORE_THRESHOLD        = int(49) # in %
ABUSE_SCORE_TO_PRINT      = int(50) # The minimum abuse rate to print in e-mail 

STATUS_CODE_MAX_THRESHOLD = int(499)
STATUS_CODE_MIN_THRESHOLD = int(400)

CLIENT_NAME="TEST CLIENT"


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def lambda_handler(event, context):

    # New
    def _get_root(event, *keys):
        """Return the first non-None of the given top-level keys."""
        for k in keys:
            v = event.get(k)
            if v is not None:
                return v
        return None

    def find_tag(key: str):
        prefix = f"{key}:"
        for t in tags:
            if t.startswith(prefix):
                return t[len(prefix):]
        return None

    logger.info(f"Received event in elb-4xx-errors: {event}")
    
    # top-level fields - New
    # 1. Normalise the two event shapes into one internal model
    source      = event.get("source")
    account     = _get_root(event, "account", "accountId")
    region      = event.get("region")
    detail      = event.get("detail") or event.get("alarmData") or {}
    tags        = detail.get("tags", [])            # Datadog only

    # initialise
    monitor_state = snap = metric_name = None
    loadbalancer  = targetgroup = None
    # monitor_state = None
    snap          = None
    metric_name   = None
    loadbalancer  = None
    targetgroup   = None


    if source and "datadog" in source:
        monitor_state = detail["meta"]["transition"]["trans_name"]
        snap          = detail["meta"]["result"]["metadata"]["snap_url"]
        metric_name   = detail["meta"]["result"]["metadata"]["metric"]
        result        = detail.get("result", {})
        
        # Define extra tags that are not even fields (top-level)
        loadbalancer = find_tag("loadbalancer")
        
        targetgroup  = find_tag("targetgroup")
        
        logger.info(
            f"AWS Account ID: {account}, "
            f"Load Balancer: {loadbalancer}, Target Group: {targetgroup}"
        )

    # Cloudwatch
    elif source == "aws.cloudwatch":
        # shape differs slightly depending on how the rule is configured
        state  = detail.get("state", {})
        monitor_state = state.get("value")
        metric_blocks = detail.get("configuration", {}).get("metrics", [])
        if metric_blocks:
            metric_stat   = metric_blocks[0]["metricStat"]
            metric        = metric_stat["metric"]
            metric_name   = metric.get("name")
            loadbalancer  = metric.get("dimensions", {}).get("LoadBalancer")
            targetgroup   = metric.get("dimensions", {}).get("TargetGroup")

        # prettier link to the alarm
        alarm_name = detail.get("alarmName")
        snap = (
            f"https://{region}.console.aws.amazon.com/cloudwatch/home"
            f"?region={region}#alarmsV2:alarm/{alarm_name}"
        )

    else:
        logger.warning("Unsupported event source %s – skipping.", source)
        return

    logger.info(
        "Parsed → state=%s account=%s lb=%s target=%s metric=%s",
        monitor_state, account, loadbalancer, targetgroup, metric_name
    )

    if monitor_state in ["Recovered", "CLOSED", "OK"]:
        try:
            logger.info(f"Sending recovered notifacation")
            send_recovered_notification(loadbalancer, account, region, targetgroup)
        
        except Exception as err:
            logger.error(f"Unexpected error while while attemoting to send a recovery notifacation: {err}")
    
    # STARTING HERE
    else:
        try:
            send_triggered_notification(
                monitor_state=monitor_state,
                snap=snap,
                account=account,
                region=region,
                loadbalancer=loadbalancer,
                metric=metric_name,
                targetgroup=targetgroup
            )
            result = get_elb_attributes(loadbalancer, account, region)
            
            if not result:
                result = get_elb_attributes(loadbalancer, account, region)
                missing_logs_attributes_notification(loadbalancer, account, region, targetgroup)
                logger.warning("Access logs not enabled; aborting further processing.")
                exit(1)     
            
            else:
                bucket, bucket_prefix, _ = result
                logger.info("ELB attrs → bucket=%s prefix=%s", bucket, bucket_prefix)
            
                # 1) collect
                ips_found, ip_rgx, keys = collect_ips_from_bucket(bucket_prefix, bucket)
                if not ips_found:
                    missing_logs_attributes_notification(loadbalancer, account, region, targetgroup)
                    logger.warning("No log files found under %s/%s; aborting.", bucket, bucket_prefix)
                    return
                
                else:
                    # 2) parse the logs
                    ips_list = sort_latest_logs(ip_rgx, bucket, keys)
                    abuse_results = abuse_scores(ips_list)
                    if not abuse_results:
                        logger.error("abuse_scores function falied. See logs.")
                        return
                    logger.info("Parsed %d unique client IPs", len(ips_list))
                    
                    ips, rates = format_ips(abuse_results)
                    logger.info(f"Filtered %d IPs with score >{ABUSE_SCORE_TO_PRINT}", len(ips))
            
                    high_risk_ips = get_ips_by_score(ips, rates)
                    logger.info("High-risk IP list (>%d%%): %s", IP_SCORE_THRESHOLD, high_risk_ips)

                    # 3) 4/5xx codes summary
                    error_codes = extract_error_codes(keys, bucket)
                    if error_codes is False:
                        logger.error("extract_error_codes function falied. See logs.")
                        return
                    logger.info("4/5xx status codes in logs: %s", error_codes)

                    # 3.5) get target urls
                    target_urls = extract_error_paths(keys, bucket)
                    if target_urls is False:
                        logger.error("extract_error_paths function falied. See logs.")
                        return
                    logger.info("target URLs: %s", target_urls)

                    # log each IP + its rate
                    high_risk = list(zip(ips, rates))
                    for ip, rate in high_risk:
                        logger.info("IP %s → %d%%", ip, rate)

                    # list the ones we're about to block
                    logger.info("IPs to block: %s", high_risk_ips)

                    # 4) update WAF
                    logger.info("Calling update_waf_ip_set with %d addresses", len(high_risk_ips))
                    update_waf_ip_set(high_risk_ips)

                    # 5) sending investigation
                    send_investigation_notification(
                        loadbalancer=loadbalancer,
                        high_risk=high_risk,
                        four_xx_codes=error_codes,
                        target_urls=target_urls
                    )
                
        except Exception as err:
            logger.error(f"Unexpected error while while attemoting to sent the event notifacation: {err}")

    if not (loadbalancer and account):
        logger.error(
            "Missing loadbalancer/account – cannot continue with remediation"
        )
        return
    
    # åbucket, prefix, _ = get_elb_attributes(loadbalancer, account, region)
    
    return {
        "monitor_state": monitor_state,
        "account": account,
        "region": region,
        "loadbalancer": loadbalancer,
        "targetgroup": targetgroup,
        "Result": result
    }


def send_recovered_notification(loadbalancer, account, region, targetgroup):
    
    lb_name = loadbalancer.split('/')[1] if '/' in loadbalancer else loadbalancer
    sub = f"[Recovered]: HTTP Error rate on Load Balancer {lb_name} in account {account}"  
    recovered_message = (
        f"Hello, \n"
        f"\nThis is an automated e-mail from our SRE team."
        f"\nPlease be advised that the HTTP error rate on Load Balancer {lb_name} has returned to normal and the alarm is now recovered.\n"

        f"\nDetails:"
        f"\n----------"
        f"\n • Account: {account}"
        f"\n • Region: {region}"
        f"\n • Target Group: {targetgroup}"
        f"\n • Please let us know if any additional action is required.\n"
        f"\nNo further action is required at this time."
        f"\nIf you have any questions, please let us know.\n"
    )

    signature = f"\nBest Regards," f"\nSRE Team"
    message = recovered_message + signature
    logger.info(f"Subject to be published: {sub}")
    SNS_CLIENT.publish(TopicArn=SNS_TOPIC_ARN, Message=message, Subject=sub)


def send_triggered_notification(monitor_state, snap, account, region, loadbalancer, metric, targetgroup):
    
    lb_name = loadbalancer.split('/')[1] if '/' in loadbalancer else loadbalancer
    sub = f"[{monitor_state}]: HTTP Error Rate on Load Balancer {lb_name} in account {account}"
    alert_message = (
        f"Hello, \n"
        f"\nThis is an automated e-mail from our SRE Team."
        f"\nPlease be advised that our monitoring system has detected that the HTTP Error count is high on Load Balancer {lb_name}."
        f"\nOur automated incident-response system is currently analysing the data and will send a full investigation report shortly.\n"
        
        f"\nDetails:"
        f"\n----------"
        f"\n • Account: {account}"
        f"\n • Target Group: {targetgroup}"
        f"\n • Region: {region}"
        f"\n • Metric type: {metric}"
        f"\n • Event snapshot URL: {snap}\n"
    )
    
    signature = f"\nBest Regards," f"\nSRE Team"
    message = alert_message + signature
    logger.info(f"Subject to be published: {sub}")
    SNS_CLIENT.publish(TopicArn=SNS_TOPIC_ARN, Message=message, Subject=sub)


def missing_logs_attributes_notification(loadbalancer, account, region, targetgroup):

    lb_name = loadbalancer.split('/')[1] if '/' in loadbalancer else loadbalancer
    sub = f"[ACTION REQUIRED] ELB {lb_name} - missing access logs | {account}"

    body = (
        "Hello,\n\n"
        "This is an automated e-mail from the our SRE team.\n"
        f"Our monitoring system has detected that ACCESS LOGS IS DISABLED OR EMPTY on "
        f"Application Load Balancer {lb_name} in AWS account {account}.\n\n"
        "Without ELB access logs we cannot collect request samples or provide detailed incident analysis.\n"
        "Please enable S3 access logging for this ELB as soon as possible. Thank you!\n\n"
        "Details:\n"
        "----------\n"
        f" • Account: {account}\n"
        f" • Region:  {region}\n"
        f" • Target Group: {targetgroup}\n\n"
        "Please let us know if any additional action is required.\n\n"
        "Best regards,\n"
        "SRE Team"
    )
    logger.info("Publishing missing-logs notification")
    SNS_CLIENT.publish(TopicArn=SNS_TOPIC_ARN, Message=body, Subject=sub)


def send_investigation_notification(loadbalancer, high_risk: list[tuple[str,int]], four_xx_codes: list[int], target_urls: list[str]):

    lb_name = loadbalancer.split('/')[1] if '/' in loadbalancer else loadbalancer
    sub = f"[INVESTIGATION READY]: Investigation results for Load Balancer {lb_name} are ready"
    lines = [
        "Hello,",
        "This is an automated e-mail from the our SRE team.",
        "Below is the incident-response investigation summary generated by our automated monitoring system.",
        "",
        "IPs and Abuse Rates found (Blocked in WAF):",
        "----------------------------------------------------------------",
    ]
    # insert one line per IP
    for ip, rate in high_risk:
        lines.append(f"{ip} → {rate}%")

    lines += [
        "",
        "HTTP Error codes found:",
        "----------------------------------------------------------------",
        ", ".join(str(c) for c in four_xx_codes),
        "",
        "Target URL Paths found:",
        "----------------------------------------------------------------"
    ]
    for path in target_urls:
        lines.append(f"{path}")

    lines += [
        "",
        f"If you need additional information or assistance, please contact our on-call engineer by e-mail at {CLIENT_NAME}-info@adomain.com or phone at:"
    ]

    lines += [
        "",
        "Best Regards,",
        "SRE Team"
    ]
    body = "\n".join(lines)
    
    logger.info(f"Subject to be published: {sub}")
    SNS_CLIENT.publish(TopicArn=SNS_TOPIC_ARN, Message=body, Subject=sub)


def get_elb_attributes(loadbalancer, account, region):
    lb_name = loadbalancer.split('/')[1].title()
    elb_client = boto3.client("elbv2", region_name=region)
    try:
        lb_arn = elb_client.describe_load_balancers(Names=[lb_name])["LoadBalancers"][0]["LoadBalancerArn"]
        response = elb_client.describe_load_balancer_attributes(LoadBalancerArn=lb_arn)
    except Exception as e:
        logger.error(f"Error describing load-balancer attributes for {lb_name}: {e}")
        return False

    attrs   = {a["Key"]: a["Value"] for a in response.get("Attributes", [])}
    enabled = attrs.get("access_logs.s3.enabled") == "true"
    if not enabled:
        return False

    bucket = attrs.get("access_logs.s3.bucket")
    bucket_prefix = attrs.get(
        "access_logs.s3.prefix",
        f"AWSLogs/{account}/elasticloadbalancing/{region}/"
    )
    logger.info(f"s3_bucket: {bucket}, prefix: {bucket_prefix}")
    return bucket, bucket_prefix, True
  

def collect_ips_from_bucket(bucket_prefix, bucket):
    
    ip_rgx = re.compile(
        rb'\b(?:25[0-5]|2[0-4]\d|1?\d{1,2})(?:\.(?:25[0-5]|2[0-4]\d|1?\d{1,2})){3}\b'
    )
    
    try:
        keys = [] # Collect every *.log.gz key under the root prefix
        for page in paginator.paginate(Bucket=bucket, Prefix=bucket_prefix):
            for obj in page.get('Contents', []):
                k = obj['Key']
                if k.endswith('.log.gz'):
                    keys.append(k)    
        if not keys:
            logger.warning('No log files found under %s', bucket, bucket_prefix)
            return False, None, None

    except ClientError as e:
        logger.error("S3 client error: %s", e)
        sys.exit(1)

    return True, ip_rgx, keys


def export_logs_to_csv(ip_rgx, keys, bucket, csv_path='elb_logs.csv', num_files=NUM_OF_LOGS_TO_PARSE):
    latest = sorted(keys)[-num_files:]
    with open(csv_path, 'w', newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow(['timestamp', 'client_ip', 'status_code', 'request_path'])
        
        for key in latest:
            body = s3.get_object(Bucket=bucket, Key=key)['Body'].read()
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as gz:
                for raw in gz:
                    if not (m := ip_rgx.search(raw)):
                        continue
                    line = raw.decode('utf-8', errors='ignore')
                    parts = line.split()
                    # parse fields
                    ts        = f"{parts[0]} {parts[1]}"
                    client_ip = m.group(0).decode()
                    status    = parts[8]
                    try: # only 4xx and 5xx
                        code = int(status)
                    except ValueError:
                        continue
                    if not (STATUS_CODE_MIN_THRESHOLD <= code < STATUS_CODE_MAX_THRESHOLD):
                        continue
                    try: # extract path from the quoted request
                        req_line = line.split('"')[1]
                        path     = req_line.split()[1]
                    except (IndexError, ValueError):
                        path = ''
                    writer.writerow([ts, client_ip, code, path])
    return csv_path


def sort_latest_logs(ip_rgx, bucket, keys):
    latest_keys = sorted(keys)[-NUM_OF_LOGS_TO_PARSE:] # 5 is temp
    logger.info('Latest 3 log keys picked: %s', latest_keys)

    ips = set()
    for key in latest_keys:
        logger.info('Processing log file: %s', key)
        try:
            body = s3.get_object(Bucket=bucket, Key=key)['Body'].read()
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as gz:
                for line in gz:
                    m = ip_rgx.search(line)
                    if m:
                        ips.add(m.group(0).decode())
        except ClientError as e:
            logger.error('S3 ClientError on %s: %s', key, e)
            exit(1)
        except gzip.BadGzipFile as e:
            logger.error('BadGzipFile on %s: %s', key, e)
            exit(1)
        except OSError as e:
            logger.error('OSError on %s: %s', key, e)
            exit(1)

    return list(ips)


def extract_error_codes(keys, bucket):
    latest_keys = sorted(keys)[-NUM_OF_LOGS_TO_PARSE:]
    codes = set()

    for key in latest_keys:
        try:
            resp = s3.get_object(Bucket=bucket, Key=key)
            body = resp['Body'].read()
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as gz:
                for raw in gz:
                    try:
                        parts = raw.decode('utf-8').split()
                        status = int(parts[8])  # ELB status code field
                    except (IndexError, ValueError, UnicodeDecodeError) as e:
                        logger.error("Malformed line in %s: %s", key, e)
                        continue

                    if STATUS_CODE_MIN_THRESHOLD <= status < STATUS_CODE_MAX_THRESHOLD:
                        codes.add(status)

        except ClientError as e:
            logger.error("S3 ClientError on %s: %s", key, e)
            return False
        except gzip.BadGzipFile as e:
            logger.error("Invalid gzip in %s: %s", key, e)
            return False
        except OSError as e:
            logger.error("I/O error on %s: %s", key, e)
            return False

    return sorted(codes)


def extract_error_paths(keys, bucket):
    latest = sorted(keys)[-NUM_OF_LOGS_TO_PARSE:]
    paths = set()

    for key in latest:
        try:
            resp = s3.get_object(Bucket=bucket, Key=key)
            with gzip.GzipFile(fileobj=io.BytesIO(resp["Body"].read())) as gz:
                for raw in gz:
                    line = raw.decode("utf-8", errors="ignore")
                    parts = line.split()
                    if len(parts) <= 8:
                        continue
                    try:
                        status = int(parts[8])
                    except ValueError:
                        continue
                    if STATUS_CODE_MIN_THRESHOLD <= status < STATUS_CODE_MAX_THRESHOLD:
                        try:
                            req_line = line.split('"')[1]      # the GET/URL/HTTP chunk
                            url      = req_line.split()[1]     # the URL itself
                        except (IndexError, ValueError):
                            continue

                        parsed = urlparse(url)
                        path = parsed.path 
                        paths.add(path)
        except Exception as e:
            logger.error("Error reading %s: %s", key, e)

    return sorted(paths)


# AbuseIPDB API key
def abuse_score(ip: str) -> int:
    """Return AbuseIPDB confidence score for one public IP (0–100)."""
    try:
        r = requests.get(
            "https://api.abuseipdb.com/api/v2/check",
            headers={"Key": ABUSE_API_KEY, "Accept": "application/json"},
            params={"ipAddress": ip, "maxAgeInDays": 1},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["data"]["abuseConfidenceScore"]
    except requests.exceptions.RequestException as e:
        logger.error("Error fetching abuse score for %s: %s", ip, e)
        return False

 
def abuse_scores(ips):
    results = []
    try:
        for ip in ips:
            if ipaddress.ip_address(ip).is_private:
                continue
            results.append((ip, abuse_score(ip)))
    except Exception as e:
        logger.error(f"ERROR: {e}")
        return False
    
    return results


# Formats by IP and it's Abuse rate
def format_ips(results):
    abuse_rates = []
    ips         = []
    try:
        for ip, score in results:
            if isinstance(score, int) and score > int(ABUSE_SCORE_TO_PRINT):
                ips.append(ip)
                abuse_rates.append(score)
        return ips, abuse_rates
    except Exception as e:
        logger.error(f"ERROR in format_ips: {e}")
        return ips, abuse_rates


# Formats only the IPs that are above the defined threshold
def get_ips_by_score(ip_list, abuse_scores, threshold=IP_SCORE_THRESHOLD): # => threshold
    ips_to_block = []
    for ip, score in zip(ip_list, abuse_scores):
        if score > threshold:
            ips_to_block.append(ip)
    return ips_to_block


def update_waf_ip_set(ips_to_block):
    if not ips_to_block:
        logger.info("No IPs to block, skipping WAF update.")
        return

    if not WAF_IPSET_NAME or not WAF_IPSET_ID:
        logger.warning("WAF_IPSET_NAME or WAF_IPSET_ID not configured. Skipping WAF update.")
        return False # new

    client = boto3.client('wafv2', region_name=REGION)
    # WAF expects /32 for single IPv4 addresses, but we should also handle IPv6 if applicable. Assuming IPv4 for now.
    ip_addresses = [f"{ip}/32" for ip in ips_to_block if ':' not in ip] # Only add IPv4 with /32
    ipv6_addresses = [f"{ip}/128" for ip in ips_to_block if ':' in ip] # Add IPv6 with /128

    if not ip_addresses and not ipv6_addresses:
        logger.info("No valid IPv4 or IPv6 addresses to add to WAF IPSet.")
        return

    all_addresses_for_waf = ip_addresses + ipv6_addresses # Combine both IPv4 and IPv6 addresses
    try:
        response = client.get_ip_set( # Get the current IP set and its lock token.
            Name=WAF_IPSET_NAME,
            Scope=WAF_SCOPE,
            Id=WAF_IPSET_ID
        )
        ip_set = response['IPSet']
        lock_token = response['LockToken']

        existing_addresses = set(ip_set.get('Addresses', [])) # Determine existing IPs to avoid duplicates if WAF doesn't handle them automatically
        new_addresses_to_add = []
        for new_ip_with_cidr in all_addresses_for_waf:
            if new_ip_with_cidr not in existing_addresses:
                new_addresses_to_add.append(new_ip_with_cidr)

        if not new_addresses_to_add:
            logger.info("All IPs to block already exist in WAF IPSet. No update needed.")
            return

        # Append new addresses to existing ones
        updated_addresses = list(existing_addresses.union(new_addresses_to_add))

        update_response = client.update_ip_set( # Update the IP set with the new IP addresses.
            Name=WAF_IPSET_NAME,
            Scope=WAF_SCOPE,
            Id=WAF_IPSET_ID,
            Addresses=updated_addresses,
            LockToken=lock_token
        )
        logger.info(f"WAF IP set {WAF_IPSET_NAME} updated successfully. Added {len(new_addresses_to_add)} new IPs.")
    except client.exceptions.WAFInvalidParameterException as e:
        logger.error(f"WAF Invalid Parameter Exception during update: {e}")
        raise
    except client.exceptions.WAFInternalErrorException as e:
        logger.error(f"WAF Internal Error Exception during update: {e}")
        raise
    except client.exceptions.WAFNonexistentItemException:
        logger.error(f"WAF IPSet '{WAF_IPSET_NAME}' with ID '{WAF_IPSET_ID}' does not exist.")
        raise
    except Exception as e:
        logger.error(f"Error updating WAF IP set {WAF_IPSET_NAME}: {e}")
        raise