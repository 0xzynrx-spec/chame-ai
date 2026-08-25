## Purpose

家长登录/注册页面，支持手机号+密码+绑定码的首次注册绑定和已有账号直接登录。

## ADDED Requirements

### Requirement: 家长注册与绑定
家长 SHALL 能够通过手机号、密码和 6 位绑定码一次性完成注册和学生绑定。

#### Scenario: 首次注册成功
- **WHEN** 家长输入有效手机号、密码和正确绑定码，点击"注册并绑定"
- **THEN** 系统调用 `POST /api/auth/parent/register`，成功后存储 JWT token 并跳转到 parent.html

#### Scenario: 绑定码无效
- **WHEN** 家长输入不存在或已失效的绑定码
- **THEN** 显示错误提示"绑定码错误"，输入框抖动

#### Scenario: 手机号已注册
- **WHEN** 家长输入已注册的手机号进行注册
- **THEN** 显示错误提示"该手机号已注册"，引导直接登录

### Requirement: 家长登录
已注册家长 SHALL 能够通过手机号和密码登录。

#### Scenario: 登录成功
- **WHEN** 家长输入正确手机号和密码，点击"登录"
- **THEN** 系统调用 `POST /api/auth/parent/login`，成功后存储 JWT token 并跳转到 parent.html

#### Scenario: 密码错误
- **WHEN** 家长输入错误密码
- **THEN** 显示错误提示"手机号或密码错误"，输入框抖动

### Requirement: 表单验证
登录表单 SHALL 在提交前验证必填字段。

#### Scenario: 空字段提交
- **WHEN** 家长未填写手机号或密码直接提交
- **THEN** 对应输入框标红，显示"请输入手机号"或"请输入密码"

#### Scenario: 绑定码格式校验
- **WHEN** 家长在绑定码输入框输入非数字字符
- **THEN** 自动过滤非数字，限制最多 6 位

### Requirement: 页面跳转
已登录家长 SHALL 自动跳转到主面板。

#### Scenario: 已登录状态访问登录页
- **WHEN** 已登录家长访问 parent-login.html
- **THEN** 自动跳转到 parent.html
