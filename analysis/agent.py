"""AI Agent vòng lặp — nhận câu hỏi bằng tiếng Việt, tự chọn tool, trả lời.

Flow mỗi lượt:
  1. Người dùng gõ câu hỏi
  2. Gửi lên Gemini kèm danh sách tool
  3. Gemini quyết định gọi tool nào (hoặc trả lời trực tiếp)
  4. Chạy tool, trả kết quả về cho Gemini
  5. Gemini tổng hợp câu trả lời cuối cùng
"""

import logging

from google import genai
from google.genai import types

from config import settings
from analysis.tools import TOOL_SCHEMAS, execute_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là FinAgent — trợ lý phân tích tài chính chứng khoán Việt Nam.
Bạn có dữ liệu lịch sử giá của 11 mã: VNM, HPG, FPT, MWG, VCB, TCB, VHM, GAS, VIC, VIX, VNINDEX.
Và 4 chỉ số vĩ mô: USDVND (tỷ giá), GC (vàng), CL (dầu WTI), GSPC (S&P 500).

Nguyên tắc:
- Luôn dùng tool để lấy số liệu thật trước khi trả lời, không đoán mò.
- Trích dẫn số liệu cụ thể (giá, %, ngày tháng) trong câu trả lời.
- Trả lời bằng tiếng Việt, ngắn gọn và rõ ràng.
- Nếu không có dữ liệu, nói thẳng thay vì bịa số.
- Không đưa ra lời khuyên đầu tư trực tiếp — chỉ phân tích khách quan."""

MAX_TOOL_ROUNDS = 5

_TYPE_MAP = {
    "string":  "STRING",
    "integer": "INTEGER",
    "number":  "NUMBER",
    "boolean": "BOOLEAN",
    "array":   "ARRAY",
    "object":  "OBJECT",
}


def _build_schema(prop: dict) -> types.Schema:
    t = _TYPE_MAP.get(prop.get("type", "string"), "STRING")
    kwargs = {"type": t, "description": prop.get("description", "")}
    if t == "ARRAY" and "items" in prop:
        kwargs["items"] = _build_schema(prop["items"])
    return types.Schema(**kwargs)


def _build_gemini_tools() -> list[types.Tool]:
    declarations = []
    for schema in TOOL_SCHEMAS:
        props    = schema["input_schema"].get("properties", {})
        required = schema["input_schema"].get("required", [])
        declarations.append(
            types.FunctionDeclaration(
                name=schema["name"],
                description=schema["description"],
                parameters=types.Schema(
                    type="OBJECT",
                    properties={k: _build_schema(v) for k, v in props.items()},
                    required=required,
                ),
            )
        )
    return [types.Tool(function_declarations=declarations)]


class FinAgent:
    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._tools  = _build_gemini_tools()
        self._config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=self._tools,
            max_output_tokens=4096,
        )
        self._history: list[types.Content] = []

    def chat(self, user_message: str) -> str:
        self._history.append(
            types.Content(role="user", parts=[types.Part(text=user_message)])
        )

        for _ in range(MAX_TOOL_ROUNDS):
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=self._history,
                config=self._config,
            )

            candidate = response.candidates[0]
            self._history.append(candidate.content)

            # Collect function calls from response parts
            fn_calls = [
                p.function_call
                for p in candidate.content.parts
                if p.function_call and p.function_call.name
            ]

            if not fn_calls:
                return "".join(
                    p.text for p in candidate.content.parts if p.text
                )

            # Execute tools and build result parts
            result_parts = []
            for fc in fn_calls:
                logger.info(f"→ Tool: {fc.name}({dict(fc.args)})")
                result = execute_tool(fc.name, dict(fc.args))
                logger.info(f"← Kết quả: {str(result)[:100]}...")
                result_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result},
                        )
                    )
                )

            self._history.append(
                types.Content(role="user", parts=result_parts)
            )

        return "Xin lỗi, tôi không thể hoàn thành yêu cầu sau nhiều lần thử."

    def reset(self):
        self._history = []
        print("Đã xoá lịch sử hội thoại.")
