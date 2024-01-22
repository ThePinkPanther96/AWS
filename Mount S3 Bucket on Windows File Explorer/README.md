# Mout S3 Bucket to Windows File Explorer
## Introduction
In this tutorial, I will guide you through the process of transforming a standard AWS S3 Bucket into a fully functional shared network drive on your Windows endpoint. By leveraging a few open-source tools and a straightforward PowerShell script, you can easily and affordably establish a solution for storing and sharing extensive data across multiple endpoints. This approach eliminates the need for consistently monitoring disk space and expanding storage capacity. Since it relies on the foundation of an S3 Bucket, the storage is elastic, dynamically scaling to meet demand without requiring initial provisioning.

I first encountered this remarkable open-source solution when tasked with conceptualizing and implementing a strategy for storing a substantial volume of system logs for our QA team in my role.


## Requirements
- Active AWS account with administrative privileges.
- Windows 10 client.
- Basic understanding of PowerShell.
- Basic understanding of JSON.
- PowerShell Module on the endpoint: AWSPowerShell


## AWS side
In this section, we will configure a new S3 Bucket with the correct permissions, an IAM user, and an IAM group that will be used to interact with the bucket. 

### Create an IAM group
1. Login to the AWS admin console.
3. Navigate to **IAM > User groups > Create group** (I named my group "s3fs-windows" so it will be easily recognizable).
4. Navigate to the newly created **IAM group > Permissions > Add permissions > Create inline policy > JSON**
5. Clear the text editor and paste the content of [**s3_iam_user_permissions.json**](https://github.com/ThePinkPanther96/AWS/blob/main/Map%20S3%20as%20a%20network%20drive%20%20-%20Windows/s3_iam_user_permissions.json) After editing the file according to your configuration layout (see instructions in the JSON file).
6. Click on **"Review policy"** and you are done with the group for now.

   *NOTE!* If you don't have an existing S3 Bucket, you'll need to enter the desired bucket name beforehand when configuring the group's permissions in the JSON file. 

### Create an IAM user
1. Navigate to **IAM > Users > Add users** 
2. Name the new user (The same name that will be given to the network drive).
3. Select **"Add user to group" > select the group that you created previously > click "Next"**
4. Under **"Key"** write **"Name"** and under Value Write the name of the new **IAM user > click "Next"**
5. Review the user settings and click **"Create user"**
  
   *NOTE!* Make sure to save the user's "Access key ID" and "Secret access key". you will need them later.


### Create S3 Bucket
In this part, we will make the S3 Bucket and pair it with the group and user that we made previously.

1. Navigate to **"S3" > "Create bucket"**
2. Give the bucket the same name as the IAM user you've created previously.
3. Under **"Block Public Access settings for this bucket"** make sure that it is set to **"Block all public access"**
4. Under **"Default Encryption"** make sure that it is set on **"Server-side encryption with Amazon S3 managed keys"**
5. Click on **"Create bucket"**
6. Navigate back to the **bucket > Permissions > Bucket policy > Edit**
7. After editing [**s3_bucket_permissions.json**](https://github.com/ThePinkPanther96/AWS/blob/main/Map%20S3%20as%20a%20network%20drive%20%20-%20Windows/s3_bucket_permissions.json) according to your configuration, paste it in the text editor under **Policy**
8. After editing the file according to your configuration layout (see instructions in the JSON file). 
9. Click on **"Save Changes"** and you are done with AWS.


## Client side
Now let's move to the client's side, where the actual "Network Drive" will be mounted. In this case, I'm using a Windows 10 machine.

1. Download and install the latest version of the WinFsp MSI package from the [WinFsp official website](https://github.com/winfsp/winfsp/releases/download/v2.0/winfsp-2.0.23075.msi), or from the WinFsp [GitHub Repository](https://github.com/winfsp/winfsp/releases/download/v1.10/winfsp-1.10.22006.msi). 
2. Download and install [Rclone 64 bit](https://downloads.rclone.org/v1.65.0/rclone-v1.65.0-windows-amd64.zip) by downloading it from [Rclone official website](https://rclone.org/)
3. Create a new directory: **C:\Rlone\Rclone**
4. Navigate to C:\Rclone\ and paste  [Mount.ps1](https://github.com/ThePinkPanther96/AWS/blob/main/Map%20S3%20as%20a%20network%20drive%20%20-%20Windows/Mount.ps1)
5. Navigate to C:\Rlone\Rclone and paste the following from this repository:
    - rclone.conf
    - rclone.exe
6. Edit rclone.conf and complete the following parameters as well as [BucketName]:
    ```
    [BucketName]
    type = s3
    provider = AWS
    env_auth = false
    access_key_id = 
    secret_access_key = 
    region = 
    ```

    *NOTE!* For additional configuration options refer to the [official Rclone guide](https://rclone.org/s3/#configuration)

7. After completing the configuration process, use the [Mount.ps1](https://github.com/ThePinkPanther96/AWS/blob/main/Map%20S3%20as%20a%20network%20drive%20%20-%20Windows/Mount.ps1) to mount the network drive.
    ```nh
    cmd /c "c:\rclone\rclone\rclone.exe"  mount <DriveName>:/<DriveName>/ <DriveLetter>: --vfs-cache-mode full 
    ```

    *NOTE!* You can create a scheduled task to run [Mount.ps1](https://github.com/ThePinkPanther96/AWS/blob/main/Map%20S3%20as%20a%20network%20drive%20%20-%20Windows/Mount.ps1) at startup. (See example below)
   
## Creating scheduled task to mount the drive on each system startup
   Use the function taken from the deployment script to create a scheduled task: 

```
function Set-Task {
    param (
        [string]$global:TaskName = "Rclone",
        [string]$global:Description = "Map AWS S3 to Windows Network Drive",
        [string]$global:Arguments = "-WindowStyle hidden -file C:\Rlone\Mount.ps1",
        [string]$global:User = "SYSTEM"
    )
    $TaskAction = New-ScheduledTaskAction `
        -Execute 'powershell.exe' `
        -Argument $Arguments `
    
    $TaskTriger = New-ScheduledTaskTrigger -AtLogOn
    
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $TaskAction `
        -Trigger $TaskTriger `
        -Description $Description `
        -User $User `
    
    $TaskPrincipal = New-ScheduledTaskPrincipal `
        -UserId "LOCALSERVICE" `
        -LogonType ServiceAccount `
        -RunLevel Highest `
        
    $TaskSettings = New-ScheduledTaskSettingsSet `
        -Compatibility Win7 `
        -AllowStartIfOnBatteries:$true `
    
    Set-ScheduledTask -TaskName $TaskName `
        -Principal $TaskPrincipal `
        -Settings $TaskSettings `
}
```

Alternatively, you can edit and use the [Deploy.ps1](https://github.com/ThePinkPanther96/AWS/blob/main/Map%20S3%20as%20a%20network%20drive%20%20-%20Windows/Deploy.ps1) that I've written, which can automatically:
- Download data from a S3 Bucket.
- Create the necessary local directories. 
- Create a scheduled task to mount the drive on each system startup.

Just edit the script according to your specifications. 
Use the comments in the script to help you with the configuration.  


I trust this guide equips you with the essential information to commence your project.
Should you have any inquiries or suggestions, please don't hesitate to reach out to me.
Many thanks! 😊



