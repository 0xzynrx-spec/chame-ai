"""ChemAI Backend — 试卷 HTML 导出服务

将考试关联的题目按模板排版渲染为可打印的 HTML 文档。
"""

from app.models import Exam


# 题型分组顺序和中文标题
QUESTION_TYPE_ORDER = ["choice", "fill", "calc", "experiment", "inference"]
QUESTION_TYPE_LABELS = {
    "choice": "选择题",
    "fill": "填空题",
    "calc": "计算题",
    "experiment": "实验题",
    "inference": "推断题",
}
# 每题默认分值（用于均分）
DEFAULT_SCORE_PER_QUESTION = {
    "choice": 6,
    "fill": 8,
    "calc": 12,
    "experiment": 12,
    "inference": 10,
}


def build_paper_html(
    exam: Exam,
    questions: list,
    include_answers: bool = False,
) -> str:
    """构建试卷 HTML 文档

    Args:
        exam: Exam ORM 对象
        questions: Question ORM 对象列表（去重后）
        include_answers: 是否包含参考答案

    Returns:
        完整的 HTML 文档字符串
    """
    # 按题型分组
    groups: dict[str, list] = {}
    for q in questions:
        q_type = q.type.value if hasattr(q.type, "value") else str(q.type)
        groups.setdefault(q_type, []).append(q)

    # 按预定顺序排列
    ordered_groups = []
    for q_type in QUESTION_TYPE_ORDER:
        if q_type in groups:
            ordered_groups.append((q_type, groups[q_type]))

    # 构建题目区域
    question_html = ""
    global_num = 1
    for q_type, qs in ordered_groups:
        per_q_score = DEFAULT_SCORE_PER_QUESTION.get(q_type, 10)
        total_score = per_q_score * len(qs)
        label = QUESTION_TYPE_LABELS.get(q_type, q_type)

        question_html += f"""
        <div class="section">
            <h2 class="section-title">{_num_to_chinese(QUESTION_TYPE_ORDER.index(q_type) + 1)}、{label}（共 {total_score} 分）</h2>
"""
        for q in qs:
            q_score = per_q_score
            content = (q.content_i18n or {}).get("zh", "") or ""
            options = (q.options_i18n or {}).get("zh", []) or []
            answer = (q.answer_i18n or {}).get("zh", "") or ""
            analysis = (q.analysis_i18n or {}).get("zh", "") or ""

            question_html += f"""
            <div class="question">
                <p class="question-text"><strong>{global_num}.</strong> {content} <span class="score">（{q_score} 分）</span></p>
"""
            # 选项
            if options:
                labels = ["A", "B", "C", "D", "E", "F"]
                question_html += '                <div class="options">\n'
                for i, opt in enumerate(options):
                    question_html += f'                    <div class="option">{labels[i]}. {opt}</div>\n'
                question_html += '                </div>\n'

            # 答题区或答案
            if include_answers:
                if answer:
                    question_html += f'                <div class="answer">参考答案：{answer}</div>\n'
                if analysis:
                    question_html += f'                <div class="analysis">解析：{analysis}</div>\n'
            else:
                question_html += '                <div class="answer-blank">\n'
                # 填空题/计算题留更多空白
                if q_type in ("fill", "calc", "experiment", "inference"):
                    question_html += '                    <div class="blank-line"></div>\n' * 3
                question_html += '                </div>\n'

            question_html += '            </div>\n'
            global_num += 1

        question_html += '        </div>\n'

    # 组装完整 HTML
    classes_str = "、".join(
        c.get("name", "") for c in (exam.classes or [])
    ) or "全部班级"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{exam.name}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css" crossorigin="anonymous">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js" crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js" crossorigin="anonymous"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "SimSun", "Songti SC", "Noto Serif CJK SC", serif;
            font-size: 14px;
            line-height: 1.8;
            color: #333;
            max-width: 210mm;
            margin: 0 auto;
            padding: 20px 25px;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #002147;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-family: "SimHei", "PingFang SC", "Microsoft YaHei", sans-serif;
            font-size: 22px;
            color: #002147;
            margin-bottom: 8px;
        }}
        .header .info {{
            font-size: 13px;
            color: #555;
            display: flex;
            justify-content: center;
            gap: 24px;
            flex-wrap: wrap;
        }}
        .section {{ margin-bottom: 24px; }}
        .section-title {{
            font-family: "SimHei", "PingFang SC", "Microsoft YaHei", sans-serif;
            font-size: 16px;
            color: #002147;
            margin-bottom: 10px;
            padding-bottom: 4px;
            border-bottom: 1px solid #ddd;
        }}
        .question {{ margin-bottom: 14px; page-break-inside: avoid; }}
        .question-text {{ margin-bottom: 4px; }}
        .score {{ color: #888; font-size: 12px; }}
        .options {{ margin-left: 20px; }}
        .option {{ margin-bottom: 2px; }}
        .answer {{
            color: #002147;
            background: #e8f4f8;
            padding: 4px 8px;
            margin-top: 4px;
            border-left: 3px solid #0d7377;
        }}
        .analysis {{
            color: #555;
            font-size: 13px;
            margin-top: 2px;
            padding-left: 8px;
        }}
        .answer-blank {{ min-height: 30px; }}
        .blank-line {{
            border-bottom: 1px solid #ccc;
            height: 24px;
        }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: #999;
            margin-top: 30px;
            padding-top: 10px;
            border-top: 1px solid #eee;
        }}
        @media print {{
            body {{ padding: 0; }}
            .header {{ border-bottom-color: #000; }}
            @page {{
                size: A4;
                margin: 15mm;
                @bottom-center {{ content: "第 " counter(page) " 页"; }}
                @top-center {{ content: "{exam.name}"; }}
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{exam.name}</h1>
        <div class="info">
            <span>总分：{exam.total_score} 分</span>
            <span>时长：{exam.duration_minutes} 分钟</span>
            <span>班级：{classes_str}</span>
        </div>
    </div>
{question_html}
    <div class="footer">— ChemAI 智辅化学 —</div>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: "$$", right: "$$", display: true}},
                    {{left: "$", right: "$", display: false}},
                    {{left: "\\\\[", right: "\\\\]", display: true}},
                    {{left: "\\\\(", right: "\\\\)", display: false}},
                ],
                macros: {{ "\\ce": "\\require{{mhchem}}\\ce" }}
            }});
        }});
    </script>
</body>
</html>"""
    return html


def _num_to_chinese(n: int) -> str:
    """数字转中文（1-9 -> 一-九）"""
    chars = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
    if 1 <= n <= 9:
        return chars[n]
    return str(n)
