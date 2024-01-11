
if (Test-Path -Path "C:\Rclone\Rclone") {

    Write-Host "S3 Mount already exists!" -BackgroundColor "Red" -ForegroundColor "DarkRed"
}

else { ## Transfering Data from AWS S3 to the target path.

    New-Item -ItemType Directory -Path C:\Rclone\Rclone 
    # Enter the AWS S3 URL for deploying configuration and installation files.
    # Replace "<S3 URL>" with the file path URLs from your deployment S3 Bucket.
    # This script retrieves the Rclone start script, installation executable, and config file from the S3 bucket to the target machine.

    
    Invoke-WebRequest -Uri https://<S3 URL>.amazonaws.com/rclone/rclone.ps1 -OutFile "C:\Rclone\Rclone.ps1" # starting file
    
    Invoke-WebRequest -Uri https://<S3 URL>.amazonaws.com/rclone/rclone/rclone.exe -OutFile "C:\Rclone\Rclone\rclone.exe" # Installation exe
   
    Invoke-WebRequest -Uri https://<S3 URL>.amazonaws.com/rclone/rclone/rclone.conf -OutFile "C:\Rclone\Rclone\rclone.conf" # Costume configuration file 

    Write-Host "Configuration Files had been deployed!" -ForegroundColor "Yellow" -BackgroundColor "DarkGreen"
}
    if (!(Test-Path -Path"C:\Program Files (x86)\WinFsp")) {

        # Provide the AWS S3 URL for deploying and installing the WinFsp MSI.
        # Replace <S3 URL> with your actual deployment S3 URL.
        ## Transferring and installing Winfsp.msi on the target system.

        Invoke-WebRequest -Uri https://<S3 URL>.amazonaws.com/winfsp-1.10.22006.msi -OutFile "C:\Windows\Temp\winfsp-1.10.22006.msi"

        ## Installing WinFsp setup. 
        $MSIInstaller = "C:\Windows\Temp\winfsp-1.10.22006.msi"
        $ArgumentList = "/I $MSIInstaller /qn"

        Start-Process "msiexec.exe" -ArgumentList $ArgumentList -Wait

        Write-Host "WinFsp has been installed!" -ForegroundColor "Yellow" -BackgroundColor "DarkGreen"
    }

    else {
        
        Write-Host "WinFsp already installed!" -BackgroundColor "Red" -ForegroundColor "DarkRed"
    }

if (Get-ScheduledTaskInfo -TaskName "Rclone") {

    Write-Host "Task alredy exists!" -BackgroundColor "Red" -ForegroundColor "DarkRed"
    
    break
}

else {
    
    ## The name & Description of the scheduled task.
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
    
    ##Set vadditional settings.
    Set-ScheduledTask -TaskName $TaskName -Principal $TaskPrincipal -Settings $TaskSettings
    
    Write-Host "Task Installed!" -ForegroundColor "Yellow" -BackgroundColor "DarkGreen"

}
