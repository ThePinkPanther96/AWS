
function ConnectToAWS {
    param (
        [Parameter(Mandatory)][string]$Accesskey,
        [Parameter(Mandatory)][string]$SecetKey
    )
    if (-not(Get-Module -Name AWSPowerShell )) {
        Import-Module -Name AWSPowerShell
    }
    else {
       try {
        Set-AWSCredentials -AccessKey $Accesskey -SecretKey $SecetKey
       }
       catch {
        Write-Host "error"
       }
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