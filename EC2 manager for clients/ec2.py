import boto3
import json

def start_ec2(names):
    instances_to_start = []
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': names}
        ]
    )

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instances_to_start.append(instance['InstanceId'])

    response = ec2.start_instances(InstanceIds=instances_to_start)
    print(response)


def stop_ec2(names):
    instances_to_stop = []
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': names}
        ]
    )

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instances_to_stop.append(instance['InstanceId'])

    response = ec2.stop_instances(InstanceIds=instances_to_stop)
    print(response)

#------------------------------------------------------------------------------------------

with open('./config.json', 'r') as f:
    config = json.load(f)

access_key = config["access_key"]
secret_access_key = config["secret_access_key"]
region = config["region"]
name_list = config["id_list"]

ec2 = boto3.client('ec2', 
                   aws_access_key_id=access_key, 
                   aws_secret_access_key=secret_access_key, 
                   region_name=region
                   )

#------------------------------------------------------------------------------------------


#start_ec2(name_list)
stop_ec2(name_list)

