# Map S3 Bucket to a network shared drive on Windows
## Introduction
In this tutorial, I will instruct you how to convert a regular S3 Bucket on AWS to a functioning shared network drive on your Windows endpoint with a few open-source tools and a relatively simple PowerShell script. this is an inexpensive and easy solution to store and share mass data from multiple endpoints without the need to constantly keep track of the disk and expand storage space. since it is based on S3 Bucket it is also elastic storage, that expands by demand and doesn't need to be 
I first encountered this great open-source solution when I was tasked in my job to think of and execute a solution for storing a great number of system logs by our QA team. So, let's get started!


## Requirements
- An active AWS account with administrative privileges.
- Windows 10/11 based endpint.
- Basic understanding in PowerShell.
- Basic understanding in JSON.

## AWS side
In this section, we will configure a new S3 Bucket with the correct permissions, an IAM user, and an IAM group that will be used to interact with the bucket. 

### Create IAM group
1. Login to AWS admin console.
3. Navigate to IAM > User groups > Create group (I named my group "s3fs-windows" so it will be easally recoznizable).
4. Navigate to the newly created IAM group > Permissions > Add premissions > Create inline policy > JSON
5. Clear the text editor and paste the contant of "s3_bucket_permissions.json" (After editing the file accurding to your configuration layout), or copy the following:
   ```
   {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "1",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::USER_ARN_NUMBER:user/USER_NAME"
            },
            "Action": [
                "s3:ListBucket",
                "s3:DeleteObject",
                "s3:GetObject",
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": [
                "arn:aws:s3:::BUCKET_NAME",
                "arn:aws:s3:::BUCKET_NAME/*"
            ]
        },
        {
            "Sid": "AWSLogDeliveryWrite",
            "Effect": "Allow",
            "Principal": {
                "Service": "delivery.logs.amazonaws.com"
            },
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::BUCKET_NAME/AWSLogs/USER_ARN_NUMBER/*",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "USER_ARN_NUMBER",
                    "s3:x-amz-acl": "bucket-owner-full-control"
                },
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:logs:REGION:USER_ARN_NUMBER:*"
                }
            }
        },
        {
            "Sid": "AWSLogDeliveryAclCheck",
            "Effect": "Allow",
            "Principal": {
                "Service": "delivery.logs.amazonaws.com"
            },
            "Action": "s3:GetBucketAcl",
            "Resource": "arn:aws:s3:::BUCKET_NAME",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "USER_ARN_NUMBER"
                },
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:logs:REGION:USER_ARN_NUMBER:*"
                }
            }
        }
    ]
}
   ```
    

