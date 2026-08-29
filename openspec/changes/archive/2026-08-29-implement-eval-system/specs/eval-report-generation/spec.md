## Purpose

将确定性评测和 LLM-as-Judge 两轨的结果合并为结构化评测报告，支持分层统计、失败明细和基线对比。

## ADDED Requirements

### Requirement: 评测报告生成
系统 SHALL 将两轨评测结果合并生成 Markdown 格式的评测报告。

#### Scenario: 生成完整报告
- **WHEN** 确定性评测 41 场景（41 passed）、LLM-as-Judge 15 场景（14 passed,1 failed）
- **THEN** 生成报告包含：总场景 56、通过 55、失败 1、通过率 98.2%

#### Scenario: 报告写入文件
- **WHEN** 报告生成完毕
- **THEN** 写入 `qa-reports/eval-report-{date}.md`

### Requirement: 分层统计
报告 SHALL 按基线/边界/回归三层分别统计通过率。

#### Scenario: 分层统计表格
- **WHEN** 基线 16 passed、边界 14/15 passed、回归 25/25 passed
- **THEN** 报告包含分层统计表：基线 100%、边界 93.3%、回归 100%

### Requirement: 失败明细
报告 SHALL 列出每个失败场景的 ID、输入、预期结果、实际结果和失败原因。

#### Scenario: 失败场景明细
- **WHEN** SEC-005 因地址脱敏粒度不足失败
- **THEN** 报告包含 SEC-005 的输入、预期输出、实际输出和失败原因分析

### Requirement: 基线对比
报告 SHALL 支持与上次评测结果对比，标注新增失败和修复的场景。

#### Scenario: 与上次对比
- **WHEN** 本次 passed=55，上次 passed=53
- **THEN** 报告标注 "passed +2"，列出新增通过的场景 ID

#### Scenario: 无历史基线
- **WHEN** 无历史评测结果可对比
- **THEN** 报告标注"首次评测，无基线对比"

### Requirement: 执行耗时统计
报告 SHALL 包含各轨道和总体的执行耗时。

#### Scenario: 耗时统计
- **WHEN** 确定性评测 4.2s，LLM-as-Judge 1m48s，pytest 28s
- **THEN** 报告包含各轨道耗时和总计 2m20s

### Requirement: 整合 pytest 结果
run_evals.py SHALL 支持同时运行现有 pytest 测试套件，结果纳入评测报告。

#### Scenario: 三轨整合
- **WHEN** 运行 `run_evals.py --track all`
- **THEN** 依次执行确定性评测、LLM-as-Judge、pytest，合并结果生成统一报告

#### Scenario: 单轨运行
- **WHEN** 运行 `run_evals.py --track deterministic`
- **THEN** 只执行确定性评测，报告只包含该轨道结果
