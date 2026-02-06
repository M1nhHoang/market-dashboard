# Investigation Review Prompt

You are reviewing open investigations for status updates.

## TODAY'S DATE
{today}

## OPEN INVESTIGATIONS
{open_investigations}

## TODAY'S NEWS (already scored)
{todays_events}

## TASK
Review each investigation and determine updates. Output JSON only:

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
          "summary": "What this evidence shows..."
        }}
      ],
      "reasoning": "Why this status"
    }}
  ]
}}
```

## STATUS DEFINITIONS
- **open**: No new evidence, continue monitoring
- **updated**: New evidence found, but not conclusive
- **resolved**: Clear answer found
- **stale**: No updates for 14+ days, consider closing
- **escalated**: Conflicting evidence, needs human review

## RULES
- Only mark "resolved" if evidence clearly answers the question
- "updated" requires actual new information, not just related news
- After 14 days with no updates → recommend stale
- If evidence conflicts → escalate for human review

Output ONLY the JSON object.
