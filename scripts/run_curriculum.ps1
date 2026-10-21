<#
.SYNOPSIS
    课程采样闭环：采集 rollout → 算权重 → 采样题目 → 按课程训练一段。

.DESCRIPTION
    三步对应三支脚本，任何一步都可以单独重跑：

      1. collect_rollouts   用「当前策略」在 train 题上每题采 G 条，打分 + 归类
                            → results/rollout_groups_<version>.jsonl
      2. bad_case_sampler   按组内奖励方差 / 成功率 / 错误类别算权重并抽样
                            → data/tasks/curriculum_train.jsonl + results/curriculum_audit.json
      3. train_grpo_agentic 读 curriculum 训练（--curriculum），题目可重复出现

    关键点：groups 必须是**同一个 policy_version** 的 rollout。所以每轮换
    adapter 之后都要重新采一次，不能复用上一轮的文件。

.PARAMETER Run
    用哪个 run 当「当前策略」。默认 runs/grpo_agentic。

.PARAMETER FromBase
    还没有 adapter 时用基座模型采集（policy_version=base）。

.PARAMETER G
    每题采样条数，至少 2。越大统计越稳，成本线性上升。

.PARAMETER Limit
    只采前 N 题，用于试通链路。**试通产物不要拿去训练**：没被采到的题会被采样器
    赋中性权重，课程会退化成「少数题 + 均匀噪声」。

.EXAMPLE
    .\scripts\run_curriculum.ps1 -Limit 3 -G 2 -Steps 2      # 先花几分钟试通
    .\scripts\run_curriculum.ps1 -FromBase -G 4 -Steps 10    # 第一轮：基座模型采集
#>
param(
    [string]$Run = "grpo_agentic",
    [switch]$FromBase,
    [int]$G = 4,
    [int]$Steps = 10,
    [int]$Limit = 0,
    [int]$Count = 35,
    [switch]$Download
)

$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root ".venv-ml\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "ML venv not found: $python" }

$env:KMP_DUPLICATE_LIB_OK = "TRUE"
$env:PYTHONIOENCODING = "utf-8"
# -Download 让三个子步骤都允许联网拉模型（默认只用本地缓存）
if ($Download) { $env:LEGALAGENT_ALLOW_DOWNLOAD = "1" }

$version = if ($FromBase) { "base" } else { $Run }
$groupsFile = "results/rollout_groups_$version.jsonl"
$curriculum = "data/tasks/curriculum_train.jsonl"

# 早失败：adapter 不存在时，别让 PeftModel 抛一大段 HF 堆栈。
if (-not $FromBase -and -not (Test-Path (Join-Path $root "runs\$Run"))) {
    throw "找不到 adapter: runs\$Run。runs/ 当前是空的 —— 改用 -FromBase（基座模型采集），或把 -Run 指向一个真实存在的 adapter。"
}

function Invoke-Step {
    param([string]$Title, [string[]]$PyArgs)
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
    Write-Host "  python $($PyArgs -join ' ')" -ForegroundColor DarkGray
    & $python @PyArgs
    if ($LASTEXITCODE -ne 0) { throw "$Title failed (exit $LASTEXITCODE)" }
}

Push-Location $root
try {
    # 1) 采集
    $collectArgs = @(
        "-m", "legalagent.analysis.collect_rollouts",
        "--split", "train", "--groups", "$G",
        "--policy-version", $version,
        "--out", $groupsFile
    )
    if (-not $FromBase) { $collectArgs += @("--adapter", "runs/$Run") }
    if ($Limit -gt 0) { $collectArgs += @("--limit", "$Limit") }
    Invoke-Step "1/3 collect rollout groups (policy=$version, G=$G)" $collectArgs

    # 2) 采样
    Invoke-Step "2/3 sample curriculum" @(
        "-m", "legalagent.analysis.bad_case_sampler",
        "--labels", "data/tasks/tasks_train_labeled.jsonl",
        "--prompts", "data/tasks/tasks_train_prompts_only.jsonl",
        "--groups", $groupsFile,
        "--count", "$Count", "--seed", "42", "--explore", "0.30",
        "--output", $curriculum,
        "--audit", "results/curriculum_audit.json"
    )

    # 3) 训练
    Invoke-Step "3/3 train on curriculum" @(
        "-m", "legalagent.train.train_grpo_agentic",
        "--max-steps", "$Steps",
        "--curriculum", $curriculum,
        "--out", "runs/${Run}_curr"
    )

    Write-Host ""
    Write-Host "[done] 下一轮把 -Run 指向 runs/${Run}_curr 即可（采集要用新策略）" -ForegroundColor Green
    if ($Limit -gt 0) {
        Write-Host "[warn] 这次只采了 $Limit 题，课程不可用于正式实验" -ForegroundColor Yellow
    }
}
finally {
    Pop-Location
}
