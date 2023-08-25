# Map S3 Bucket to a network shared drive on Windows
## Introduction
In this tutorial, I will guide you through the process of transforming a regular AWS S3 Bucket into a functional shared network drive on your Windows endpoint. By utilizing a few open-source tools and a straightforward PowerShell script, you can easily and affordably establish a solution for storing and sharing extensive data across multiple endpoints. This approach eliminates the necessity of consistently monitoring disk space and expanding storage capacity. Since it relies on the foundation of an S3 Bucket, the storage is elastic, dynamically scaling to meet demand without requiring initial provisioning.

I first came across this remarkable open-source solution when I was assigned the task of conceptualizing and implementing a strategy for storing a substantial volume of system logs for our QA team in my role. So, let's begin this journey!


## Requirements
- An active AWS account with administrative privileges.
- Windows 10 based endpoint.
- Basic understanding of PowerShell.
- Basic understanding of JSON.


## AWS side
In this section, we will configure a new S3 Bucket with the correct permissions, an IAM user, and an IAM group that will be used to interact with the bucket. 

### Create an IAM group
1. Login to the AWS admin console.
3. Navigate to IAM > User groups > Create group (I named my group "s3fs-windows" so it will be easily recognizable).
4. Navigate to the newly created IAM group > Permissions > Add permissions > Create inline policy > JSON
5. Clear the text editor and paste the content of "s3_iam_user_permissions.json" After editing the file according to your configuration layout (see instructions in the JSON file).
6. Click on "Review policy" and you are done with the group for now. 

### Create an IAM user
1. Navigate to IAM > Users > Add users 
2. Name the new user (The same name that will be given to the network drive).
3. Under "Select AWS credentials type" select "Access key" and then click "Next".
4. Select "Add user to group" > select the group that you created previously > click "Next".
5. Under "Key" write "Name" and under Value Write the name of the new IAM user > click "Next".
6. Review the user settings and click "Create user".
  
  #### NOTE! Make sure to save the user's "Access key ID" and "Secret access key". you will need them later.


### Create S3 Bucket
In this part, we will make the S3 Bucket and pair it with the group and user that we made previously.

1. Navigate to "S3" > "Create bucket".
2. Give the bucket the same name as the IAM user you've created previously.
3. Make sure that you are at the right AWS Region and that "Block Public Access settings" are set on "Block all public access".
4. Click on "Create bucket".
5. Navigate back to the bucket > Permissions > Bucket policy > Edit
6. In the text editor paste the content of "s3_bucket_permissions.json" After editing the file according to your configuration layout (see instructions in the JSON file). 
7. Click on "Save Changes" and you are done with AWS.


## Client side
Now let's move to the client's side, where the actual "Network Drive" will be mounted. In this case, I'm using a Windows 10 machine.

1. Download and install WinFsp by using the MSI package from this repository, or downloading the latest version from the WinFsp official website or GitHub Repository: https://github.com/winfsp/winfsp/releases/download/v1.10/winfsp-1.10.22006.msi![image](https://user-images.githubusercontent.com/112376660/234830822-6d51374f-ef2b-469a-ac13-cbd64425c6e0.png)
2. Download and install Rclone 64 bit by downloading it from Rclone official website: https://downloads.rclone.org/v1.58.1/rclone-v1.58.1-windows-amd64.zip![image](https://user-images.githubusercontent.com/112376660/234830737-818f171c-ae1b-4be6-8fd5-5158c6f9c397.png)
3. Create a new directory: C:\Rlone\Rclone
4. Navigate to C:\Rlone\Rclone and paste the following from this repository:
  - rclone.conf
  - rclone.exe
5. Edit rclone.conf and complete the following parameters under [BucketName]:
  - access_key_id = 
  - secret_access_key = 
  - region = 


For additional configuration options refer to the official Rclone guide: 	https://rclone.org/s3/#configuration
 6. After completing the configuration process, use the Rclone.ps1 to mount the network drive.
  Alternatively, you can mount the drive and set a drive letter by typing the following command line:
  ```nh
  cmd /c "c:\rclone\rclone\rclone.exe"  mount <DriveName>:/<DriveName>/ <DriveLetter>: --vfs-cache-mode full 
  ```
 ## Creating scheduled task to mount the drive on each system startup
   Use the following PowerShell script to create the task:
   ```nh
   	## The name and description of the scheduled task.
    $TaskName = "Rclone"
    $Description = "Map AWS S3 to Windows Network Drive"
    
    ## Create a new task action
    $TaskAction = New-ScheduledTaskAction `
        -Execute 'powershell.exe' `
        -Argument '-WindowStyle hidden -file C:\Rclone\Rclone.ps1'
    
    ## Create a new trigger (At LogOn)
    $TaskTriger = New-ScheduledTaskTrigger -AtLogOn
    
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $TaskAction `
        -Trigger $TaskTriger `
        -Description $Description `
        -User "System" `
    
    ## Set the task principal's user ID and run level.
    $TaskPrincipal = New-ScheduledTaskPrincipal `
        -UserId "LOCALSERVICE" `
        -LogonType ServiceAccount `
        -RunLevel Highest `
    
    ## Set the task compatibility value to Windows 7
    ## Making sure it runs well on laptops as well.
    $TaskSettings = New-ScheduledTaskSettingsSet -Compatibility Win7 -AllowStartIfOnBatteries:$true
    
    ## Set additional settings.
    Set-ScheduledTask -TaskName $TaskName -Principal $TaskPrincipal -Settings $TaskSettings
   ```

Alternatively, you can edit and use the S3_to_Network_Drive_Deployment_Script.ps1 that I've written, which can automatically:
- Create the local directories.
- Pull and execute the installation files from a different AWS S3 Bucket.
- Mount the drive. 
- Create the task.
Just edit the script according to your specifications. 
Use the comments in the script to help you with the configuration.  


I hope this guide has provided you with all the information you need to get started with my project. 
Please feel free to contact me with any suggestions or questions that you may have. 
Thanks a lot! :smiley: 





