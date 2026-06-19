# Chào mừng các bạn đến với Giai đoạn 2, Track 3, Day 17: Memory Systems for AI Agent

Trong Day 17 này, các bạn sẽ tập trung vào một câu hỏi rất thực tế: làm sao để AI agent **không chỉ trả lời tốt trong một lượt chat**, mà còn **nhớ đúng thông tin quan trọng qua nhiều phiên làm việc** mà vẫn kiểm soát được chi phí token.

Trong bài lab này, các bạn sẽ xây dựng và so sánh hai agent:

- `Baseline Agent`: chỉ có short-term memory trong cùng một thread
- `Advanced Agent`: có short-term memory, `User.md` bền vững, và compact memory để nén hội thoại dài

Mục tiêu cuối cùng không phải chỉ là “agent nhớ nhiều hơn”, mà là hiểu rõ trade-off giữa:

- độ nhớ dài hạn
- chất lượng phản hồi
- chi phí token
- độ phức tạp của hệ thống memory

## Các bạn sẽ làm gì trong track này?

Sau khi hoàn thành, các bạn cần có khả năng:

- phân biệt `short-term memory`, `persistent memory`, và `compact memory`
- xây dựng agent baseline và advanced trên cùng một benchmark
- lưu hồ sơ người dùng bằng `User.md`
- kích hoạt compact memory khi hội thoại dài vượt ngưỡng
- benchmark hai agent bằng cùng một bộ dữ liệu tiếng Việt
- đọc kết quả benchmark theo các chỉ số recall, token, memory growth, chất lượng phản hồi

## Cấu trúc codebase

Repo này được chia thành ba phần rõ ràng:

- `src/`: bản scaffold dành cho sinh viên, chứa pseudocode và TODO để hoàn thiện
- `data/`: dữ liệu benchmark ở root để dùng cho cả benchmark chuẩn và stress benchmark

## Provider hỗ trợ

Trong bản solved lab, runtime hỗ trợ các provider sau:

- `openai`
- `custom` (OpenAI-compatible base URL)
- `gemini`
- `anthropic`
- `ollama`
- `openrouter`

Điều này quan trọng vì memory system không nên bị khóa vào một provider duy nhất.

## Chỉ số benchmark cần hiểu

Khi hoàn thiện bài, benchmark nên cho các cột sau:

- `Agent tokens only`: token sinh ra trực tiếp trong hội thoại của agent
- `Prompt tokens processed`: lượng ngữ cảnh agent phải kéo theo qua các lượt
- `Cross-session recall`: khả năng nhớ facts qua thread hoặc session mới
- `Response quality`: chất lượng phản hồi
- `Memory growth (bytes)`: tốc độ phình của file memory
- `Compactions`: số lần compact memory đã nén lịch sử cũ

Điểm quan trọng nhất của track này là:

- ở hội thoại ngắn, `Advanced` có thể tốn hơn `Baseline` về token usage
- ở hội thoại rất dài, compact memory nên giúp `Advanced` xử lý ngữ cảnh hiệu quả hơn đáng kể + tiết kiệm usage.

## Cách dùng repo này

## Setup môi trường

Các bạn cần chuẩn bị môi trường Python `>= 3.11` và cài các package cần thiết cho LangChain, LangGraph, provider SDK, `python-dotenv`, `tabulate`, và `pytest`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install langchain langgraph langchain-openai langchain-google-genai langchain-anthropic langchain-ollama langchain-openrouter python-dotenv tabulate pytest
```

Sau đó làm việc trực tiếp với `src/` và `data/` ở root repo.

Nếu các bạn là sinh viên:

- làm bài trong `src/`
- dùng `data/` làm benchmark input

Nếu các bạn là giảng viên hoặc reviewer:

- dùng `src/` để đánh giá scaffold giao cho sinh viên và kết quả hoàn thiện cuối cùng

## Trạng thái triển khai

Repo đã hoàn thiện cả hai agent, benchmark và test. Chế độ offline deterministic
được dùng mặc định khi không có credential, nhờ đó kết quả chấm có thể tái lập.

Chạy toàn bộ kiểm chứng:

```bash
pytest -q
python src/benchmark.py
```

Chạy website showcase để thuyết trình:

```bash
python -m http.server 8080
```

Mở `http://localhost:8080/web/`. Website có benchmark tương tác, mô phỏng
correction trong `User.md`, kiến trúc ba lớp, evaluator mode bám sát rubric và
presentation mode toàn màn hình. Evidence map chi tiết nằm tại
`web/RUBRIC_EVIDENCE.md`; phần phân tích 10 câu hỏi nằm tại `ANALYSIS.md`.

Kết quả offline tham chiếu trên dataset đi kèm:

| Suite | Agent | Prompt tokens processed | Cross-session recall | Compactions |
|---|---|---:|---:|---:|
| Standard | Baseline | 12,852 | 0.036 | 0 |
| Standard | Advanced | 23,699 | 1.000 | 0 |
| Stress | Baseline | 21,718 | 0.000 | 0 |
| Stress | Advanced | 15,362 | 1.000 | 7 |

Các số trên minh họa đúng trade-off:

- Hội thoại ngắn: Advanced có overhead vì luôn nạp `User.md`; compact chưa kích
  hoạt nên không nhất thiết rẻ hơn Baseline.
- Hội thoại dài: Baseline xử lý lại toàn bộ lịch sử mỗi lượt, còn Advanced giữ
  summary bị chặn kích thước và một cửa sổ message gần nhất. Lợi ích chính nằm ở
  `Prompt tokens processed`, không phải số token agent sinh ra.
- Persistent memory tăng recall qua session nhưng file có thể phình theo số field.
  Bản này dùng structured upsert để mỗi field chỉ có một giá trị hiện hành.

## Bonus và guardrail

- **Confidence threshold:** chỉ các câu khẳng định khớp pattern rõ ràng mới được
  ghi; câu hỏi, câu đùa, địa điểm công tác tạm thời và phủ định bị bỏ qua.
- **Entity extraction:** profile lưu theo field (`name`, `location`,
  `profession`, `response_style`, ...), dễ đọc và dễ kiểm thử.
- **Conflict handling:** correction thay thế giá trị cũ, nên `backend engineer`
  không tồn tại song song với `MLOps engineer`.
- **Bounded summary:** compact summary có giới hạn kích thước để tránh chuyển
  vấn đề tăng trưởng từ raw history sang summary.

Rủi ro còn lại là regex có thể bỏ sót cách diễn đạt mới hoặc ghi nhầm một câu
khẳng định mơ hồ. Production system nên bổ sung schema validation, provenance,
timestamp/decay và bước xác nhận khi confidence ở vùng trung gian.

## Tài liệu nên đọc tiếp

- `Guide.md`: hướng dẫn từng bước để hoàn thành lab
- `Rubric.md`: tiêu chí chấm điểm và bonus

Track này được thiết kế để các bạn không chỉ “dùng agent”, mà còn bắt đầu nghĩ như một người thiết kế **memory system** cho agent production.
