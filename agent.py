"""
FinAgent — AI Chatbot phân tích chứng khoán Việt Nam

Hỗ trợ BẤT KỲ mã cổ phiếu nào trên HOSE, HNX, UPCoM.
Với mã chưa có cache, agent tự tải dữ liệu từ vnstock rồi phân tích.

Chạy:
    python agent.py

Ví dụ câu hỏi:
    > Giá VNM hôm nay là bao nhiêu?
    > Phân tích HPG trong 3 tháng gần đây
    > So sánh VNM, HPG và FPT
    > Mã nào tăng mạnh nhất tháng này?
    > Vẽ biểu đồ Bollinger cho GAS
    > Phân tích ACB          (mã chưa có cache — tự tải)
    > Cho tôi xem giá SSI    (tự tải nếu chưa có)
    > reset  (xoá lịch sử, bắt đầu lại)
    > quit   (thoát)
"""

import logging
import sys
import warnings

warnings.filterwarnings("ignore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Kiểm tra API key trước khi khởi động
from config import settings
if not settings.groq_api_key:
    print("❌ Chưa có GROQ_API_KEY trong file .env")
    print("   Tạo file .env và thêm dòng: GROQ_API_KEY=your_key_here")
    print("   Lấy key miễn phí tại: https://console.groq.com")
    sys.exit(1)

from analysis.agent import FinAgent

BANNER = """
╔══════════════════════════════════════════════════════╗
║          FinAgent — Phân tích Chứng khoán VN         ║
║  Gõ câu hỏi bằng tiếng Việt. 'quit' để thoát.       ║
╚══════════════════════════════════════════════════════╝
"""

EXAMPLES = """Ví dụ:
  Giá VNM hôm nay?
  Phân tích HPG 3 tháng gần đây
  So sánh VNM, HPG, FPT
  Mã nào tăng mạnh nhất tháng này?
  Vẽ biểu đồ Bollinger cho GAS
"""


def main():
    print(BANNER)
    print(EXAMPLES)

    agent = FinAgent()

    while True:
        try:
            user_input = input("Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTạm biệt!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "thoát"):
            print("Tạm biệt!")
            break
        if user_input.lower() == "reset":
            agent.reset()
            continue

        print("FinAgent: ", end="", flush=True)
        response = agent.chat(user_input)
        print(response)
        print()


if __name__ == "__main__":
    main()
