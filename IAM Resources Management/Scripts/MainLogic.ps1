$scriptDirectory = Split-Path $MyInvocation.MyCommand.Path
Set-Location $scriptDirectory

Import-Module -name AWSPowerShell

Import-Module -Name "$scriptDirectory\Utility.ps1"
Import-Module -Name "$scriptDirectory\Database.ps1"


function ConnectSession {
  param(
    [Parameter(Mandatory)][string]$key,
    [Parameter(Mandatory)][string]$SKey,
    [Parameter(Mandatory)][string]$region
  )
  try {
    Import-Module -name AWSPowerShell
    Initialize-AWSDefaults -AccessKey $key -SecretKey $SKey -Region $region  # -Scope Global
  }
  catch {
    Write-Log -Function "ConnectSession" -Level "ERROR" -Message "$_"
  }  
}

# temp

function StopSession {
  try {
    Clear-AWSCredential
    Remove-Module -name AWSPowerShell
  }
  catch {
    Write-Log -Function "StopSession" -Level "ERROR" -Message "$_"
  }
}

function CreateIAMUser {
  param (
    [Parameter(Mandatory)][string]$Username,
    [string]$Key,
    [string]$Value,
    [string]$Table,
    [string]$Database
  )
  if ($key -and $Value) {
    try {
      New-IAMUser -UserName $Username -Tag @{Key=$Key;Value=$Value}
      StoreNewUser -Username $Username -Key $Key -Value $Value -Table $Table -Database $Database
    }
    catch { Write-Log -Function "CreateIAMUser" -Level "ERROR" `
      -Message "COULD NOT CREATE USER WITH KEY\VALUE: $_" 
      return
    }
  }
  else {
    try {
      New-IAMUser -UserName $Username
      StoreNewUser -Username $Username -Table $Table -Database $Database
    }
    catch { Write-Log -Function "CreateIAMUser" -Level "ERROR" `
      -Message "COULD NOT CREATE USER WITH ONLY USERNAME: $_" 
      return
    }
  }
}

function GrantConsoleAccess {
  param (
    [string]$Username,
    [string]$Password
  )
  try {
    New-IAMLoginProfile -UserName $Username `
      -PasswordResetRequired $true `
      -Password $Password }
  catch {
    Write-Log -Function "GrantConsoleAccess" -Level "ERROR" -Message "$_"
  }  
}

function GenerateAccessKeys {
  param (
    [string]$Username,
    [string]$Table,
    [string]$Database
  )
  try {
    $newKeys = New-IAMAccessKey -UserName $Username
    StoreAccessKeys -AccessKey "$($newKeys.AccessKeyId)" -SecretKey "$($newKeys.SecretAccessKey)" `
      -Username $Username -Table $Table ` # temp
      -Database $Database # temp 
  }
  catch {
    Write-Log -Function "GenerateAccessKeys" -Level "ERROR" -Message "$_"
  }
}


# Buggy - not finished
function DeleteIAMUser {
  param (
    [Parameter(Mandatory)][string]$Username,
    [string]$Database = "C:\Git\AWS\IAM Resources Management\Data\User_Credentials.SQLite", #temp
    [string]$Table = "USER_CREDENTIALS", #temp
    [string]$PrimaryKeyName = "Username", #temp
    [string]$ValueToGet  = "Secret_Key"
  )
  if (Get-IAMAccessKey -UserName $Username) {
    try {
      $Access_Key = $(GetValueByPrimaryKey -Database $Database -PrimaryKeyName $PrimaryKeyName -PrimaryKeyValue $Username -Table $Table -ValueToGet $ValueToGet)
      Remove-IAMAccessKey -UserName $Username -AccessKeyId $Access_key -Force
      Remove-IAMUser -UserName $Username -Force
      DeleteRowByPrimaryKey -Database $Database -PrimaryKeyName $PrimaryKeyName -PrimaryKeyValue $Username -Table $Table
    }
    catch { Write-Log -Function "DeleteIAMUser" -Level "ERROR" -Message "COULD NOT DELETE ACCESS KEYS: $_" }
  }
  else {
    try { 
      Remove-IAMUser -UserName $Username -Force
      DeleteRowByPrimaryKey -Database $Database -PrimaryKeyName $PrimaryKeyName -PrimaryKeyValue $Username -Table $Table  
    }
    catch { Write-Log -Function "DeleteIAMUser" -Level "ERROR" -Message "COULD NOT DELETE IAM USER: $_" }
  }
}


function CreateIAMGroup {

    
}

function DeleteIAMGroup {

    
}

function AttachIAMUserToGroup {

}


function ExportIAMUserKeys {
    
}


function AttachIAMPoliciesToGroup {

}


function CreateIAMPolicies {
    # (???)
}

function CreatInctance {

}


function deleteInstance {
  
}

function CreateS3Bucket {
  
}

function DeleteS3Bucket {
  
}


