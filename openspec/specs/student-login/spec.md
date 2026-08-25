## Purpose

为学生提供独立的登录入口，支持学号或手机号 + 密码认证，登录后获取 JWT 并持久化到 localStorage，实现无登录态自动跳转。

## ADDED Requirements

### Requirement: 学生登录表单

系统 SHALL 提供 `login.html` 登录页面，包含学号/手机号输入框、密码输入框（支持可见性切换）和登录按钮。页面使用 ChemAI 设计系统（Oxford Blue 主色、Warm Paper 背景、IBM Plex Sans 字体）。

#### Scenario: 正常登录

- **WHEN** 学生输入正确的学号/手机号和密码，点击登录
- **THEN** 系统调用 `POST /api/auth/login`，成功后将 `access_token` 存入 `localStorage`（键 `chemai_token`），跳转至 `index.html`

#### Scenario: 登录失败

- **WHEN** 学生输入错误的账号或密码
- **THEN** 登录按钮显示错误提示"账号或密码错误"，输入框显示红色边框

#### Scenario: 登录中状态

- **WHEN** 学生点击登录按钮，请求进行中
- **THEN** 登录按钮显示"登录中…"并禁用，防止重复提交

### Requirement: 密码可见性切换

系统 SHALL 在密码输入框右侧提供眼睛图标，点击可切换密码明文/密文显示。

#### Scenario: 切换可见性

- **WHEN** 学生点击密码输入框右侧的眼睛图标
- **THEN** 密码从密文（••••）切换为明文显示，图标同步切换

### Requirement: 认证守卫

系统 SHALL 在每个学生端页面加载时检查 JWT 有效性，无 token 或 token 过期时自动跳转至登录页。

#### Scenario: 无 token 跳转

- **WHEN** 学生访问任意学生端页面且 `localStorage` 中无 `chemai_token`
- **THEN** 系统自动跳转至 `login.html`

#### Scenario: token 过期跳转

- **WHEN** 学生访问任意学生端页面且 JWT 的 `exp` 字段已过期
- **THEN** 系统清除过期 token，跳转至 `login.html`

### Requirement: 退出登录

系统 SHALL 在侧边栏（AI 助教页）和「我的」页面提供退出登录功能，清除 token 后跳转至登录页。

#### Scenario: 退出登录

- **WHEN** 学生点击"退出登录"
- **THEN** 系统清除 `localStorage` 中的 `chemai_token`，跳转至 `login.html`
