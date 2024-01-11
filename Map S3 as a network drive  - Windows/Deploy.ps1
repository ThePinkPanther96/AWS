function Get-Files {
    param (
        [string[]]$TargetPaths,
        [string]$SecretKey,
        [string]$Key,
        [string]$BucketName = "systemvalidation"
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

    Get-Files -TargetPaths $TargetPaths -S3Objects $S3Objects `
        -BucketNmae $BucketName `
        -Key "AKIAR2QC6VD465F4O4PH" `
        -SecretKey "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" `
    
    Install-Software -Software "winfsp" -TargetPath "C:\Windows\Temp\"
    
    Set-Task -TaskName $TaskName `
        -Description $Description `
        -Arguments $Arguments `
        -User $User
}