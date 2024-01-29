import boto3
import json
import ipaddress
import botocore

with open('launch_inctances_conf.json', 'r') as args:
    config = json.load(args)

access_key = config["access_key"]
secret_access_key = config["secret_access_key"]
region = config["region"]

session = boto3.Session(aws_access_key_id=access_key, 
                        aws_secret_access_key=secret_access_key, 
                        region_name=region)
ec2 = session.client('ec2')


def launch_new_Instance(config):
    starting_ipv4_address = ipaddress.IPv4Address(config["StartingIPv4Address"])
    num_instances = len(config["name_list"])
    try:
        for instance in range(num_instances):
            ipv4 = str(starting_ipv4_address + instance)
            args = {
                "ImageId": config["ImageId"],
                "InstanceType": config["InstanceType"],
                "MinCount": int(config["MinCount"]),
                "MaxCount": int(config["MaxCount"]),
                "SecurityGroupIds": config["SecurityGroupIds"],
                "SubnetId": config["SubnetId"],
                "UserData": config["UserData"],
                "TagSpecifications": [
                    {
                        "ResourceType": "instance",
                        "Tags": [
                            {
                                "Key": "Name",
                                "Value": config["name_list"][instance]
                            }
                        ]
                    }
                ],
                "PrivateIpAddress": ipv4
            }
            response = ec2.run_instances(**args)
            instance_id = response['Instances'][0]['InstanceId']
            print(f"Instance {instance+1} created with IPv4 address {ipv4}: {instance_id}")
    
    except botocore.exceptions.ClientError as error:
       print(error)
    except botocore.exceptions.ParamValidationError as error:
       print(ValueError('The parameters you provided are incorrect: {}'.format(error)))
    except [TypeError,SyntaxError,ValueError] as error:
        print(error)   




launch_new_Instance(config)