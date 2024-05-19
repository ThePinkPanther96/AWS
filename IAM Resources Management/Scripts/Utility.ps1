$scriptDirectory = Split-Path $MyInvocation.MyCommand.Path
Set-Location $scriptDirectory

function Write-Log {
  param (
    [string]$Message,
    [string]$Level = "INFO",
    [string]$Function
  )
  $FileTimeStamp = Get-Date -Format "dd-MM-yyyy"
  $ContentTimeStamp =  (Get-Date).toString("dd/MM/yyyy HH:mm:ss")
  $LogFileName = "C:\Git\AWS\IAM Resources Management\Logs\Event_log_$FileTimeStamp.log" # temp
  $LogEntry = "$ContentTimeStamp - [$Level][$Function] - $Message"
  Add-Content -Path $LogFileName -Value $LogEntry
}

# edit
function EncryptString {
  param (
    [securestring]$Password
  )
  $encryptedPassword = $Password | ConvertTo-SecureString -AsPlainText -Force
  $encryptedString = ConvertFrom-SecureString -SecureString $encryptedPassword
  $encryptedString
}

# edit
function DecryptString {
  param (
    [securestring]$Password
  )
  $decryptedPassword = $matchedRow.Password | ConvertTo-SecureString
  $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($decryptedPassword))
  $plainPassword
}
 