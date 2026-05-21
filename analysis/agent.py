"""AI Agent vòng lặp — nhận câu hỏi bằng tiếng Việt, tự chọn tool, trả lời.

Flow mỗi lượt:
  1. Người dùng gõ câu hỏi
  2. Gửi lên Groq (LLaMA 3.3 70B) kèm danh sách tool
  3. Model quyết định gọi tool nào (hoặc trả lời trực tiếp)
  4. Chạy tool, trả kết quả về cho model
  5. Model tổng hợp câu trả lời cuối cùng
"""

import json
import logging

from groq import Groq

from config import settings
from analysis.tools import TOOL_SCHEMAS, execute_tool

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"
MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = """Bạn là FinAgent — trợ lý phân tích tài chính chứng khoán Việt Nam.
Bạn có dữ liệu lịch sử giá của 11 mã: VNM, HPG, FPT, MWG, VCB, TCB, VHM, GAS, VIC, VIX, VNINDEX.
Và 4 chỉ số vĩ mô: USDVND (tỷ giá), GC (vàng), CL (dầu WTI), GSPC (S&P 500).

Nguyên tắc:
- Luôn dùng tool để lấy số liệu thật trước khi trả lời, không đoán mò.
- Trích dẫn số liệu cụ thể (giá, %, ngày tháng) trong câu trả lời.
- Trả lời bằng tiếng Việt, ngắn gọn và rõ ràng.
- Nếu không có dữ liệu, nói thẳng thay vì bịa số.
- Không đưa ra lời khuyên đầu tư trực tiếp — chỉ phân tích khách quan."""


def _build_openai_tools() -> list[dict]:
    """Chuyển TOOL_SCHEMAS (Anthropic format) → OpenAI/Groq format."""
    return [
        {
            "type": "function",
            "function": {
                "name": s["name"],
                "description": s["description"],
                "parameters": s["input_schema"],
            },
        }
        for s in TOOL_SCHEMAS
    ]


class FinAgent:
    def __init__(self):
        self._client = Groq(api_key=settings.groq_api_key)
        self._tools  = _build_openai_tools()
        self._history: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def chat(self, user_message: str) -> str:
        self._history.append({"role": "user", "content": user_message})

        for _ in range(MAX_TOOL_ROUNDS):
            response = self._client.chat.completions.create(
                model=MODEL,
                messages=self._history,
                tools=self._tools,
                tool_choice="auto",
                max_tokens=4096,
            )

            msg = response.choices[0].message
            self._history.append(msg)

            # Không có tool call → trả lời thẳng
            if not msg.tool_calls:
                return msg.content or ""

            # Thực thi các tool calls
            for tc in msg.tool_calls:
                logger.info(f"→ Tool: {tc.function.name}({tc.function.arguments[:80]})")
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                result = execute_tool(tc.function.name, args)
                logger.info(f"← Kết quả: {str(result)[:100]}...")
                self._history.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      result,
                })

        return "Xin lỗi, tôi không thể hoàn thành yêu cầu sau nhiều lần thử."

    def reset(self):
        self._history = [{"role": "system", "content": SYSTEM_PROMPT}]
        print("Đã xoá lịch sử hội thoại.")
