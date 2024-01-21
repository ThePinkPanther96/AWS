import boto3
import json
from colorama import Fore

with open('./config.json', 'r') as f:
    config = json.load(f)

access_key = config["access_key"]
secret_access_key = config["secret_access_key"]
region = config["region"]
name_list = config["id_list"]

ec2 = boto3.client('ec2', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key, region_name=region)

def ec2_status(names):
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': names}
        ]
    )
    if 'Reservations' in response:
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                state = instance['State']['Name']
                if state == 'running':
                    return True 
    return False


def start_ec2(names) -> list:
    try:
        for name in names:
            response = ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Name', 'Values': [name]}
                ]
            )
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    result = ec2_status([name])

                    if result is False:
                        print(Fore.YELLOW + f"Attempting to start {name}")
                        response = ec2.start_instances(InstanceIds=[instance['InstanceId']])
                        print(Fore.GREEN + f"{name} was started")
                    else:
                        print(Fore.BLUE + f"{name} is already working")
    
    except Exception as err: 
        print(Fore.RED + f"Unexpected {err=}, {type(err)=}")
        raise



def stop_ec2(names) -> list:
    try:
        for name in names:
            response = ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Name', 'Values': [name]}
                ]
            )
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    result = ec2_status([name])
                    
                    if result is True:
                        print(Fore.YELLOW + f"Attempting to stop {name}")
                        response = ec2.stop_instances(InstanceIds=[instance['InstanceId']])
                        print(Fore.GREEN + f"{name} stoped")
                    else:
                        print(Fore.BLUE + f"{name} is already off")
    
    except Exception as err: 
        print(Fore.RED + f"Unexpected {err=}, {type(err)=}")
        raise


#------------------------------------------------------------------------------------------

#start_ec2(name_list)
stop_ec2(name_list)
