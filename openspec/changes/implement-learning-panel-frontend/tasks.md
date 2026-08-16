## 1. 后端：任课班级列表端点

- [ ] 1.1 写测试 `tests/test_classes_api.py`：教师返回任课班级（`class_id`/`class_name`/`subject`）、无任课返回空数组、学生返回 403 `PERMISSION_DENIED`
- [ ] 1.2 实现 `app/api/classes.py`：`GET /api/classes`，`require_role(["teacher","admin"])`，teacher 走 `TeacherClassSubject` 关联、admin 返回本校全部班级，按学校隔离
- [ ] 1.3 在 `app/api/__init__.py` 导出 `classes_router`，`app/main.py` `include_router` 注册
- [ ] 1.4 运行新增测试确认 GREEN（RED → GREEN）

## 2. 前端：面板页面骨架与数据加载

- [ ] 2.1 创建 `frontend/pages/panel.html` 骨架：Tailwind CDN + 设计系统 `tailwind.config`（Oxford Blue / Teal / Warm Paper、Cormorant Garamond 标题）+ 字体；布局含班级选择器、4 KPI 卡区、3 图表区、需关注学生横条、抽屉容器
- [ ] 2.2 实现认证与 fetch 封装：读取 `localStorage.chemai_token`、`Authorization: Bearer`、401 清 token 跳登录、`API_BASE = http://localhost:8000`
- [ ] 2.3 实现班级选择器：`GET /api/classes` 填充、默认选首班、切班并行重拉面板 + 趋势、空态「暂无任课班级」
- [ ] 2.4 实现 4 张 KPI 概要卡：考试次数 / 需关注学生（`dominant_barrier` 非空人数）/ 班级人数 / 最近均分（null 显示「—」）

## 3. 前端：三个图表

- [ ] 3.1 知识点错误率柱状图：`knowledge_points` 按错误率降序渲染（最多 10 项）、空态「暂无作答数据」
- [ ] 3.2 障碍类型环形图：`barrier_distribution` 三段 SVG（concept 紫 / reading 蓝 / expression 青）、全零空态
- [ ] 3.3 成绩趋势折线图：`trend.score_trend` SVG polyline、少于 2 点提示「数据不足以绘制趋势」

## 4. 前端：学生下钻与状态处理

- [ ] 4.1 需关注学生横条：`students` 渲染 concept/reading/expression 三项比例横条、空班级空态
- [ ] 4.2 学生详情抽屉：点击学生 `GET /api/panel/class/{cid}/student/{sid}` 渲染障碍分布/主导障碍/薄弱知识点/作答历史，支持关闭
- [ ] 4.3 加载 / 空 / 错误状态：骨架屏、空态、接口失败「重试」按钮
- [ ] 4.4 演示模式：核心接口失败降级为内置静态示例数据并显示「演示数据」徽标，后端恢复可重载真实数据

## 5. 验证与收尾

- [ ] 5.1 后端全量 `pytest` 无回归（含新增 classes 测试）
- [ ] 5.2 前端浏览器冒烟：登录 → 打开面板 → 切班 → 开学生抽屉 → 模拟接口失败进入演示模式
- [ ] 5.3 `openspec validate implement-learning-panel-frontend` 通过
