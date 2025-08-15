# This version can handle multi-tunnel alerts (Not Composites) - One monitor that moniors two tunnels. 
from os import getenv
import boto3
import logging
import json
from botocore.exceptions import ClientError, BotoCoreError

sns_client = boto3.client("sns")
topic_arn = getenv("sns_topic_arn") #environment variable

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

CLIENT_NAME="TEST CLIENT"

def lambda_handler(event, context):
    logger.info(f"Received event in vpn-dpwn: {event}")
    
    metric_name   = None
    monitor_state = None
    vpn_id        = None
    tunnel_ips    = []
    monitor       = {}
    result        = {}
    
    if "Records" in event and event["Records"][0].get("EventSource") == "aws:sns":
        event = json.loads(event["Records"][0]["Sns"]["Message"])
        event["source"] = "aws.cloudwatch"

    account = event.get("account") or event.get("AWSAccountId")
    region  = event.get("region") or event.get("Region") or event.get("AlarmArn", "").split(":")[3]
    source  = event.get("source")

    if source and 'datadog' in source:
        monitor_state = event["detail"]["meta"]["transition"]["trans_name"]
        snap = event["detail"]["meta"]["result"]["metadata"]["snap_url"]
        tags = event["detail"].get("tags")
        metric = event['detail']['meta']['result']['metadata']['metric']
        
        detail = event.get("detail", {})
        monitor = detail.get("meta", {}).get("monitor", {})
        result = detail.get("result", {})
        
        # extract VPN info if tagged
        tunnel_ips = [t.split(":",1)[1] for t in tags if t.startswith("tunnelipaddress:")]
        vpn_id = next((t.split(":",1)[1] for t in tags if t.startswith("vpnid:")), None)

        logger.info(f"AWS Account ID: {account}, Tunnel IPs: {tunnel_ips}, VPN id: {vpn_id}")

    
    elif source == "aws.cloudwatch":
        monitor_state = event.get("NewStateValue")
        trigger       = event.get("Trigger", {})
        metric_name   = trigger.get("MetricName")
        metric        = metric_name

        dims = {d["name"]: d["value"] for d in trigger.get("Dimensions", [])}
        tunnel_ip = dims.get("TunnelIpAddress")
        if tunnel_ip:
            tunnel_ips = [tunnel_ip]
        vpn_id = dims.get("VpnId") or dims.get("VpnConnectionId")

        region = event.get("AlarmArn", "").split(":")[3]   # eu-central-1

        if vpn_id is None and tunnel_ips:
            ec2 = boto3.client("ec2", region_name=region)
            resp = ec2.describe_vpn_connections()
            for v in resp["VpnConnections"]:
                vpn_ips = [tel.get("OutsideIpAddress") for tel in v.get("VgwTelemetry", [])]
                if any(ip in vpn_ips for ip in tunnel_ips):
                    vpn_id = v["VpnConnectionId"]
                    break

        if len(tunnel_ips) < 2:
            tunnel_ips = get_down_tunnel_ips(region)

        account = event.get("AWSAccountId")

        alarm_name = event.get("AlarmName")
        snap = (
            f"https://{region}.console.aws.amazon.com/cloudwatch/home"
            f"?region={region}#alarmsV2:alarm/{alarm_name}"
        )

    else:
        logger.warning("Unsupported event source %s – skipping.", source)
        return
    
    
    if monitor_state in ["Recovered", "CLOSED", "OK"]:
        try:
            logger.info(f"Sending recovered notifacation")
            send_recovered_notification(tunnel_ips, account, region, vpn_id)
        
        except Exception as err:
            logger.error(f"Unexpected error while while attemoting to send a recovery notifacation: {err}")
    
    else:
        down_ips = [ip for ip in tunnel_ips if is_tunnel_down(ip, region)]
        if down_ips:
            logger.info(f"the tunnel is {is_tunnel_down(tunnel_ips, region)}")
    
            try:
                display_id = open_ticket(
                    down_ips,      # ← pass the list, not a comparison!
                    vpn_id,
                    account,
                    region,
                    message_subject="VPN tunnel(s) DOWN (Automated alert)",
                    body_text=(
                        "Hello,\n\n"
                        "Our automated monitoring system has detected that one or more VPN tunnel(s) are down:\n\n"
                        "Please investigate and resolve this issue promptly.\n\n"
                        f"Best regards,\n{CLIENT_NAME}\n"
                    )
                )
            except Exception as err:
                logger.error(f"Unexpected error while while attemoting to open the Support ticket: {err}")
                display_id = None

            try:
                send_notification(
                    down_ips,
                    monitor_state,
                    snap,
                    account,
                    region,
                    vpn_id,
                    metric,
                    display_id
                )
            except Exception as err:
                logger.error(f"Unexpected error while while attemoting to sent the event notifacation: {err}")        
    
    return {
        "monitor_state": monitor_state,
        "account": account,
        "region": region,
        "tunnel_ips": tunnel_ips,
        "vpn_id": vpn_id,
        "monitor": monitor,
        "Result": result
    }


def send_recovered_notification(tunnel_ips, account, region, vpn_id):

    sub = f"[Recovered]: One or more VPN Tunnel(s) DOWN in {vpn_id}"
    
    recovered_message = (
        "Hello, \n"
        "\nhis is an automated e-mail from SRE Team."
        f"\nPlease be advised that the state of VPN Tunnel(s): {tunnel_ips}, in {vpn_id}, has RECOVERED. \n"
        f"\n • Account: {account}"
        f"\n • Region: {region}\n"
        f"\nIf you need additional information or assistance, please contact our on-call engineer by e-mail at {CLIENT_NAME}-info@domain.com or by phone at:"
        "\nBest Regards,"
        "\nCloudOps Team"
    )
    
    response = sns_client.publish(TopicArn=topic_arn, Message=recovered_message, Subject=sub)
    return response


def send_notification(tunnel_ips, monitor_state, snap, account, region, vpn_id, display_id, metric):

    sub = f"[{monitor_state}]: One or more VPN Tunnel(s) DOWN in {vpn_id}"

    alert_message = (
        "Hello, \n"
        "\nThis is an automated e-mail from SRE Team."
        f"\nPlease be advised that our monitoring system has detected that VPN Tunnel(s) {tunnel_ips} state, in {vpn_id}, is DOWN"
        "\nA ticket to AWS Support was opened on your behalf.\n"
        f"\n • Account: {account}"
        f"\n • Region: {region}"
        f"\n • Metric type: {metric}"
        f"\n • Event snapshot URL: {snap}"
        f"\n • Support case ID: {display_id or 'No Support Case was created.'}\n"
        f"\nIf you need additional information or assistance, please contact our on-call engineer by e-mail at {CLIENT_NAME}-info@domain.com or by phone at:"
    )
    signature = f"\nBest Regards," f"\nCloudOps Team"

    message = alert_message + signature

    logger.info(f"Subject to be published: {sub}")

    # Publishing the message via SNS
    sns_client.publish(TopicArn=topic_arn, Message=message, Subject=sub)


class SupportWrapper:

    def __init__(self, support_client):
        self.support_client = support_client

    @classmethod
    def from_client(cls):

        support_client = boto3.client("support")
        return cls(support_client)

    def create_case(self, description, message_subject):

        try:
            response = self.support_client.create_case(
                subject=message_subject["code"],
                communicationBody=description["code"],
                serviceCode="amazon-virtual-private-network",
                severityCode="high",
                categoryCode="connectivity-issues",
                language="en",
                issueType="technical",
            )
            case_id = response["caseId"]

            describe_response = self.support_client.describe_cases(
                caseIdList=[case_id],
                language="en" 
            )
            display_id = describe_response["cases"][0]["displayId"]

        except ClientError as err:
            if err.response["Error"]["Code"] == "SubscriptionRequiredException":
                logger.error(
                    "This account is not registered to at least one of Business, Enterprise On-Ramp, or Enterprise Support.")
            else:
                logger.error(
                    "Couldn't create case. Here's why: %s: %s",
                    err.response["Error"]["Code"],
                    err.response["Error"]["Message"],
                )
                raise
        else:
            return display_id


def check_down_tunnel(tunnel_ips, vpn_id):
    ec2_client = boto3.client('ec2')
    try:
        # 1. Query only one VPN if we have its ID; otherwise list them all
        if vpn_id:
            response = ec2_client.describe_vpn_connections(VpnConnectionIds=[vpn_id])
        else:
            response = ec2_client.describe_vpn_connections()

        # 2. Search every VPN/tunnel for the requested outside-IP
        for vpn in response["VpnConnections"]:
            for tel in vpn.get("VgwTelemetry", []):
                if tel.get("OutsideIpAddress") == tunnel_ips:
                    return tel.get("Status")   # UP | DOWN | etc.

        return f"Tunnel IP {tunnel_ips} not found in any VPN connection."
    
    except Exception as e:
        return f"Error occurred: {str(e)}"


def get_down_tunnel_ips(region):
    ec2 = boto3.client('ec2', region_name=region) if region else boto3.client('ec2')
    resp = ec2.describe_vpn_connections()
    return [
        t['OutsideIpAddress']
        for v in resp['VpnConnections']
        for t in v.get('VgwTelemetry', [])
        if t['Status'] != 'UP'
    ]


def is_tunnel_down(tunnel_ips, region):
    return tunnel_ips in get_down_tunnel_ips(region)
   

# Used to detect second IP address from CloudWatch
def get_vpn_id_by_tunnel_ip(tunnel_ip: str, region: str) -> str | None:
    ec2 = boto3.client("ec2", region_name=region)
    resp = ec2.describe_vpn_connections()          # ← one call, no paginator
    for vpn in resp["VpnConnections"]:
        for tel in vpn.get("VgwTelemetry", []):
            if tel.get("OutsideIpAddress") == tunnel_ip:
                return vpn["VpnConnectionId"]
    return None


def format_down_tunnels(vpn_id, tunnel_ips, account, region):
    lines = [
        f"Account ID: {account}",
        f"Region:     {region}",
        f"VPN ID:     {vpn_id}",
        "",
        "Down tunnels:",
        "-----------------"
    ]
    for ip in tunnel_ips:
        status = check_down_tunnel(ip, vpn_id)
        lines.append(f"  • {ip}: {status}")

    return "\n".join(lines)


def open_ticket(tunnel_ips, vpn_id, account: str, region: str, message_subject: str, body_text: str | None = None):
    try:
        body_contents = []
        if body_text:
            body_contents.append(body_text.strip())
        body_contents.append(format_down_tunnels(vpn_id, tunnel_ips, account, region))
        message_body = "\n\n".join(body_contents)

        subject   = {"code": message_subject}
        body_dict = {"code": message_body}

        wrapper     = SupportWrapper.from_client()
        display_id  = wrapper.create_case(body_dict, subject)

        logger.info("Opened AWS Support case (Console ID %s)", display_id)
        return display_id

    except ClientError as e:
        logger.error("AWS Support API error: %s - %s",
                     e.response['Error']['Code'],
                     e.response['Error']['Message'])
    except BotoCoreError as e:
        logger.error("BotoCoreError error while opening ticket: %s", e)
    except Exception as err:
        logger.error("Unexpected error while opening ticket: %s", err)