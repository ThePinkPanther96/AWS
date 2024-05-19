$scriptDirectory = Split-Path $MyInvocation.MyCommand.Path
Set-Location $scriptDirectory

Import-Module PSSQLite

Import-Module -Name "$scriptDirectory\MainLogic.ps1"
Import-Module -Name "$scriptDirectory\Utility.ps1"

# Create
function InsertNewCredentials {
    param(
        [string]$Database,
        [string]$Table,
        [hashtable[]]$Values
    )
    $query = "INSERT INTO $Table ("
    $query += ($Values.Name -join ', ')
    $query += ") VALUES ("
    $query += ($Values.Value | ForEach-Object { "'$_'" }) -join ', '
    $query += ")"

    Invoke-SqliteQuery -DataSource $Database -Query $query
}

function StoreAccessKeys { 
    param (
        [Parameter(Mandatory)][string]$AccessKey,
        [Parameter(Mandatory)][string]$SecretKey,
        [Parameter(Mandatory)][string]$Database,
        [Parameter(Mandatory)][string]$Username,
        [Parameter(Mandatory)][string]$Table
    )
    $values = @(
        @{ Name = "Username"; Value = "$Username" },
        @{ Name = "Access_Key"; Value = "$AccessKey" },
        @{ Name = "Secret_Key"; Value = "$SecretKey" } 
    )
    try { InsertNewCredentials -Database $Database -Values $values -Table $Table }
    catch { Write-Log -Function "StoreAccessKeys" -Level "ERROR" -Message "$_" }
} 

function StoreNewUser {
    param (
        [Parameter(Mandatory)][string]$Username,
        [string]$Key,
        [string]$Value,
        [string]$Table,
        [string]$Database
    )
    if ($Key -and $Value) {
        $values = @(
            @{ Name = "Username"; Value = "$Username" },
            @{ Name = "Key"; Value = "$Key" },
            @{ Name = "Value"; Value = "$Value" } 
        )   
    }
    else {
        $values = @(
            @{ Name = "Username"; Value = "$Username" }
        )
    }
    try { InsertNewCredentials -Database $Database -Values $values -Table $Table  }
    catch { Write-Log -Function "StoreAccessKeys" -Level "ERROR" -Message "$_" }
}

# Update

function UpdateCredentials {
    param(
        [string]$Database,
        [string]$Table,
        [hashtable[]]$Values
    )
    $query = "INSERT OR REPLACE INTO $Table ("
    $query += ($Values.Name -join ', ')
    $query += ") VALUES ("
    $query += ($Values.Value | ForEach-Object { "'$_'" }) -join ', '
    $query += ")"
    Invoke-SqliteQuery -DataSource $Database -Query $query
}




function UpdateDataAtStartup {

    
}


# Read

function GetValueByPrimaryKey {
    param (
        [Parameter(Mandatory)][string]$Database,
        [Parameter(Mandatory)][string]$Table,
        [Parameter(Mandatory)][string]$ValueToGet,
        [Parameter(Mandatory)][string]$PrimaryKeyName,
        [Parameter(Mandatory)][string]$PrimaryKeyValue
    )
    try {
        $query = "SELECT $ValueToGet FROM $Table WHERE $PrimaryKeyName = '$PrimaryKeyValue'"
        $Result = Invoke-SqliteQuery -DataSource $Database -Query $query
        if ($Result) {
            return $Result[0].$ValueToGet
        }
        return $false
    }
    catch { Write-Log -Function "FindRow" -Level "ERROR" -Message "$_" } 
}

function GetAccessKeys {
    

}


# Delete

function DeleteRowByPrimaryKey {
    param (
        [Parameter(Mandatory)][string]$Table,
        [Parameter(Mandatory)][string]$Database,
        [Parameter(Mandatory)][string]$PrimaryKeyValue,
        [Parameter(Mandatory)][string]$PrimaryKeyName

    )
    try {
        $Query = "DELETE FROM $Table WHERE $PrimaryKeyName = '$PrimaryKeyValue'"
        Invoke-SqliteQuery -Query $Query -DataSource $Database 
    }
    catch { Write-Log -Function "DeleteRow" -Level "ERROR" -Message "$_" }
}

function DeleteValueByPrimaryKey {
    param (
        [Parameter(Mandatory)][string]$Table,
        [Parameter(Mandatory)][string]$Database,
        [Parameter(Mandatory)][string]$PrimaryKeyValue,
        [Parameter(Mandatory)][string]$PrimaryKeyName,
        [Parameter(Mandatory)][string]$ValueToDelete
    )
    try {
        $Query = "UPDATE $Table SET $ValueToDelete = '' WHERE $PrimaryKeyName = '$PrimaryKeyValue'"
        Invoke-SqliteQuery -Query $Query -DataSource $Database 
    }
    catch { Write-Log -Function "DeleteRow" -Level "ERROR" -Message "$_" }
}




function DeleteAccessKeys {
    

}

