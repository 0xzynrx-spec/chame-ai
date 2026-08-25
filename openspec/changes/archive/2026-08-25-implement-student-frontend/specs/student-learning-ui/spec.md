## Purpose

升级现有学生端 3 个页面（练习/错题/复习）的视觉体验，统一落地 ChemAI 设计系统的骨架屏、空态、微交互规范。

## ADDED Requirements

### Requirement: 骨架屏加载态

系统 SHALL 在数据加载时显示骨架屏动画（灰色占位条脉冲闪烁），替代纯文字"加载中…"。

#### Scenario: 练习列表加载

- **WHEN** 学生进入练习页，数据加载中
- **THEN** 系统显示 3 个骨架卡片（灰色矩形脉冲动画），不显示"加载中…"

#### Scenario: 错题列表加载

- **WHEN** 学生进入错题本，数据加载中
- **THEN** 系统显示统计卡片骨架 + 3 个错题卡片骨架

#### Scenario: 复习列表加载

- **WHEN** 学生进入复习中心，数据加载中
- **THEN** 系统显示统计区骨架 + 3 个复习卡片骨架

### Requirement: 空态插图优化

系统 SHALL 在无数据时显示 Material Symbols 图标 + 引导文字 + 可选操作按钮，替代简单文字提示。

#### Scenario: 无练习任务

- **WHEN** 学生暂无待完成练习
- **THEN** 系统显示大号 `edit_note` 图标（Teal 色）+ "暂无练习任务" + "老师布置的个性化练习会出现在这里"

#### Scenario: 无错题

- **WHEN** 学生错题本为空
- **THEN** 系统显示大号 `task_alt` 图标（绿色）+ "暂无错题，继续保持！"

#### Scenario: 无待复习

- **WHEN** 学生无到期复习任务
- **THEN** 系统显示大号 `event_available` 图标 + "暂无待复习题目"

### Requirement: 卡片入场动画

系统 SHALL 在列表数据加载完成后，卡片从下方渐入（fade-in + slide-up），依次出现形成瀑布效果。

#### Scenario: 卡片瀑布入场

- **WHEN** 练习/错题/复习列表数据加载完成
- **THEN** 每张卡片以 `animation-delay: index * 60ms` 依次从下方 20px 处渐入

### Requirement: 统计数字跳动

系统 SHALL 在统计卡片中的数字从 0 跳动到目标值，持续 600ms。

#### Scenario: 数字动画

- **WHEN** 练习/错题/复习页面的统计数字渲染
- **THEN** 数字从 0 以 ease-out 缓动跳动到目标值，持续 600ms

### Requirement: 选项选中动效

系统 SHALL 在练习作答时，选项点击后 0.3s 显示正确/错误颜色反馈。

#### Scenario: 选项反馈

- **WHEN** 学生点击某个选项
- **THEN** 选中项以 Teal 边框 + 浅青背景高亮，0.3s 后根据正确性显示绿色（正确）或红色（错误）
