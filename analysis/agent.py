"""AI Agent vòng lặp — nhận câu hỏi bằng tiếng Việt, tự chọn tool, trả lời.

Flow mỗi lượt:
  1. Người dùng gõ câu hỏi
  2. Gửi lên Claude kèm danh sách tool
  3. Claude quyết định gọi tool nào (hoặc trả lời trực tiếp)
  4. Chạy tool, trả kết quả về cho Claude
  5. Claude tổng hợp câu trả lời cuối cùng
"""

import logging

import anthropic

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

MAX_TOOL_ROUNDS = 5   # Tránh vòng lặp vô hạn


class FinAgent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model  = "claude-opus-4-7"
        self.history: list[dict] = []   # Lưu lịch sử hội thoại

    def chat(self, user_message: str) -> str:
        """Gửi tin nhắn và nhận câu trả lời từ agent."""
        self.history.append({"role": "user", "content": user_message})

        for round_num in range(MAX_TOOL_ROUNDS):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=self.history,
            )

            # Nếu Claude trả lời thẳng (không gọi tool)
            if response.stop_reason == "end_turn":
                answer = response.content[0].text
                self.history.append({"role": "assistant", "content": answer})
                return answer

            # Claude muốn gọi tool
            if response.stop_reason == "tool_use":
                # Thêm response của Claude vào history
                self.history.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Chạy tất cả tool Claude yêu cầu
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    logger.info(f"→ Tool: {block.name}({block.input})")
                    result = execute_tool(block.name, block.input)
                    logger.info(f"← Kết quả: {result[:100]}...")
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     result,
                    })

                # Đưa kết quả tool vào history để Claude xử lý tiếp
                self.history.append({
                    "role":    "user",
                    "content": tool_results,
                })

        return "Xin lỗi, tôi không thể hoàn thành yêu cầu sau nhiều lần thử."

    def reset(self):
        """Xoá lịch sử hội thoại, bắt đầu cuộc trò chuyện mới."""
        self.history = []
        print("Đã xoá lịch sử hội thoại.")
