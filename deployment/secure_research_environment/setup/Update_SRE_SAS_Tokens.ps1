param(
    [Parameter(Mandatory = $true, HelpMessage = "Enter SHM ID (e.g. 'project')")]
    [string]$shmId,
    [Parameter(Mandatory = $true, HelpMessage = "Enter SRE ID (e.g. 'sandbox')")]
    [string]$sreId
)

Import-Module Az.Accounts -ErrorAction Stop
Import-Module Az.Resources -ErrorAction Stop
Import-Module Az.Storage -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/AzureCompute -Force -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/AzureKeyVault -Force -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/AzureStorage -Force -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/Configuration -Force -ErrorAction Stop
Import-Module $PSScriptRoot/../../common/Logging -Force -ErrorAction Stop


# Get config and original context before changing subscription
# ------------------------------------------------------------
$config = Get-SreConfig -shmId $shmId -sreId $sreId
$originalContext = Get-AzContext
$null = Set-AzContext -SubscriptionId $config.sre.subscriptionName -ErrorAction Stop

# Generate a new SAS token for each persistent data container
# -----------------------------------------------------------
$persistentStorageAccount = Get-StorageAccount -ResourceGroupName $config.shm.storage.persistentdata.rg -Name $config.sre.storage.persistentdata.account.name
$sasTokens = @{}
foreach ($receptacleName in $config.sre.storage.persistentdata.containers.Keys) {
    # Create SAS policy
    $accessPolicyName = $config.sre.storage.persistentdata.containers[$receptacleName].accessPolicyName
    $sasPolicy = Deploy-SasAccessPolicy -Name $accessPolicyName `
                                        -Permission $config.sre.storage.accessPolicies[$accessPolicyName].permissions `
                                        -StorageAccount $persistentStorageAccount `
                                        -ContainerName $receptacleName `
                                        -ValidityYears 1
    # Create token
    $sasToken = New-StorageReceptacleSasToken -ContainerName $receptacleName -PolicyName $sasPolicy.Policy -StorageAccount $persistentStorageAccount
    # Write to KeyVault
    $sasTokens[$receptacleName] = Resolve-KeyVaultSecret -VaultName $config.sre.keyVault.name -SecretName $config.sre.storage.persistentdata.containers[$receptacleName].connectionSecretName -DefaultValue $sasToken -AsPlaintext -ForceOverwrite
}

# Get list of SRDs
# ----------------
Add-LogMessage -Level Info "Retrieving list of SRD VMs..."
$VMs = Get-AzVM -ResourceGroupName $config.sre.srd.rg | `
    Where-Object { $_.Name -like "*SRD*" }

# Update blobfuse credentials on each SRD
# ---------------------------------------
$sasTokensBase64 = @{}
$sasTokens.Keys | For-EachObject {
    $sasTokensBase64[($_ + '_B64')] = ($sasTokens[$_] | ConvertTo-Base64)
}
$scriptPath = Join-Path $PSScriptRoot ".." "remote" "secure_research_desktop" "scripts" "write_sas_tokens.sh"
foreach ($VM in $Vms) {
    $null = Invoke-RemoteScript -VMName $VM.Name -ResourceGroupName $VM.ResourceGroupName -Shell "UnixShell" -ScriptPath $scriptPath -Parameter $sasTokens
}


# Switch back to original subscription
# ------------------------------------
$null = Set-AzContext -Context $originalContext -ErrorAction Stop
