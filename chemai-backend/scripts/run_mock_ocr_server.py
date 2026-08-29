"""QA 辅助 — 以 mock OCR 提供方启动后端

识别固定返回「姓名: 张三」+ 两道作答（1. B / 2. NaCl），用于本地走通
「上传 → 识别 → 判分 → 复核 → 确认入库」完整闭环，无需百度 OCR 凭据。

原理：在导入 app.main 之前打桩 ocr_provider.is_ocr_configured / get_ocr_provider，
使 api/ocr.py 与 services/grading.py 的 from-import 绑定到 mock（不修改生产代码）。

运行：cd chemai-backend && python scripts/run_mock_ocr_server.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.services.ocr_provider as ocr_provider

# 识别文本：张三 第 1 题答 B（参考答案 B → 对），第 2 题答 NaCl（参考答案 H2O → 错）
MOCK_TEXT = "姓名: 张三\n学号: 20250001\n1. B\n2. NaCl\n"


class MockOCRProvider:
    """mock OCR：返回固定识别文本与高置信度"""

    def recognize_with_confidence(self, file_path: str) -> tuple[str, float]:
        return MOCK_TEXT, 0.95


# 在导入 app.main 之前打桩（先于 grading.py / ocr.py 的 from-import 生效）
ocr_provider.is_ocr_configured = lambda: True
ocr_provider.get_ocr_provider = lambda: MockOCRProvider()

import uvicorn  # noqa: E402
from app.main import app  # noqa: E402


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
