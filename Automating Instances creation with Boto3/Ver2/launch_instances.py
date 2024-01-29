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
    starting_ipv4_address = ipaddress.IPv4Address(config["ec2_instance_params"]["StartingIPv4Address"])
    num_instances = len(config["ec2_instance_params"]["name_list"])
    try:
        for instance in range(num_instances):
            ipv4 = str(starting_ipv4_address + instance)
            args = {
                "ImageId": config["ec2_instance_params"]["ImageId"],
                "InstanceType": config["ec2_instance_params"]["InstanceType"],
                "MinCount": int(config["ec2_instance_params"]["MinCount"]),
                "MaxCount": int(config["ec2_instance_params"]["MaxCount"]),
                "SecurityGroupIds": config["ec2_instance_params"]["SecurityGroupIds"],
                "SubnetId": config["ec2_instance_params"]["SubnetId"],
                "UserData": config["ec2_instance_params"]["UserData"],
                "TagSpecifications": [
                    {
                        "ResourceType": "instance",
                        "Tags": [
                            {
                                "Key": "Name",
                                "Value": config["ec2_instance_params"]["name_list"][instance]
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


def launch_instance_from_template():
    pass


def terminate_instance():
    pass


def create_ebs_vol():
    pass


def check_vol():
    pass


if __name__ == "__main__":
    launch_new_Instance(config)

