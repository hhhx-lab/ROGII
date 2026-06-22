param(
    [ValidateSet("conservative", "balanced", "aggressive")]
    [string]$Variant = "balanced",
    [switch]$SkipInstall,
    [switch]$SkipPart3Features,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ReportDir = Join-Path $Root "reports"
$LogDir = Join-Path $ReportDir "full_inference_logs"
$RunStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$SummaryJson = Join-Path $ReportDir "full_inference_run_summary.json"
$SummaryMd = Join-Path $ReportDir "full_inference_run_summary.md"
$Results = New-Object System.Collections.Generic.List[object]

function Format-Now {
    return (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
}

function Write-RunMessage {
    param([string]$Message)
    Write-Host ("[{0}] {1}" -f (Format-Now), $Message)
}

function Join-ProcessArguments {
    param([string[]]$Arguments)
    $quoted = foreach ($arg in $Arguments) {
        if ($arg -match '[\s"]') {
            '"' + ($arg -replace '"', '\"') + '"'
        } else {
            $arg
        }
    }
    return ($quoted -join " ")
}

function Convert-ToRelativePath {
    param([string]$Path)
    $rootWithSlash = $Root.TrimEnd("\") + "\"
    if ($Path.StartsWith($rootWithSlash, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $Path.Substring($rootWithSlash.Length)
    }
    return $Path
}

function Write-Summary {
    param(
        [string]$StartedAt,
        [string]$FinishedAt,
        [string]$Status,
        [string]$FailedStep
    )

    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

    $payload = [ordered]@{
        started_at = $StartedAt
        finished_at = $FinishedAt
        status = $Status
        failed_step = $FailedStep
        variant = $Variant
        dry_run = [bool]$DryRun
        results = $Results
    }
    $payload | ConvertTo-Json -Depth 6 | Set-Content -Path $SummaryJson -Encoding UTF8

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# Full Inference Run Summary")
    $lines.Add("")
    $lines.Add("- Started at: ``$StartedAt``")
    $lines.Add("- Finished at: ``$FinishedAt``")
    $lines.Add("- Status: ``$Status``")
    $lines.Add("- Failed step: ``$FailedStep``")
    $lines.Add("- Variant: ``$Variant``")
    $lines.Add("- Dry run: ``$([bool]$DryRun)``")
    $lines.Add("")
    $lines.Add("| Step | Exit code | Started | Finished | Seconds | Log |")
    $lines.Add("|---|---:|---|---|---:|---|")
    foreach ($result in $Results) {
        $line = "| {0} | {1} | {2} | {3} | {4:n1} | ``{5}`` |" -f `
            $result.step, `
            $result.exit_code, `
            $result.started_at, `
            $result.finished_at, `
            [double]$result.seconds, `
            $result.log
        $lines.Add($line)
    }
    $lines.Add("")
    $lines | Set-Content -Path $SummaryMd -Encoding UTF8
}

function Ensure-DataRaw {
    $repoData = Join-Path $Root "data"
    $repoRaw = Join-Path $repoData "raw"

    if ((Test-Path (Join-Path $repoData "train")) -and
        (Test-Path (Join-Path $repoData "test"))) {
        Write-RunMessage "Using data at $(Convert-ToRelativePath $repoData)"
        return
    }

    if ((Test-Path (Join-Path $repoRaw "train")) -and
        (Test-Path (Join-Path $repoRaw "test"))) {
        Write-RunMessage "Using data at $(Convert-ToRelativePath $repoRaw)"
        return
    }

    $parentRaw = (Resolve-Path -ErrorAction SilentlyContinue (Join-Path $Root "..\data\raw"))
    if ($null -eq $parentRaw) {
        throw "Could not find data/raw under repository or parent folder."
    }

    $targetRaw = $parentRaw.Path
    foreach ($required in @("train", "test")) {
        if (-not (Test-Path (Join-Path $targetRaw $required))) {
            throw "Data candidate is missing ${required}: $targetRaw"
        }
    }

    New-Item -ItemType Directory -Force -Path $repoData | Out-Null
    if (Test-Path $repoRaw) {
        throw "Repository data/raw exists but is incomplete: $repoRaw"
    }

    New-Item -ItemType Junction -Path $repoRaw -Target $targetRaw | Out-Null
    Write-RunMessage "Linked repository data/raw to $targetRaw"
}

function Resolve-Python {
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    if ($DryRun) {
        return "python"
    }
    Write-RunMessage "Creating .venv"
    & python -m venv (Join-Path $Root ".venv")
    if (-not (Test-Path $venvPython)) {
        throw "Failed to create .venv Python at $venvPython"
    }
    return $venvPython
}

function Run-Step {
    param(
        [string]$Name,
        [string[]]$Command,
        [hashtable]$ExtraEnv = @{}
    )

    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $logPath = Join-Path $LogDir ("{0}_{1:00}_{2}.log" -f $RunStamp, ($Results.Count + 1), $Name)
    $relativeLogPath = Convert-ToRelativePath $logPath
    $startedAt = Format-Now
    $watch = [System.Diagnostics.Stopwatch]::StartNew()

    Write-RunMessage ("START {0}" -f $Name)
    Write-RunMessage ("LOG   {0}" -f $relativeLogPath)
    Write-RunMessage ("CMD   {0}" -f ($Command -join " "))

    $exitCode = 0
    if ($DryRun) {
        "DRY RUN: $($Command -join ' ')" | Set-Content -Path $logPath -Encoding UTF8
    } else {
        $oldEnv = @{}
        foreach ($key in $ExtraEnv.Keys) {
            $oldEnv[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
            [Environment]::SetEnvironmentVariable($key, [string]$ExtraEnv[$key], "Process")
        }
        try {
            $exe = $Command[0]
            $args = @()
            if ($Command.Count -gt 1) {
                $args = $Command[1..($Command.Count - 1)]
            }
            $psi = [System.Diagnostics.ProcessStartInfo]::new()
            $psi.FileName = $exe
            $psi.Arguments = Join-ProcessArguments $args
            $psi.WorkingDirectory = $Root
            $psi.UseShellExecute = $false
            $psi.RedirectStandardOutput = $true
            $psi.RedirectStandardError = $true

            $process = [System.Diagnostics.Process]::new()
            $process.StartInfo = $psi
            try {
                [void]$process.Start()
                $stdoutTask = $process.StandardOutput.ReadToEndAsync()
                $stderrTask = $process.StandardError.ReadToEndAsync()
                $process.WaitForExit()
                $stdout = $stdoutTask.Result
                $stderr = $stderrTask.Result
                $exitCode = $process.ExitCode

                $logParts = New-Object System.Collections.Generic.List[string]
                $logParts.Add("# $Name")
                $logParts.Add("")
                $logParts.Add("Command: $($Command -join ' ')")
                $logParts.Add("")
                if (-not [string]::IsNullOrWhiteSpace($stdout)) {
                    $logParts.Add("## stdout")
                    $logParts.Add("")
                    $logParts.Add($stdout.TrimEnd())
                    Write-Host $stdout.TrimEnd()
                }
                if (-not [string]::IsNullOrWhiteSpace($stderr)) {
                    $logParts.Add("")
                    $logParts.Add("## stderr")
                    $logParts.Add("")
                    $logParts.Add($stderr.TrimEnd())
                    Write-Host $stderr.TrimEnd()
                }
                $logParts.Add("")
                $logParts.Add("Exit code: $exitCode")
                $logParts | Set-Content -Path $logPath -Encoding UTF8
            } finally {
                $process.Dispose()
            }
        } finally {
            foreach ($key in $ExtraEnv.Keys) {
                [Environment]::SetEnvironmentVariable($key, $oldEnv[$key], "Process")
            }
        }
    }

    $watch.Stop()
    $finishedAt = Format-Now
    $Results.Add([pscustomobject]@{
        step = $Name
        command = $Command
        started_at = $startedAt
        finished_at = $finishedAt
        seconds = [math]::Round($watch.Elapsed.TotalSeconds, 3)
        exit_code = [int]$exitCode
        log = $relativeLogPath
    }) | Out-Null

    Write-RunMessage ("END   {0} exit={1} seconds={2:n1}" -f $Name, $exitCode, $watch.Elapsed.TotalSeconds)
    if ($exitCode -ne 0) {
        throw "Step failed: $Name"
    }
}

Set-Location $Root
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$startedAt = Format-Now
$failedStep = ""

try {
    Write-RunMessage "Full inference run started at $Root"
    Ensure-DataRaw
    $Python = Resolve-Python

    if (-not $SkipInstall) {
        Run-Step "install_dependencies" @($Python, "-m", "pip", "install", "-r", "requirements.txt")
    }

    Run-Step "eda" @($Python, "scripts/run_eda.py")
    Run-Step "data_contract" @($Python, "scripts/check_data_contract.py")
    Run-Step "baseline_cv" @($Python, "scripts/evaluate_baseline_cv.py")
    Run-Step "baseline_features" @($Python, "scripts/build_baseline_features.py")
    Run-Step "geometry_features" @($Python, "scripts/build_geometry_features.py")
    Run-Step "train_geometry_residual" @($Python, "scripts/train_residual_model.py", "--spec", "geometry")
    Run-Step "part3_diagnostics" @($Python, "scripts/build_part3_diagnostics.py")

    if (-not $SkipPart3Features) {
        Run-Step "part3_features" @($Python, "scripts/build_part3_features.py")
    }

    Run-Step "blend_predictions" @($Python, "scripts/blend_predictions.py")
    Run-Step "postprocess_$Variant" @($Python, "scripts/postprocess_predictions.py", "--variant", $Variant)
    Run-Step "make_submission_$Variant" @($Python, "scripts/make_submission.py", "--variant", $Variant, "--output", "submission.csv")
    Run-Step "validate_submission" @($Python, "scripts/validate_submission.py", "--submission", "submission.csv")

    $finishedAt = Format-Now
    Write-Summary $startedAt $finishedAt "PASS" ""
    Write-RunMessage "Full inference run passed. Summary: $(Convert-ToRelativePath $SummaryMd)"
    exit 0
} catch {
    $finishedAt = Format-Now
    if ($Results.Count -gt 0) {
        $last = $Results[$Results.Count - 1]
        if ($last.exit_code -ne 0) {
            $failedStep = $last.step
        }
    }
    if ($failedStep -eq "") {
        $failedStep = "setup"
    }
    Write-Summary $startedAt $finishedAt "FAIL" $failedStep
    Write-RunMessage ("FAILED {0}: {1}" -f $failedStep, $_.Exception.Message)
    Write-RunMessage ("Summary: {0}" -f (Convert-ToRelativePath $SummaryMd))
    if ($Results.Count -gt 0) {
        $last = $Results[$Results.Count - 1]
        Write-RunMessage ("Last log: {0}" -f $last.log)
    }
    exit 1
}
