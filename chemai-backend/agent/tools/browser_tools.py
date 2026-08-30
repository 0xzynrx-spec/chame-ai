"""ChemAI Agent — 浏览器工具（5个）

navigate_to_page, click_element, fill_form, take_screenshot, extract_page_content
"""

from langchain.tools import tool


@tool
def navigate_to_page(url: str) -> str:
    """页面导航。

    **何时用**：需要打开某个页面时调用。
    **会发生什么**：浏览器导航到指定 URL，返回页面状态。
    **下一步**：可以调用 extract_page_content 提取内容。
    **NOT for**：前端路由跳转（用 navigate 事件）。

    Args:
        url: 目标 URL
    """
    return f"[导航] URL={url}\n导航中...（占位）"


@tool
def click_element(selector: str, page: str = "current") -> str:
    """点击页面元素。

    **何时用**：需要点击按钮、链接等页面元素时调用。
    **会发生什么**：模拟点击操作，返回点击结果。
    **下一步**：可以调用 take_screenshot 查看结果。
    **NOT for**：填写表单（用 fill_form）。

    Args:
        selector: CSS 选择器或元素描述
        page: 页面标识
    """
    return f"[点击] 选择器={selector}, 页面={page}\n点击中...（占位）"


@tool
def fill_form(selector: str, value: str, page: str = "current") -> str:
    """填写表单。

    **何时用**：需要在输入框中填写内容时调用。
    **会发生什么**：在指定输入框中填入值。
    **下一步**：可以调用 click_element 提交表单。
    **NOT for**：简单导航（用 navigate_to_page）。

    Args:
        selector: 输入框选择器
        value: 填入的值
        page: 页面标识
    """
    return f"[填写] 选择器={selector}, 值={value}\n填写中...（占位）"


@tool
def take_screenshot(page: str = "current") -> str:
    """截图。

    **何时用**：需要保存当前页面状态时调用。
    **会发生什么**：返回截图的 base64 编码或文件路径。
    **下一步**：可以将截图分享给用户。
    **NOT for**：提取文本内容（用 extract_page_content）。

    Args:
        page: 页面标识
    """
    return f"[截图] 页面={page}\n截图中...（占位）"


@tool
def extract_page_content(page: str = "current", selector: str = "") -> str:
    """提取页面内容。

    **何时用**：需要获取页面上的文本内容时调用。
    **会发生什么**：返回页面或指定元素的文本内容。
    **下一步**：可以对内容进行分析或总结。
    **NOT for**：截图（用 take_screenshot）。

    Args:
        page: 页面标识
        selector: 可选的元素选择器
    """
    return f"[提取内容] 页面={page}, 选择器={selector}\n提取中...（占位）"
