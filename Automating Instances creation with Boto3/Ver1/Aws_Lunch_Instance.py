import botocore
from logging import error
import boto3

## PLEASE PAY ATENTION TO THE COMENTS ##
# Varibles
ec2 = boto3.resource('ec2')
baseIP = '' # IP address
listec2 = [''] # List of instnces 
myImageId = '<IAM ID>'

# You can lounch from a template or use user data to set first boot operations.
# NOTE Just remember to enable or disable from main

myLaunchTemplate = {
    'LaunchTemplateId': 'Template ID', # The Template ID number
    'Version': '' # The template version
}

#user_data = '''
            
    ## Some Command lines ##

# '''

# Enter the instance system configuration.
myInstanceType = '' # Instance type
myKeyName = '' # pem Key
mysubnet_id = '' # Subnet ID
myVpcId = '', # VPC ID
myBlockDeviceMappings=[{
    'DeviceName': '/dev/sda1', 
    'Ebs': {
        'DeleteOnTermination': False,
        'VolumeSize': 50,
        'VolumeType': 'gp2',
        'Encrypted': False 
    },
}]

# -- Main --

for e in listec2:
    myPrivateIP = (baseIP + e.replace('instancename', '')) # Set the name of the instance
    try:
        instances = ec2.create_instances(
               #DryRun=True,
               ImageId=myImageId,
               #UserData = user_data,
               LaunchTemplate = myLaunchTemplate,
               MinCount=1,
               MaxCount=1,
               InstanceType=myInstanceType,
               KeyName=myKeyName,
               PrivateIpAddress = myPrivateIP,
               SubnetId = mysubnet_id,
               BlockDeviceMappings = myBlockDeviceMappings,
               #VpcId = '',
               #Tags = {'Name': e},
               SecurityGroupIds = [''], # Security group
        )

        intID = instances[0].instance_id
        tag = ec2.create_tags(
            Resources = [intID],
            Tags = [{
                'Key': 'Name',
                'Value':e ,
            }],
        )
    except botocore.exceptions.ClientError as error:
       # Put your error handling logic here
       print(error)
    except botocore.exceptions.ParamValidationError as error:
       print(ValueError('The parameters you provided are incorrect: {}'.format(error)))
      
    #print (myPrivateIP)
