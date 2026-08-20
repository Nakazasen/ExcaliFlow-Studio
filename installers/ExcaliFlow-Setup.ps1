[CmdletBinding()]
param(
    [ValidateSet("codex", "antigravity", "agy", "claude", "copilot", "gemini", "opencode", "kiro", "custom")]
    [string]$IDE,
    [string]$Workspace,
    [string]$Target,
    [switch]$Quiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SkillContent = @("SKILL.md", "THIRD_PARTY_LICENSES.md", "agents", "assets", "scripts", "tests")
$RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$TargetConfig = Get-Content -LiteralPath (Join-Path $PSScriptRoot "host-targets.json") -Raw | ConvertFrom-Json

function Assert-PortableSkill {
    foreach ($name in $SkillContent) {
        if (-not (Test-Path -LiteralPath (Join-Path $RepositoryRoot $name))) {
            throw "The installer bundle is incomplete: missing $name. Download a complete ExcaliFlow release ZIP."
        }
    }
}

function Get-ConfigPath {
    param(
        [Parameter(Mandatory = $true)][object]$Segments,
        [Parameter(Mandatory = $true)][string]$Root
    )
    $result = $Root
    foreach ($segment in $Segments) {
        $result = Join-Path $result ([string]$segment)
    }
    return Join-Path $result "excaliflow"
}

function Resolve-SkillTarget {
    param(
        [Parameter(Mandatory = $true)][string]$SkillHost,
        [string]$WorkspacePath,
        [string]$ExplicitTarget
    )
    if ($SkillHost -eq "custom") {
        if ([string]::IsNullOrWhiteSpace($ExplicitTarget)) {
            throw "Custom IDE installation requires an exact destination folder."
        }
        return [System.IO.Path]::GetFullPath($ExplicitTarget)
    }
    if ($SkillHost -eq "antigravity") {
        $profile = Join-Path $HOME ".gemini\config\skills"
        if (-not (Test-Path -LiteralPath $profile -PathType Container)) {
            throw "Antigravity Desktop has no verified profile on this computer. Select Custom and choose its exact skill folder."
        }
        return Join-Path $profile "excaliflow"
    }
    if (-not [string]::IsNullOrWhiteSpace($WorkspacePath)) {
        if (-not (Test-Path -LiteralPath $WorkspacePath -PathType Container)) {
            throw "Workspace does not exist: $WorkspacePath"
        }
        $segments = $TargetConfig.workspace.PSObject.Properties[$SkillHost].Value
        if ($null -eq $segments) {
            throw "$SkillHost does not publish a workspace skill folder. Use Custom and choose an exact destination."
        }
        return Get-ConfigPath -Segments $segments -Root ([System.IO.Path]::GetFullPath($WorkspacePath))
    }
    $segments = $TargetConfig.user.PSObject.Properties[$SkillHost].Value
    if ($null -eq $segments) {
        throw "$SkillHost needs a workspace folder or an explicit custom destination."
    }
    return Get-ConfigPath -Segments $segments -Root $HOME
}

function Install-PortableSkill {
    param([Parameter(Mandatory = $true)][string]$Destination)
    Assert-PortableSkill
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    foreach ($name in $SkillContent) {
        Copy-Item -LiteralPath (Join-Path $RepositoryRoot $name) -Destination (Join-Path $Destination $name) -Recurse -Force
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Destination "scripts\generate_diagram.py") -PathType Leaf)) {
        throw "Verification failed: the generator is missing after installation."
    }
    return $Destination
}

function Select-Folder {
    param([string]$InitialPath)
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    if (-not [string]::IsNullOrWhiteSpace($InitialPath) -and (Test-Path -LiteralPath $InitialPath)) {
        $dialog.SelectedPath = $InitialPath
    }
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        return $dialog.SelectedPath
    }
    return $null
}

function Start-InstallerUi {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "ExcaliFlow Studio - One-click setup"
    $form.Size = New-Object System.Drawing.Size(700, 360)
    $form.StartPosition = "CenterScreen"
    $form.Font = New-Object System.Drawing.Font("Segoe UI", 10)
    $form.MaximizeBox = $false
    $form.FormBorderStyle = "FixedDialog"

    $title = New-Object System.Windows.Forms.Label
    $title.Text = "Install ExcaliFlow for your AI coding tool"
    $title.Font = New-Object System.Drawing.Font("Segoe UI", 15, [System.Drawing.FontStyle]::Bold)
    $title.AutoSize = $true
    $title.Location = New-Object System.Drawing.Point(24, 22)
    $form.Controls.Add($title)

    $hint = New-Object System.Windows.Forms.Label
    $hint.Text = "No Python, Administrator access, or network download is needed."
    $hint.AutoSize = $true
    $hint.Location = New-Object System.Drawing.Point(26, 56)
    $form.Controls.Add($hint)

    $hostLabel = New-Object System.Windows.Forms.Label
    $hostLabel.Text = "Tool"
    $hostLabel.AutoSize = $true
    $hostLabel.Location = New-Object System.Drawing.Point(26, 100)
    $form.Controls.Add($hostLabel)

    $hostBox = New-Object System.Windows.Forms.ComboBox
    $hostBox.DropDownStyle = "DropDownList"
    [void]$hostBox.Items.AddRange([string[]]@("codex", "antigravity", "claude", "copilot", "gemini", "opencode", "kiro", "agy", "custom"))
    $hostBox.SelectedIndex = 0
    $hostBox.Location = New-Object System.Drawing.Point(150, 96)
    $hostBox.Size = New-Object System.Drawing.Size(220, 28)
    $form.Controls.Add($hostBox)

    $workspaceCheck = New-Object System.Windows.Forms.CheckBox
    $workspaceCheck.Text = "Install in a project workspace"
    $workspaceCheck.AutoSize = $true
    $workspaceCheck.Location = New-Object System.Drawing.Point(26, 140)
    $form.Controls.Add($workspaceCheck)

    $workspaceBox = New-Object System.Windows.Forms.TextBox
    $workspaceBox.Location = New-Object System.Drawing.Point(150, 138)
    $workspaceBox.Size = New-Object System.Drawing.Size(405, 28)
    $workspaceBox.Enabled = $false
    $form.Controls.Add($workspaceBox)

    $browseWorkspace = New-Object System.Windows.Forms.Button
    $browseWorkspace.Text = "Browse"
    $browseWorkspace.Location = New-Object System.Drawing.Point(566, 137)
    $browseWorkspace.Size = New-Object System.Drawing.Size(90, 30)
    $browseWorkspace.Enabled = $false
    $form.Controls.Add($browseWorkspace)

    $destinationLabel = New-Object System.Windows.Forms.Label
    $destinationLabel.Text = "Destination"
    $destinationLabel.AutoSize = $true
    $destinationLabel.Location = New-Object System.Drawing.Point(26, 184)
    $form.Controls.Add($destinationLabel)

    $destinationBox = New-Object System.Windows.Forms.TextBox
    $destinationBox.Location = New-Object System.Drawing.Point(150, 180)
    $destinationBox.Size = New-Object System.Drawing.Size(405, 28)
    $destinationBox.ReadOnly = $true
    $form.Controls.Add($destinationBox)

    $browseDestination = New-Object System.Windows.Forms.Button
    $browseDestination.Text = "Browse"
    $browseDestination.Location = New-Object System.Drawing.Point(566, 179)
    $browseDestination.Size = New-Object System.Drawing.Size(90, 30)
    $browseDestination.Enabled = $false
    $form.Controls.Add($browseDestination)

    $status = New-Object System.Windows.Forms.Label
    $status.AutoSize = $false
    $status.Size = New-Object System.Drawing.Size(630, 36)
    $status.Location = New-Object System.Drawing.Point(26, 220)
    $form.Controls.Add($status)

    $install = New-Object System.Windows.Forms.Button
    $install.Text = "Install ExcaliFlow"
    $install.Location = New-Object System.Drawing.Point(426, 270)
    $install.Size = New-Object System.Drawing.Size(230, 42)
    $form.Controls.Add($install)

    $refresh = {
        $skillHost = [string]$hostBox.SelectedItem
        $workspaceBox.Enabled = $workspaceCheck.Checked
        $browseWorkspace.Enabled = $workspaceCheck.Checked
        $isCustom = $skillHost -eq "custom"
        $destinationBox.ReadOnly = -not $isCustom
        $browseDestination.Enabled = $isCustom
        try {
            $workspacePath = if ($workspaceCheck.Checked) { $workspaceBox.Text } else { $null }
            $destinationBox.Text = Resolve-SkillTarget -SkillHost $skillHost -WorkspacePath $workspacePath -ExplicitTarget $destinationBox.Text
            $status.ForeColor = [System.Drawing.Color]::FromArgb(40, 100, 60)
            $status.Text = "The exact folder above will receive the portable skill."
        } catch {
            $status.ForeColor = [System.Drawing.Color]::FromArgb(150, 70, 20)
            $status.Text = $_.Exception.Message
            if (-not $isCustom) { $destinationBox.Text = "" }
        }
    }
    $hostBox.add_SelectedIndexChanged($refresh)
    $workspaceCheck.add_CheckedChanged($refresh)
    $workspaceBox.add_TextChanged($refresh)
    $browseWorkspace.add_Click({
        $selected = Select-Folder -InitialPath $workspaceBox.Text
        if ($selected) { $workspaceBox.Text = $selected }
    })
    $browseDestination.add_Click({
        $selected = Select-Folder -InitialPath $destinationBox.Text
        if ($selected) { $destinationBox.Text = (Join-Path $selected "excaliflow") }
    })
    $install.add_Click({
        try {
            $skillHost = [string]$hostBox.SelectedItem
            $workspacePath = if ($workspaceCheck.Checked) { $workspaceBox.Text } else { $null }
            $destination = Resolve-SkillTarget -SkillHost $skillHost -WorkspacePath $workspacePath -ExplicitTarget $destinationBox.Text
            $installed = Install-PortableSkill -Destination $destination
            [System.Windows.Forms.MessageBox]::Show("ExcaliFlow is ready in:`n$installed`n`nRestart or reload $skillHost to discover it.", "ExcaliFlow installed", "OK", "Information") | Out-Null
            $form.Close()
        } catch {
            [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, "ExcaliFlow was not installed", "OK", "Error") | Out-Null
        }
    })
    & $refresh
    [void]$form.ShowDialog()
}

if ($Quiet -or $PSBoundParameters.ContainsKey("IDE")) {
    if ([string]::IsNullOrWhiteSpace($IDE)) {
        throw "Non-interactive setup requires -IDE."
    }
    $installed = Install-PortableSkill -Destination (Resolve-SkillTarget -SkillHost $IDE -WorkspacePath $Workspace -ExplicitTarget $Target)
    Write-Output "Installed ExcaliFlow skill to: $installed"
} else {
    Start-InstallerUi
}
