function Connect-Session {
  param(
    [Parameter(Mandatory)][string]$key,
    [Parameter(Mandatory)][string]$SKey,
    [Parameter(Mandatory)][string]$region
  )
  $env:AWS_ACCESS_KEY_ID = $key
  $env:AWS_SECRET_ACCESS_KEY = $SKey
  $env:AWS_DEFAULT_REGION = $region
  try {
    Import-Module -name AWSPowerShell
    Initialize-AWSDefaults -AccessKey $key -SecretKey $SKey -Region $region
  }
  catch {
    Write-Host "ERROR: $_" # temp
  }  
}

function Exit-Session {
  try {
    Remove-Module -name AWSPowerShell
    Clear-AWSCredential -force
  }
  catch {
    Write-Host "ERROR: $_" # temp
  }
}


function CreateIAMUser {
    
}


function CreateIAMGroup {

    
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



# temp

$key = ""
$SKey = ""
$region = ""

Connect-Session -key $key -SKey $SKey -region $region

# Stop-Session
