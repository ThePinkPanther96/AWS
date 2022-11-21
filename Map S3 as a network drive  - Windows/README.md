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
5. Clear the text editor and paste the content of "s3_iam_user_permissions.json" After editing the file according to your configuration layout (see instructions in the JSON file).
6. Click on "Review policy" and you are done with the group for now. 

### Create IAM user
1. Navigate to IAM > Users > Add users 
2. Name the new user (The same name that will be given to the network drive).
3. Under "Select AWS credentials type" select "Access key" and then click "Next".
4. Select "Add user to group" > select the group that you created previously > click "Next".
5. Under "Key" write "Name" and under Value Write the name of the new IAM user > click "Next".
6. Review the user settings and click "Create user".
  
  #### NOTE! Make sure to save the user's "Access key ID" and "Secret access key". you will need them later.




