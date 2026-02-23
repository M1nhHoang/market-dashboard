# Narrative Synthesis Prompt

Tổng hợp các signals của một trend thành narrative ngắn gọn.

## BỐI CẢNH

### Theme
- Tên: {theme_name}
- Mô tả: {theme_description}
- First seen: {first_seen}
- Strength: {strength}

### Active Signals ({signals_count} predictions)
{signals_section}

### Related Indicators (current values)
{indicators_section}

## TASK

Tổng hợp thành **narrative ngắn gọn** (3-5 câu) theo cấu trúc:

1. **Opening:** Mô tả xu hướng chính đang diễn ra
2. **Causation:** Giải thích nguyên nhân (tổng hợp từ reasoning)
3. **Implication:** Hệ quả tiềm năng và điều cần theo dõi
4. **Timeline:** Khi nào cần chú ý (dựa vào expires_at gần nhất)

## EXAMPLE OUTPUT

"Thanh khoản hệ thống ngân hàng đang chịu áp lực đáng kể khi giải ngân đầu tư công tăng mạnh, rút vốn từ các ngân hàng thương mại. SBV đã phản ứng bằng cách bơm ròng hơn 80,000 tỷ qua OMO, nhưng lãi suất liên ngân hàng qua đêm vẫn neo ở mức cao 9.12%. Nếu xu hướng tiếp tục, các ngân hàng có thể buộc phải tăng lãi suất huy động trong 1-2 tuần tới để bù đắp chi phí vốn."

## OUTPUT

Chỉ trả về narrative text thuần túy, không có JSON hay format đặc biệt.
