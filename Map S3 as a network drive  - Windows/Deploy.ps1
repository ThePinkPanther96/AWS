<#
.SYNOPSIS
This script automates the setup of an AWS S3 mapping to a Windows Network Drive using Rclone.
It includes functions to download necessary files from an S3 bucket, install required software,
and create a scheduled task to run a PowerShell script at logon.

.NOTES
File Name      : Mount.ps1
Prerequisite   : PowerShell, AWS Tools for PowerShell
Dependencies   : AWSPowerShell
Copyright 2024 - Gal Rozman


.FUNCTIONALITY

function Get-Files {

    .SYNOPSIS
    Downloads files from an AWS S3 bucket to specified target paths.

    .DESCRIPTION
    The Get-Files function downloads files from an AWS S3 bucket and checks their existence at the target paths.
    If the files already exist, it prints a message; otherwise, it downloads and verifies their deployment.
    This function for deploying the needed object from a S3 Bucket.

    .PARAMETER TargetPaths
    An array of the full target path including the objects names, where the files should be deployed.
    It is important to specify the full target path including the precise name of the object as it appears in the deployment bucket.
    
    .PARAMETER SecretKey
    The AWS IAM User Secret Acsses key.

    .PARAMETER Key
    The AWS IAM User Acsses key.

    .PARAMETER BucketName
    The name of the AWS S3 bucket.
}

function Install-Software {

    .SYNOPSIS
    Installs software using the Windows Installer (msiexec.exe) and checks for successful installation.
    This is applicable only for MSI installations.
    
    .DESCRIPTION
    The Install-Software function installs a specified software using msiexec.exe.
    It checks if the software is already installed; if not, it attempts installation.
    It retries the installation on failure and reports the outcome. 
    In this case, the software to install is WinFsp.

    .PARAMETER Software
    The name of the software to be installed.
    Only the software name itself is required; the full name of the software is not needed. 
    For example, if the software name is 'winfsp-2.0.23075.msi,' only the 'WinFsp' part is needed. 
    This precision ensures the code's accuracy.

    .PARAMETER TargetPath
    The target directory where the software installer is located.
    In this case the objects will be deployed to "C:\Rclone" 
    WinFsp will be deployed to "C:\Windows\Temp"
}

function Set-Task {

    .SYNOPSIS
    Creates a scheduled task to run a PowerShell script at logon.

    .DESCRIPTION
    The Set-Task function configures a scheduled task named 'Rclone' to run a specified PowerShell script at logon.

    .PARAMETER TaskName
    The name of the scheduled task.

    .PARAMETER Description
    The description of the scheduled task.

    .PARAMETER Arguments
    The arguments to be passed to the PowerShell script. 

    .PARAMETER User
    The user account under which the task will run.

}

.EXAMPLE
$TargetPaths is a list of the deployment destinations on the local machine. 
To deploy correctly, you must specify the path for deployment, 
as well as the precise names of the objects as they are named in the deployment S3 Bucket
See example:

$TargetPaths = @("C:\Rclone\Rclone\rclone.conf", "C:\Rclone\Rclone\rclone.exe", 
"C:\Windows\Temp\winfsp-2.0.23075.msi", "C:\Rclone\Mount.ps1")

Example for executing the script:

if ($MyInvocation.CommandOrigin -eq 'Runspace'){

    Get-Files -TargetPaths $TargetPaths `
        -BucketNmae "testbucket" `
        -Key "hvhgHG787JF%67g$^" `
        -SecretKey "&^6$%$#^&V%^$c%4^5C8&b87^O7V" `
    
    Install-Software -Software "winfsp" -TargetPath "C:\Windows\Temp\"
    
    Set-Task -TaskName Rclone deployment `
        -Description Deploy Rclone s3 bucket to win drive. `
        -Arguments "-WindowStyle hidden -file C:\Rclone\Mount.ps1" `
        -User SYSTEM
}
#>

function Get-Files {
    param (
        [string[]]$TargetPaths,
        [string]$SecretKey,
        [string]$Key,
        [string]$BucketName
    )
    foreach ($Path in $TargetPaths) {
        if (Test-Path -Path $Path) {
            Write-Host "$Path Already Exists!" -ForegroundColor "Gray"
        }
        else {
            Import-Module -Name AWSPowerShell
            $credentials = New-Object Amazon.Runtime.BasicAWSCredentials -ArgumentList $Key, $SecretKey
            $Object = [System.IO.Path]::GetFileName($Path)
            Write-Host "Downloading files to $Path ..." -ForegroundColor "Yellow"
            Read-S3Object -BucketName $BucketName -Key $Object -File $Path -Credential $credentials
            if (Test-Path -Path $TargetPaths) {
                Write-Host "$Object deployed successfully" -ForegroundColor "Green"
            }
            else {
                Write-Host "$Object was not deployed!" -ForegroundColor "Red"
            }
        }
    }
}

function Install-Software {
    param (
        [string]$Software,
        [string]$TargetPath
    )
    $Object = Get-ChildItem -Path $TargetPath -Filter "*$Software*" | Select-Object -ExpandProperty FullName
    if(-not(Get-WmiObject -Class Win32_Product | Where-Object {$_.Name -like "*$Software*"})){
        try {
            Write-Host "Starting $Software installation... " -ForegroundColor "Yellow"
            Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$Object`" /qn" -Wait
        }
        catch [System.SystemException] {
            Write-Host "An error occurred while attempting to install
            $($Software): $_" -ForegroundColor "Red"
        }
        finally {
          if (Get-WmiObject -Class Win32_Product | Where-Object {$_.Name -like "*$Software*"}){
               Write-Host "$Software Installed Successfully" -ForegroundColor "Green"
            }
            else {
                Write-Host "$Software Could not install! Attempting to install again..." -ForegroundColor "Red"
                Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$Object`" /qn" -Wait
                if (Get-WmiObject -Class Win32_Product | Where-Object {$_.Name -like "*$Software*"}){
                    Write-Host "$Software was installed successfully on the second attempt." -ForegroundColor "Green"
                    else {
                        Write-Host "$Software Could not install after the second attempt!" -ForegroundColor "Red"
                        return;
                    }
                }
            }  
        }
    }
    else {
        Write-Host "$Software already installed"
    }
}

function Set-Task {
    param (
        [string]$global:TaskName = "Rclone",
        [string]$global:Description = "Map AWS S3 to Windows Network Drive",
        [string]$global:Arguments = "-WindowStyle hidden -file C:\Rclone\Mount.ps1",
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


$TargetPaths = @("C:\Rclone\Rclone\rclone.conf", "C:\Rclone\Rclone\rclone.exe", 
"C:\Windows\Temp\winfsp-2.0.23075.msi", "C:\Rclone\Mount.ps1")

if ($MyInvocation.CommandOrigin -eq 'Runspace'){

    Get-Files -TargetPaths $TargetPaths `
        -BucketNmae "BUCKET NAME" `
        -Key "KEY" `
        -SecretKey "SECRET KEY" `
    
    Install-Software -Software "winfsp" -TargetPath "C:\Windows\Temp\"
    
    Set-Task -TaskName $TaskName `
        -Description $Description `
        -Arguments $Arguments `
        -User $User
}