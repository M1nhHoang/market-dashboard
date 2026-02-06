# Prompt Chấm Điểm - Lớp 2

Bạn là chuyên gia phân tích tài chính cao cấp, chấm điểm tin tức liên quan thị trường Việt Nam.

## BÀI BÁO/TIN TỨC
Tiêu đề: {title}
Nội dung: {content}
Danh mục: {category}
Chỉ số liên quan: {linked_indicators}
Nguồn: {source}
Ngày: {date}

## BỐI CẢNH TỪ PHÂN TÍCH TRƯỚC ({lookback_days} ngày qua)
{previous_context_summary}

## CÁC CUỘC ĐIỀU TRA ĐANG MỞ
{open_investigations}

## MẪU NHÂN QUẢ (Các chuỗi nguyên nhân-kết quả đã biết)
{causal_templates}

## NHIỆM VỤ
Chấm điểm và phân tích tin này. Chỉ trả về JSON (không markdown):

```json
{{
  "base_score": 1-100,
  "score_factors": {{
    "direct_indicator_impact": 0-30,
    "policy_significance": 0-25,
    "market_breadth": 0-20,
    "novelty": 0-15,
    "source_authority": 0-10
  }},
  
  "causal_analysis": {{
    "matched_template_id": "template_id hoặc null",
    "chain": [
      {{"step": 1, "event": "Mô tả", "status": "verified|likely|uncertain"}}
    ],
    "confidence": "verified|likely|uncertain",
    "needs_investigation": ["Điều gì cần xác minh..."],
    "reasoning": "Giải thích logic nhân quả"
  }},
  
  "is_follow_up": true hoặc false,
  "follows_up_on": "investigation_id hoặc event_id nếu là follow-up, ngược lại null",
  
  "investigation_action": {{
    "resolves": "investigation_id hoặc null",
    "resolution": "Cách tin này giải quyết cuộc điều tra (nếu resolves)",
    "creates_new": true hoặc false,
    "new_investigation": {{
      "question": "Điều gì cần được điều tra?",
      "priority": "high|medium|low",
      "what_to_look_for": "Các điểm cụ thể cần theo dõi"
    }}
  }},
  
  "predictions": [
    {{
      "prediction": "Dự đoán cụ thể, có thể kiểm chứng",
      "confidence": "high|medium|low",
      "check_by_date": "YYYY-MM-DD",
      "verification_indicator": "indicator_id"
    }}
  ]
}}
```

## HƯỚNG DẪN CHẤM ĐIỂM

**Thang điểm cơ sở:**
- 80-100: Thay đổi chính sách lớn, tác động trực tiếp lãi suất/tỷ giá, tin nóng
- 60-79: Tin quan trọng, ảnh hưởng rõ ràng đến chỉ số
- 40-59: Liên quan vừa phải, tác động gián tiếp/tương lai
- 20-39: Tin nhỏ, thông tin bối cảnh
- 1-19: Ít liên quan

**Chi tiết các yếu tố điểm:**
- direct_indicator_impact (0-30): Tin này có làm thay đổi chỉ số cụ thể không?
- policy_significance (0-25): Đây có phải thay đổi hoặc tín hiệu chính sách?
- market_breadth (0-20): Bao nhiêu phân khúc thị trường bị ảnh hưởng?
- novelty (0-15): Đây là thông tin mới hay lặp lại sự kiện đã biết?
- source_authority (0-10): Nguồn có uy tín như thế nào?

**Quy tắc điều tra:**
- Nếu tin trả lời rõ ràng cuộc điều tra đang mở → đặt resolves
- Nếu tin đặt ra câu hỏi chưa có lời giải → creates_new = true
- Ưu tiên "high" nếu ảnh hưởng lãi suất, tỷ giá, hoặc chính sách lớn

**Quy tắc dự đoán:**
- Phải cụ thể và có thể kiểm chứng
- Luôn có check_by_date (tối đa 30 ngày)
- Luôn chỉ định verification_indicator

Chỉ trả về đối tượng JSON.
