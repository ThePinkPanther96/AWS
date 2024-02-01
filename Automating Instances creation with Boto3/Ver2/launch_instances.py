import boto3
import json
import ipaddress

with open('launch_inctances_conf.json', 'r') as args:
    config = json.load(args)

access_key = config["access_key"]
secret_access_key = config["secret_access_key"]
region = config["region"]

ec2 = boto3.client('ec2', region_name=config["region"], 
                           aws_access_key_id=config["access_key"], 
                           aws_secret_access_key=config["secret_access_key"])

args = {
    "ImageId": config["ImageId"],
    "InstanceType": config["InstanceType"],
    "MinCount": int(config["MinCount"]),
    "MaxCount": int(config["MaxCount"]),
    "SecurityGroupIds": config["SecurityGroupIds"],
    "SubnetId": config["SubnetId"],
    "UserData": config["UserData"],
    "BlockDeviceMappings": config["BlockDeviceMappings"],
    "TagSpecifications": [
        {
            "ResourceType": "instance",
            "Tags": [
                {
                    "Key": "Name",
                    "Value": ""
                }
            ]
        }
    ],
    "PrivateIpAddress": ""
}


def launch_new_instance(config,args):
    starting_ipv4_address = ipaddress.IPv4Address(config["StartingIPv4Address"])
    num_instances = len(config["name_list"])
    try:
        for instance in range(num_instances):
            ipv4 = str(starting_ipv4_address + instance)
            args["TagSpecifications"][0]["Tags"][0]["Value"] = config["name_list"][instance]
            args["PrivateIpAddress"] = ipv4
            response = ec2.run_instances(**args)
            instance_id = response['Instances'][0]['InstanceId']
            print(f"Instance {instance+1} created with IPv4 address {ipv4}: {instance_id}")
    
    except Exception as error:
        print(error)


def launch_instance_from_template():
    pass


def terminate_instance(config,args):
    try:
        for name in config["name_list"]:
            args["TagSpecifications"][0]["Tags"][0]["Value"] = name
            response = ec2.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:Name',
                        'Values': [name]
                    }
                ]
            )
            if response['Reservations']:
                instance_id = response['Reservations'][0]['Instances'][0]['InstanceId']
                instance_state = response['Reservations'][0]['Instances'][0]['State']['Name']
                if instance_state == 'terminated':
                    print(f"{name} has already been terminated")
                else:
                    ec2.terminate_instances(InstanceIds=[instance_id], DryRun=False)
                    print(f"Instance with name {name}, ID: {instance_id} was terminated")
            else:
                print(f"No instance found with name: {name}")

    except Exception as error:
        print(error)



if __name__ == "__main__":
    #launch_new_instance(config, args)
    terminate_instance(config,args)
 
 
 
