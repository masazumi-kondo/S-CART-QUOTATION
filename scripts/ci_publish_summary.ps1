param(
    [string]$JOB_LABEL = $env:JOB_LABEL,
    [string]$SCRIPT_LABEL = $env:SCRIPT_LABEL,
    [string]$ARTIFACT_LABEL = $env:ARTIFACT_LABEL
)
$summaryDir = "artifacts/test_summary"
Add-Content -Path $env:GITHUB_STEP_SUMMARY -Value "## Test Summary ($JOB_LABEL job)`nThis job runs $SCRIPT_LABEL directly.`nArtifacts: test_logs_$ARTIFACT_LABEL / server_logs_$ARTIFACT_LABEL`n"
if (!(Test-Path $summaryDir)) {
    Add-Content -Path $env:GITHUB_STEP_SUMMARY -Value "No test summary directory found.`n"
} else {
    try {
        $latest = Get-ChildItem $summaryDir -Filter "test_summary_*.md" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latest) {
            $content = Get-Content -Path $latest.FullName -Raw
            Add-Content -Path $env:GITHUB_STEP_SUMMARY -Value $content
        } else {
            Add-Content -Path $env:GITHUB_STEP_SUMMARY -Value "No test summary file found.`n"
        }
    } catch {
        Add-Content -Path $env:GITHUB_STEP_SUMMARY -Value "Error reading summary file: $($_.Exception.Message)`n"
    }
}
