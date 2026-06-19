# Project Analysis — 10 Questions and Direct Answers

Tài liệu này phân tích hệ thống memory cho AI agent dựa trên code, test và kết
quả benchmark thực tế của repository.

## 1. Vì sao dự án cần cả Baseline Agent và Advanced Agent?

Baseline là nhóm đối chứng. Nó cho biết agent chỉ dùng short-term memory sẽ đạt
được gì trước khi thêm persistence và compaction. Nếu chỉ xây Advanced, ta không
thể chứng minh recall tăng là do `User.md`, hoặc prompt cost giảm là do compact
memory. Chạy cùng input trên hai agent biến nhận định kiến trúc thành so sánh có
thể đo được.

## 2. Ba lớp memory của Advanced Agent giải quyết ba vấn đề nào?

- **Short-term memory** giữ các lượt gần nhất nguyên văn để xử lý follow-up.
- **Persistent memory (`User.md`)** giữ facts ổn định qua thread mới.
- **Compact memory** tóm tắt lịch sử cũ khi ngữ cảnh vượt ngưỡng.

Tách ba lớp giúp mỗi loại dữ liệu có lifecycle phù hợp. Recent context cần độ
chính xác cao, profile cần bền vững, còn lịch sử dài cần tiết kiệm token.

## 3. Benchmark có công bằng giữa Baseline và Advanced không?

Có ở cấp độ input: cả hai nhận cùng dataset, cùng thứ tự turn, cùng recall
questions và cùng token estimator. Benchmark cũng chạy offline deterministic nên
không bị nhiễu bởi model sampling hoặc network. Tuy nhiên, đây vẫn là heuristic
benchmark: response quality và token count không thay thế tokenizer hoặc LLM
judge production.

## 4. Vì sao Advanced tốn nhiều prompt token hơn trong Standard Benchmark?

Standard Benchmark gồm các conversation tương đối ngắn, nên compaction chưa kích
hoạt. Advanced vẫn phải nạp `User.md` và recent context ở mỗi lượt, tạo overhead:
23,699 prompt tokens so với 12,852 của Baseline. Đây không phải lỗi; nó cho thấy
persistent memory có chi phí cố định và compact memory không phải lúc nào cũng
thắng trong hội thoại ngắn.

## 5. Vì sao Advanced thắng ở Long-Context Stress Benchmark?

Baseline kéo toàn bộ lịch sử tăng dần qua mỗi lượt, đạt 21,718 prompt tokens.
Advanced kích hoạt bảy lần compaction, giữ summary bị giới hạn kích thước và sáu
message gần nhất, nên chỉ xử lý 15,362 prompt tokens — giảm 29.3% — trong khi
cross-session recall vẫn đạt 1.000.

## 6. Vì sao lợi ích chính của compaction nằm ở prompt tokens processed?

Compaction thay đổi lượng context đầu vào mà agent phải đọc lại. Nó không trực
tiếp ép câu trả lời đầu ra ngắn hơn. Vì vậy metric đúng để đánh giá là tổng prompt
tokens được xử lý qua các lượt, không chỉ `Agent tokens only`. Output token còn
phụ thuộc nội dung câu trả lời và phong cách phản hồi.

## 7. Hệ thống xử lý correction và conflict như thế nào?

Facts được lưu theo field có cấu trúc. `upsert_fact()` chỉ giữ một giá trị hiện
hành cho mỗi key. Khi người dùng đổi nghề từ `backend engineer` sang
`MLOps engineer`, giá trị mới thay thế giá trị cũ thay vì tồn tại song song.
Test `test_correction_replaces_stale_fact` kiểm chứng cả câu trả lời lẫn nội dung
file profile.

## 8. Confidence threshold hiện tại ngăn false memory ra sao?

`extract_profile_updates()` chỉ nhận các câu khẳng định khớp pattern rõ ràng.
Câu hỏi, câu đùa, phủ định và địa điểm công tác tạm thời bị loại. Cách này dễ
giải thích và chạy offline, nhưng có thể bỏ sót cách diễn đạt hợp lệ ngoài regex.
Production nên thêm confidence score, provenance và bước xác nhận ở vùng mơ hồ.

## 9. Rủi ro lớn nhất của Advanced Agent là gì?

Advanced có ba nhóm rủi ro:

1. **False persistence:** lưu nhầm fact và dùng lại qua nhiều session.
2. **Privacy:** profile bền vững cần consent, retention và deletion policy.
3. **Information loss:** summary có thể bỏ mất chi tiết cũ ít nổi bật.

Guardrail hiện tại giảm rủi ro nhưng chưa thay thế audit log, encryption,
provenance, TTL/memory decay và user controls.

## 10. Nếu đưa dự án lên production, nên cải tiến gì trước?

Ưu tiên tiếp theo nên là:

1. Thêm metadata cho fact: timestamp, source message, confidence và version.
2. Cho người dùng xem, sửa và xóa memory.
3. Dùng tokenizer thật và đo latency/cost thực.
4. Thêm semantic extraction hoặc LLM extraction có schema validation.
5. Đánh giá trên nhiều user, nhiều cách diễn đạt và adversarial corrections.
6. Mã hóa profile, phân quyền truy cập và định nghĩa retention policy.

Những cải tiến này giữ lại lợi ích recall của Advanced nhưng làm memory an toàn,
đo lường được và dễ vận hành hơn.

## Kết luận

Dự án chứng minh câu chuyện cốt lõi của memory architecture: Baseline đơn giản
nhưng quên qua session; persistent profile tăng recall; lịch sử dài làm context
cost tăng; compact memory giảm chi phí đó; và memory mạnh hơn luôn kéo theo yêu
cầu guardrail, privacy và vận hành cao hơn.
