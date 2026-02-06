# Prompt Rà Soát Điều Tra

Bạn đang rà soát các cuộc điều tra còn mở để cập nhật trạng thái.

## NGÀY HÔM NAY
{today}

## CÁC CUỘC ĐIỀU TRA ĐANG MỞ
{open_investigations}

## TIN TỨC HÔM NAY (đã được chấm điểm)
{todays_events}

## NHIỆM VỤ
Rà soát từng cuộc điều tra và xác định cập nhật. Chỉ trả về JSON:

```json
{{
  "investigation_updates": [
    {{
      "investigation_id": "inv_xxx",
      "previous_status": "open",
      "new_status": "open|updated|resolved|stale",
      "evidence_today": [
        {{
          "event_id": "evt_xxx",
          "evidence_type": "supports|contradicts|neutral",
          "summary": "Bằng chứng này cho thấy..."
        }}
      ],
      "reasoning": "Lý do trạng thái này"
    }}
  ]
}}
```

## ĐỊNH NGHĨA TRẠNG THÁI
- **open**: Chưa có bằng chứng mới, tiếp tục theo dõi
- **updated**: Tìm thấy bằng chứng mới, nhưng chưa đủ kết luận
- **resolved**: Đã tìm được câu trả lời rõ ràng
- **stale**: Không có cập nhật trên 14 ngày, xem xét đóng
- **escalated**: Bằng chứng mâu thuẫn, cần con người xem xét

## QUY TẮC
- Chỉ đánh dấu "resolved" nếu bằng chứng trả lời rõ ràng câu hỏi
- "updated" yêu cầu thông tin mới thực sự, không chỉ là tin liên quan
- Sau 14 ngày không có cập nhật → đề xuất stale
- Nếu bằng chứng mâu thuẫn → escalate để con người xem xét

Chỉ trả về đối tượng JSON.
