"""
API Routes - All endpoint definitions for Market Intelligence Dashboard

Endpoints organized by:
- Health Check
- Indicators (current values and history)
- Events (key events, other news, archive)
- Signals (predictions with targets) - LEGACY, use /trends for dashboard
- Themes (narrative groupings) - LEGACY, use /trends for dashboard
- Trends (UNIFIED: Themes + Signals combined view) - NEW
- Watchlist (user-defined alerts)
- Topics (hot topics)
- Calendar (economic events)
- System (runs, refresh)

## TREND SYSTEM (migration 005_trends_system)
The /trends endpoints provide a unified view combining themes and signals.
Frontend should use /trends for the main dashboard, while /themes and /signals
remain available for backward compatibility.
"""
import json
import math
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from config import settings
from database import get_connection, INDICATOR_GROUPS

router = APIRouter()


# ============================================================
# Health Check
# ============================================================
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": str(settings.DATABASE_PATH)
    }


# ============================================================
# Indicators
# ============================================================
@router.get("/indicators")
async def list_indicators(
    category: Optional[str] = None,
    grouped: bool = Query(default=True, description="Group indicators by category")
):
    """
    List all indicators.
    
    If grouped=True, returns indicators organized by category groups.
    """
    conn = get_connection(settings.DATABASE_PATH)
    
    if category:
        cursor = conn.execute(
            "SELECT * FROM indicators WHERE category = ? ORDER BY name",
            (category,)
        )
    else:
        cursor = conn.execute("SELECT * FROM indicators ORDER BY category, name")
    
    rows = cursor.fetchall()
    conn.close()
    
    indicators = [dict(row) for row in rows]
    
    # Parse attributes JSON for indicators that have it
    import json as _json
    for ind in indicators:
        if ind.get('attributes'):
            try:
                ind['attributes'] = _json.loads(ind['attributes'])
            except (ValueError, TypeError):
                pass
    
    if grouped and not category:
        # Group by category
        grouped_data = {}
        for group_id, group_info in INDICATOR_GROUPS.items():
            group_result = {
                "display_name": group_info["display_name"],
                "indicators": [
                    ind for ind in indicators 
                    if ind.get('category') == group_id or ind.get('id') in group_info.get("indicators", [])
                ]
            }
            # Pass expandable metadata for gold group
            if group_info.get("expandable"):
                group_result["expandable"] = True
                group_result["primary_indicators"] = group_info.get("primary_indicators", [])
            grouped_data[group_id] = group_result
        return {"groups": grouped_data, "total": len(indicators)}
    
    return {"indicators": indicators}


@router.get("/indicators/{indicator_id}")
async def get_indicator(indicator_id: str):
    """Get single indicator with recent history."""
    conn = get_connection(settings.DATABASE_PATH)
    
    # Get current value
    cursor = conn.execute("SELECT * FROM indicators WHERE id = ?", (indicator_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Indicator not found")
    
    result = dict(row)
    
    # Get recent history (last 30 records)
    cursor = conn.execute(
        """SELECT * FROM indicator_history 
           WHERE indicator_id = ? 
           ORDER BY date DESC 
           LIMIT 30""",
        (indicator_id,)
    )
    history = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    result["history"] = history
    return result


@router.get("/indicators/{indicator_id}/history")
async def get_indicator_history(
    indicator_id: str,
    days: int = Query(default=30, le=365, description="Number of days of history")
):
    """Get indicator history for charts."""
    conn = get_connection(settings.DATABASE_PATH)
    
    cursor = conn.execute(
        """SELECT * FROM indicator_history 
           WHERE indicator_id = ? 
           ORDER BY date DESC 
           LIMIT ?""",
        (indicator_id, days)
    )
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail="No history found")
    
    return {
        "indicator_id": indicator_id,
        "history": [dict(row) for row in rows],
        "count": len(rows)
    }


@router.get("/indicators/category/{category}")
async def list_indicators_by_category(category: str):
    """List indicators by category (vietnam_monetary, vietnam_forex, etc)."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        "SELECT * FROM indicators WHERE category = ? ORDER BY name",
        (category,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"indicators": [dict(row) for row in rows], "category": category}
    
    return {"indicators": [dict(row) for row in rows]}


@router.get("/indicators/{indicator_id}")
async def get_indicator(indicator_id: str):
    """Get single indicator by ID."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute("SELECT * FROM indicators WHERE id = ?", (indicator_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Indicator not found")
    
    return dict(row)


@router.get("/indicators/region/{region}")
async def list_indicators_by_region(
    region: str,
    limit: int = Query(default=50, le=200)
):
    """List indicators by region (vietnam/global)."""
    category_prefix = "vietnam" if region == "vietnam" else "global"
    
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        "SELECT * FROM indicators WHERE category LIKE ? ORDER BY updated_at DESC LIMIT ?",
        (f"{category_prefix}%", limit)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"indicators": [dict(row) for row in rows]}


# ============================================================
# Events
# ============================================================
@router.get("/events")
async def list_events(
    category: Optional[str] = None,
    region: Optional[str] = None,
    display_section: Optional[str] = Query(default=None, description="key_events, other_news, archive"),
    limit: int = Query(default=50, le=200),
    offset: int = 0
):
    """List events with optional filters."""
    conn = get_connection(settings.DATABASE_PATH)
    
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    
    if category:
        query += " AND category = ?"
        params.append(category)
    if region:
        query += " AND region = ?"
        params.append(region)
    if display_section:
        query += " AND display_section = ?"
        params.append(display_section)
    
    query += " ORDER BY current_score DESC, published_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return {
        "events": [dict(row) for row in rows],
        "limit": limit,
        "offset": offset
    }


@router.get("/events/key")
async def get_key_events():
    """Get key events (high-scoring, market-moving)."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        """SELECT * FROM events 
           WHERE display_section = 'key_events' 
           ORDER BY current_score DESC 
           LIMIT 15"""
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"events": [dict(row) for row in rows]}


@router.get("/events/other")
async def get_other_news(
    limit: int = Query(default=30, le=100),
    offset: int = 0
):
    """Get other news (sorted by date, newest first)."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        """SELECT * FROM events 
           WHERE display_section = 'other_news' 
           ORDER BY published_at DESC 
           LIMIT ? OFFSET ?""",
        (limit, offset)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"events": [dict(row) for row in rows], "limit": limit, "offset": offset}


@router.get("/events/today")
async def get_today_events():
    """Get today's events only."""
    today = date.today().isoformat()
    
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        "SELECT * FROM events WHERE run_date = ? ORDER BY current_score DESC",
        (today,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"events": [dict(row) for row in rows], "date": today}


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get single event with full analysis."""
    conn = get_connection(settings.DATABASE_PATH)
    
    # Get event
    cursor = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    
    if not event:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")
    
    result = dict(event)
    
    # Parse JSON fields
    if result.get('linked_indicators'):
        try:
            result['linked_indicators'] = json.loads(result['linked_indicators'])
        except:
            pass
    if result.get('score_factors'):
        try:
            result['score_factors'] = json.loads(result['score_factors'])
        except:
            pass
    
    # Get causal analysis
    cursor = conn.execute(
        "SELECT * FROM causal_analyses WHERE event_id = ?",
        (event_id,)
    )
    analysis = cursor.fetchone()
    if analysis:
        analysis_dict = dict(analysis)
        # Parse JSON fields in analysis
        for field in ['chain_steps', 'affected_indicators']:
            if analysis_dict.get(field):
                try:
                    analysis_dict[field] = json.loads(analysis_dict[field])
                except:
                    pass
        result["causal_analysis"] = analysis_dict
    
    # Get related signals
    cursor = conn.execute(
        """SELECT * FROM signals 
           WHERE source_event_id = ?""",
        (event_id,)
    )
    signals = [dict(r) for r in cursor.fetchall()]
    if signals:
        result["related_signals"] = signals
    
    conn.close()
    return result


# ============================================================
# Causal Analysis
# ============================================================
@router.get("/analysis/{event_id}")
async def get_causal_analysis(event_id: str):
    """Get causal chain analysis for an event."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        "SELECT * FROM causal_analyses WHERE event_id = ?",
        (event_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return dict(row)


# ============================================================
# Signals (LEGACY endpoints - prefer /trends for dashboard)
# Kept for: SignalDetail modal, direct signal access, debugging
# TODO: Consider removing after frontend fully migrated to /trends
# ============================================================
@router.get("/signals")
async def list_signals(
    status: Optional[str] = Query(default=None, description="active, verified_correct, verified_wrong, expired")
):
    """List signals, defaults to active."""
    conn = get_connection(settings.DATABASE_PATH)
    
    if status == "all":
        cursor = conn.execute(
            """SELECT s.*, e.title as source_event_title
               FROM signals s
               LEFT JOIN events e ON s.source_event_id = e.id
               ORDER BY s.created_at DESC"""
        )
    elif status:
        cursor = conn.execute(
            """SELECT s.*, e.title as source_event_title
               FROM signals s
               LEFT JOIN events e ON s.source_event_id = e.id
               WHERE s.status = ?
               ORDER BY s.created_at DESC""",
            (status,)
        )
    else:
        # Default: active
        cursor = conn.execute(
            """SELECT s.*, e.title as source_event_title
               FROM signals s
               LEFT JOIN events e ON s.source_event_id = e.id
               WHERE s.status = 'active'
               AND (s.expires_at IS NULL OR s.expires_at > datetime('now'))
               ORDER BY 
                   CASE s.confidence WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                   s.created_at DESC"""
        )
    
    rows = cursor.fetchall()
    conn.close()
    
    return {"signals": [dict(row) for row in rows]}


@router.get("/signals/{signal_id}")
async def get_signal(signal_id: str):
    """Get single signal with details."""
    conn = get_connection(settings.DATABASE_PATH)
    
    cursor = conn.execute(
        """SELECT s.*, e.title as source_event_title
           FROM signals s
           LEFT JOIN events e ON s.source_event_id = e.id
           WHERE s.id = ?""",
        (signal_id,)
    )
    sig = cursor.fetchone()
    
    if not sig:
        conn.close()
        raise HTTPException(status_code=404, detail="Signal not found")
    
    result = dict(sig)
    
    # Get source event details
    if sig["source_event_id"]:
        cursor = conn.execute(
            "SELECT * FROM events WHERE id = ?",
            (sig["source_event_id"],)
        )
        source_event = cursor.fetchone()
        if source_event:
            result["source_event"] = dict(source_event)
    
    # Get theme if linked
    if sig["theme_id"]:
        cursor = conn.execute(
            "SELECT * FROM themes WHERE id = ?",
            (sig["theme_id"],)
        )
        theme = cursor.fetchone()
        if theme:
            result["theme"] = dict(theme)
    
    conn.close()
    return result


@router.get("/signals/accuracy")
async def get_signal_accuracy():
    """Get signal accuracy statistics."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        """SELECT * FROM signal_accuracy_stats 
           ORDER BY calculated_at DESC 
           LIMIT 10"""
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"accuracy_stats": [dict(row) for row in rows]}


# ============================================================
# Themes (LEGACY endpoints - prefer /trends for dashboard)
# Kept for: backward compatibility, direct theme access, debugging
# TODO: Consider removing after frontend fully migrated to /trends
# ============================================================
@router.get("/themes")
async def list_themes(
    status: Optional[str] = Query(default=None, description="emerging, active, fading, archived")
):
    """List themes, defaults to active and emerging."""
    conn = get_connection(settings.DATABASE_PATH)
    
    if status == "all":
        cursor = conn.execute(
            """SELECT * FROM themes 
               ORDER BY strength DESC, event_count DESC"""
        )
    elif status:
        cursor = conn.execute(
            """SELECT * FROM themes 
               WHERE status = ?
               ORDER BY strength DESC""",
            (status,)
        )
    else:
        # Default: active and emerging
        cursor = conn.execute(
            """SELECT * FROM themes 
               WHERE status IN ('active', 'emerging')
               ORDER BY strength DESC, event_count DESC"""
        )
    
    rows = cursor.fetchall()
    conn.close()
    
    return {"themes": [dict(row) for row in rows]}


@router.get("/themes/{theme_id}")
async def get_theme(theme_id: str):
    """Get single theme with related events and signals."""
    conn = get_connection(settings.DATABASE_PATH)
    
    cursor = conn.execute(
        "SELECT * FROM themes WHERE id = ?",
        (theme_id,)
    )
    theme = cursor.fetchone()
    
    if not theme:
        conn.close()
        raise HTTPException(status_code=404, detail="Theme not found")
    
    result = dict(theme)
    
    # Parse JSON fields
    if result.get('related_event_ids'):
        try:
            result['related_event_ids'] = json.loads(result['related_event_ids'])
        except:
            pass
    
    # Get related signals
    cursor = conn.execute(
        """SELECT * FROM signals 
           WHERE theme_id = ?
           ORDER BY created_at DESC""",
        (theme_id,)
    )
    signals = [dict(r) for r in cursor.fetchall()]
    result["signals"] = signals
    
    conn.close()
    return result


# ============================================================
# Trends: Priority Score + Category Helpers
# ============================================================

# Category keywords for auto-classification of themes by name.
# Order matters: first match wins. More specific patterns first.
CATEGORY_KEYWORDS = {
    'gold': ['vàng', 'gold', 'kim loại quý', 'bạc tích trữ'],
    'monetary': ['lãi suất', 'tiền tệ', 'ngân hàng trung ương', 'omo', 'thanh khoản',
                 'tín phiếu', 'huy động', 'tiền gửi', 'fed', 'deposit rate', 'interbank',
                 'tái cơ cấu ngân hàng', 'tăng trưởng ngân hàng'],
    'trade': ['thương mại', 'thuế quan', 'tariff', 'trade', 'xuất khẩu', 'nhập khẩu',
              'bảo hộ', 'trừng phạt'],
    'forex': ['tỷ giá', 'usd/vnd', 'forex', 'ngoại hối', 'đô la', 'nhân dân tệ',
              'yên', 'đồng', 'dxy'],
    'equity': ['chứng khoán', 'cổ phiếu', 'vnindex', 'nâng hạng', 'ipo', 'quỹ ngoại',
               'danh mục'],
    'energy': ['năng lượng', 'dầu', 'oil', 'gas', 'điện', 'xăng'],
    'geopolitics': ['địa chính trị', 'quân sự', 'trung đông', 'chiến tranh', 'leo thang',
                    'xung đột'],
    'realestate': ['bất động sản', 'nhà ở', 'metro', 'hạ tầng', 'đô thị'],
    'tech': ['ai ', 'công nghệ', 'chuyển đổi số', 'bán dẫn', 'fdi công nghệ'],
    'agriculture': ['nông sản', 'nông nghiệp', 'thực phẩm', 'gạo', 'cà phê'],
    'macro': ['gdp', 'cpi', 'lạm phát', 'tăng trưởng', 'kinh tế vĩ mô', 'tài khóa',
              'đầu tư công', 'phục hồi kinh tế', 'du lịch'],
    'fiscal': ['thuế', 'ngân sách', 'thuế suất', 'tuân thủ thuế'],
}


def _classify_category(name: str) -> str:
    """Classify a theme into a category based on name keywords."""
    name_lower = (name or '').lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                return category
    return 'other'


def _compute_priority_score(trend: dict) -> float:
    """
    Compute composite priority score (0-100) for a trend.
    
    Components:
    - Signal density (30%): More active signals = more important
    - Average confidence (25%): high > medium > low
    - Strength (15%): Theme strength from LLM
    - Time urgency (15%): Days until earliest signal expires
    - Evidence breadth (15%): More events = more evidence
    
    This score determines which trends appear in "Today's Focus".
    """
    signals = trend.get('signals', [])
    active_signals = [s for s in signals if s.get('status') == 'active']
    sig_count = len(active_signals)
    
    # 1. Signal density (0-30): logarithmic scale, diminishing returns after ~10
    # 1 signal → ~9, 5 signals → ~21, 10 → ~27, 43 → ~30
    sig_score = min(30, math.log2(sig_count + 1) / math.log2(50) * 30) if sig_count > 0 else 0
    
    # 2. Average confidence (0-25)
    conf_map = {'high': 3, 'medium': 2, 'low': 1}
    if active_signals:
        avg_conf = sum(conf_map.get(s.get('confidence', 'low'), 1) for s in active_signals) / len(active_signals)
    else:
        avg_conf = 1
    conf_score = (avg_conf / 3.0) * 25
    
    # 3. Strength (0-15)
    strength = trend.get('strength', 0) or 0
    strength_score = min(strength, 1.0) * 15
    
    # 4. Time urgency (0-15): inverted — sooner expiry = higher score
    expires = trend.get('earliest_signal_expires')
    if expires:
        try:
            exp_dt = datetime.fromisoformat(str(expires).replace('Z', '+00:00'))
            days_left = max(0, (exp_dt.replace(tzinfo=None) - datetime.now()).total_seconds() / 86400)
        except:
            days_left = 14
    else:
        days_left = 14
    
    if days_left < 1:
        time_score = 15
    elif days_left < 3:
        time_score = 12
    elif days_left < 7:
        time_score = 8
    else:
        time_score = 4
    
    # 5. Evidence breadth (0-15): logarithmic
    event_count = trend.get('event_count', 0) or 0
    evidence_score = min(15, math.log2(event_count + 1) / math.log2(20) * 15) if event_count > 0 else 0
    
    total = sig_score + conf_score + strength_score + time_score + evidence_score
    return round(total, 1)


# ============================================================
# Trends (Unified view: Themes + Signals)
# ============================================================
# NEW ENDPOINT: Replaces separate /themes and /signals for dashboard
# Frontend: TrendsPanel uses this as main data source
# Concept: Each "Trend" is a Theme with computed signal stats
# ============================================================

@router.get("/trends")
async def list_trends(
    urgency: Optional[str] = Query(default=None, description="urgent, watching, low"),
    with_summary: bool = Query(default=True, description="Include summary stats"),
    include_fading: bool = Query(default=False, description="Include fading trends"),
    include_empty: bool = Query(default=False, description="Include themes with no active signals"),
    limit: int = Query(default=30, le=200, description="Max results to return."),
    offset: int = Query(default=0, ge=0, description="Offset for pagination")
):
    """
    List trends for dashboard - unified Themes + Signals view.
    
    ## What is a Trend?
    A Trend = Theme (narrative) + Signals (predictions) + Events (evidence)
    
    ## Urgency levels:
    - urgent: Has signals expiring in < 7 days
    - watching: Has signals expiring in 7-14 days  
    - low: Has signals expiring in > 14 days
    - null: No active signals
    
    ## UI Usage:
    - TrendsPanel.jsx main dashboard
    - Sidebar "Active Trends" section
    
    ## Returns:
    - trends: Array of theme objects with signals loaded
    - summary: (if with_summary=true) Overall stats
    """
    conn = get_connection(settings.DATABASE_PATH)
    
    # Build query based on urgency filter
    if urgency:
        cursor = conn.execute(
            """SELECT t.*, 
                      (SELECT COUNT(*) FROM signals s WHERE s.theme_id = t.id AND s.status = 'active') as active_signals_count
               FROM themes t
               WHERE t.urgency = ?
               AND t.status IN ('active', 'emerging')
               ORDER BY t.earliest_signal_expires ASC
               LIMIT ? OFFSET ?""",
            (urgency, limit, offset)
        )
    else:
        # Default: all active/emerging, ordered by urgency then strength
        # By default, exclude themes with no active signals (urgency IS NULL)
        # to focus the dashboard on actionable trends with predictions
        status_filter = "('active', 'emerging', 'fading')" if include_fading else "('active', 'emerging')"
        urgency_filter = "" if include_empty else "AND t.urgency IS NOT NULL"
        cursor = conn.execute(
            f"""SELECT t.*,
                       (SELECT COUNT(*) FROM signals s WHERE s.theme_id = t.id AND s.status = 'active') as active_signals_count
                FROM themes t
                WHERE t.status IN {status_filter}
                {urgency_filter}
                ORDER BY 
                    CASE t.urgency 
                        WHEN 'urgent' THEN 1 
                        WHEN 'watching' THEN 2 
                        WHEN 'low' THEN 3 
                        ELSE 4 
                    END,
                    t.earliest_signal_expires ASC,
                    t.strength DESC
                LIMIT ? OFFSET ?""",
            (limit, offset)
        )
    
    trends_raw = [dict(row) for row in cursor.fetchall()]
    
    # Enrich each trend with its signals
    trends = []
    for trend in trends_raw:
        # Parse JSON fields
        for field in ['related_event_ids', 'related_signal_ids', 'related_indicators']:
            if trend.get(field):
                try:
                    trend[field] = json.loads(trend[field])
                except:
                    pass
        
        # Get active signals for this trend (exclude expired)
        # Signals past expires_at are automatically transitioned by recompute_trend_stats
        cursor = conn.execute(
            """SELECT * FROM signals 
               WHERE theme_id = ? AND status = 'active'
               ORDER BY 
                   expires_at ASC,
                   CASE confidence WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                   created_at DESC""",
            (trend['id'],)
        )
        trend['signals'] = [dict(s) for s in cursor.fetchall()]
        
        # Get related events (limited)
        if trend.get('related_event_ids'):
            event_ids = trend['related_event_ids'][:5]  # Limit to 5
            placeholders = ','.join(['?' for _ in event_ids])
            cursor = conn.execute(
                f"""SELECT id, title, source, published_at, current_score 
                    FROM events 
                    WHERE id IN ({placeholders})
                    ORDER BY published_at DESC""",
                event_ids
            )
            trend['events'] = [dict(e) for e in cursor.fetchall()]
        else:
            trend['events'] = []
        
        # Compute priority_score and category for each trend
        trend['priority_score'] = _compute_priority_score(trend)
        trend['category'] = _classify_category(trend.get('name_vi') or trend.get('name') or '')
        
        trends.append(trend)
    
    # Sort by priority_score DESC (highest priority first)
    trends.sort(key=lambda t: t['priority_score'], reverse=True)
    
    # has_more: true if there could be more results beyond this page
    has_more = len(trends_raw) == limit
    
    result = {"trends": trends, "has_more": has_more, "offset": offset, "limit": limit}
    
    # Add summary stats if requested
    if with_summary:
        # Count only themes with active signals (urgency IS NOT NULL)
        # to match what the dashboard displays
        cursor = conn.execute(
            """SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN urgency = 'urgent' THEN 1 ELSE 0 END) as urgent_count,
                SUM(CASE WHEN urgency = 'watching' THEN 1 ELSE 0 END) as watching_count,
                SUM(CASE WHEN signals_count > 0 THEN 1 ELSE 0 END) as with_signals_count
               FROM themes
               WHERE status IN ('active', 'emerging')
               AND urgency IS NOT NULL"""
        )
        counts = dict(cursor.fetchone())
        
        # Get overall signal accuracy
        cursor = conn.execute(
            """SELECT 
                SUM(CASE WHEN status = 'verified_correct' THEN 1 ELSE 0 END) as correct,
                COUNT(*) as total
               FROM signals
               WHERE status IN ('verified_correct', 'verified_wrong')"""
        )
        acc = dict(cursor.fetchone())
        
        accuracy_pct = None
        if acc['total'] and acc['total'] > 0:
            accuracy_pct = round((acc['correct'] or 0) / acc['total'] * 100, 1)
        
        result['summary'] = {
            **counts,
            'signals_correct': acc['correct'] or 0,
            'signals_total_verified': acc['total'] or 0,
            'signals_accuracy': accuracy_pct,
        }
    
    conn.close()
    return result


# ============================================================
# IMPORTANT: Static routes MUST come BEFORE dynamic routes
# FastAPI matches routes in order of declaration
# /trends/urgent/sidebar must be BEFORE /trends/{trend_id}
# ============================================================

@router.get("/trends/urgent/sidebar")
async def get_urgent_trends_sidebar():
    """
    Get urgent trends for sidebar quick view.
    
    ## UI Usage:
    - Vietnam/Global tab sidebar "Active Trends" section
    - Limited data, optimized for small display
    
    ## Returns:
    - urgent: Array of urgent trends (max 3)
    - watching: Array of watching trends (max 2)
    """
    conn = get_connection(settings.DATABASE_PATH)
    
    # Get urgent
    cursor = conn.execute(
        """SELECT id, name, name_vi, urgency, signals_count, earliest_signal_expires
           FROM themes
           WHERE urgency = 'urgent' AND status IN ('active', 'emerging')
           ORDER BY earliest_signal_expires ASC
           LIMIT 3"""
    )
    urgent = [dict(row) for row in cursor.fetchall()]
    
    # Get watching
    cursor = conn.execute(
        """SELECT id, name, name_vi, urgency, signals_count, earliest_signal_expires
           FROM themes
           WHERE urgency = 'watching' AND status IN ('active', 'emerging')
           ORDER BY earliest_signal_expires ASC
           LIMIT 2"""
    )
    watching = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return {"urgent": urgent, "watching": watching}


@router.get("/trends/summary")
async def get_trends_summary():
    """
    Get summary stats for trends dashboard header.
    
    ## UI Usage:
    - TrendsPanel header stats bar
    """
    conn = get_connection(settings.DATABASE_PATH)
    
    cursor = conn.execute(
        """SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN urgency = 'urgent' THEN 1 ELSE 0 END) as urgent_count,
            SUM(CASE WHEN urgency = 'watching' THEN 1 ELSE 0 END) as watching_count,
            SUM(CASE WHEN signals_count > 0 THEN 1 ELSE 0 END) as with_signals_count
           FROM themes
           WHERE status IN ('active', 'emerging')"""
    )
    counts = dict(cursor.fetchone())
    
    cursor = conn.execute(
        """SELECT 
            SUM(CASE WHEN status = 'verified_correct' THEN 1 ELSE 0 END) as correct,
            COUNT(*) as total
           FROM signals
           WHERE status IN ('verified_correct', 'verified_wrong')"""
    )
    acc = dict(cursor.fetchone())
    
    accuracy_pct = None
    if acc['total'] and acc['total'] > 0:
        accuracy_pct = round((acc['correct'] or 0) / acc['total'] * 100, 1)
    
    conn.close()
    return {
        **counts,
        'signals_correct': acc['correct'] or 0,
        'signals_total_verified': acc['total'] or 0,
        'signals_accuracy': accuracy_pct,
    }


# ============================================================
# Dynamic route - MUST come AFTER all static /trends/* routes
# ============================================================

@router.get("/trends/{trend_id}")
async def get_trend(trend_id: str):
    """
    Get single trend with full details.
    
    ## UI Usage:
    - TrendDetail modal/page
    - Shows full narrative, all signals, all events
    
    ## Returns:
    - Full theme object with all signals and events
    """
    conn = get_connection(settings.DATABASE_PATH)
    
    cursor = conn.execute(
        "SELECT * FROM themes WHERE id = ?",
        (trend_id,)
    )
    theme = cursor.fetchone()
    
    if not theme:
        conn.close()
        raise HTTPException(status_code=404, detail="Trend not found")
    
    result = dict(theme)
    
    # Parse JSON fields
    for field in ['related_event_ids', 'related_signal_ids', 'related_indicators']:
        if result.get(field):
            try:
                result[field] = json.loads(result[field])
            except:
                pass
    
    # Get ALL signals (including verified)
    cursor = conn.execute(
        """SELECT s.*, e.title as source_event_title
           FROM signals s
           LEFT JOIN events e ON s.source_event_id = e.id
           WHERE s.theme_id = ?
           ORDER BY 
               CASE s.status WHEN 'active' THEN 1 ELSE 2 END,
               s.expires_at ASC""",
        (trend_id,)
    )
    result['signals'] = [dict(s) for s in cursor.fetchall()]
    
    # Separate active and verified signals for UI
    result['active_signals'] = [s for s in result['signals'] if s['status'] == 'active']
    result['verified_signals'] = [s for s in result['signals'] if s['status'] in ['verified_correct', 'verified_wrong']]
    
    # Get ALL related events
    if result.get('related_event_ids'):
        event_ids = result['related_event_ids']
        placeholders = ','.join(['?' for _ in event_ids])
        cursor = conn.execute(
            f"""SELECT * FROM events 
                WHERE id IN ({placeholders})
                ORDER BY published_at DESC""",
            event_ids
        )
        result['events'] = [dict(e) for e in cursor.fetchall()]
    else:
        result['events'] = []
    
    # Get related indicator values
    if result.get('related_indicators'):
        ind_ids = result['related_indicators']
        placeholders = ','.join(['?' for _ in ind_ids])
        cursor = conn.execute(
            f"""SELECT id, name, name_vi, value, change, change_pct, trend, updated_at
                FROM indicators
                WHERE id IN ({placeholders})""",
            ind_ids
        )
        result['indicators'] = [dict(i) for i in cursor.fetchall()]
    else:
        result['indicators'] = []
    
    conn.close()
    return result


@router.post("/trends/{trend_id}/archive")
async def archive_trend(trend_id: str):
    """
    Archive a trend (set status to 'archived').
    
    ## UI Usage:
    - TrendDetail "Archive" button
    - Removes from active dashboard but keeps history
    """
    conn = get_connection(settings.DATABASE_PATH)
    
    cursor = conn.execute(
        "UPDATE themes SET status = 'archived', updated_at = datetime('now') WHERE id = ?",
        (trend_id,)
    )
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Trend not found")
    
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Trend {trend_id} archived"}


@router.post("/trends/{trend_id}/dismiss")
async def dismiss_trend(trend_id: str):
    """
    Dismiss a trend (set status to 'fading').
    
    ## UI Usage:
    - TrendDetail "Dismiss" button
    - Moves to fading section, will auto-archive eventually
    """
    conn = get_connection(settings.DATABASE_PATH)
    
    cursor = conn.execute(
        "UPDATE themes SET status = 'fading', urgency = NULL, updated_at = datetime('now') WHERE id = ?",
        (trend_id,)
    )
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Trend not found")
    
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Trend {trend_id} dismissed"}


# ============================================================
# Watchlist
# ============================================================
@router.get("/watchlist")
async def list_watchlist(
    status: Optional[str] = Query(default=None, description="active, triggered, dismissed")
):
    """List watchlist items, defaults to active."""
    conn = get_connection(settings.DATABASE_PATH)
    
    if status == "all":
        cursor = conn.execute(
            """SELECT * FROM watchlist 
               ORDER BY created_at DESC"""
        )
    elif status:
        cursor = conn.execute(
            """SELECT * FROM watchlist 
               WHERE status = ?
               ORDER BY created_at DESC""",
            (status,)
        )
    else:
        # Default: active
        cursor = conn.execute(
            """SELECT * FROM watchlist 
               WHERE status = 'active'
               ORDER BY created_at DESC"""
        )
    
    rows = cursor.fetchall()
    conn.close()
    
    return {"watchlist": [dict(row) for row in rows]}


@router.get("/watchlist/{item_id}")
async def get_watchlist_item(item_id: str):
    """Get single watchlist item with trigger event."""
    conn = get_connection(settings.DATABASE_PATH)
    
    cursor = conn.execute(
        "SELECT * FROM watchlist WHERE id = ?",
        (item_id,)
    )
    item = cursor.fetchone()
    
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    
    result = dict(item)
    
    # Get trigger event if exists
    if item["triggered_by_event_id"]:
        cursor = conn.execute(
            "SELECT * FROM events WHERE id = ?",
            (item["triggered_by_event_id"],)
        )
        event = cursor.fetchone()
        if event:
            result["trigger_event"] = dict(event)
    
    conn.close()
    return result


# ============================================================
# Topics
# ============================================================
@router.get("/topics/hot")
async def get_hot_topics():
    """Get hot topics (3+ occurrences in 7 days)."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        """SELECT * FROM topic_frequency 
           WHERE is_hot = TRUE 
           AND last_seen >= date('now', '-7 days')
           ORDER BY occurrence_count DESC"""
    )
    rows = cursor.fetchall()
    conn.close()
    
    topics = []
    for row in rows:
        topic = dict(row)
        if topic.get('related_event_ids'):
            try:
                topic['related_event_ids'] = json.loads(topic['related_event_ids'])
            except:
                pass
        topics.append(topic)
    
    return {"hot_topics": topics}


@router.get("/topics/trending")
async def get_trending_topics(limit: int = Query(default=20, le=50)):
    """Get trending topics (appearing frequently)."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        """SELECT * FROM topic_frequency 
           WHERE occurrence_count >= 2 
           ORDER BY occurrence_count DESC, last_seen DESC 
           LIMIT ?""",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"topics": [dict(row) for row in rows]}


@router.get("/topics/{topic}/events")
async def get_topic_events(topic: str):
    """Get events related to a topic."""
    conn = get_connection(settings.DATABASE_PATH)
    
    # Get topic info
    cursor = conn.execute(
        "SELECT * FROM topic_frequency WHERE topic = ?",
        (topic,)
    )
    topic_info = cursor.fetchone()
    
    if not topic_info:
        conn.close()
        raise HTTPException(status_code=404, detail="Topic not found")
    
    topic_dict = dict(topic_info)
    event_ids = []
    if topic_dict.get('related_event_ids'):
        try:
            event_ids = json.loads(topic_dict['related_event_ids'])
        except:
            pass
    
    events = []
    if event_ids:
        placeholders = ','.join(['?' for _ in event_ids])
        cursor = conn.execute(
            f"SELECT * FROM events WHERE id IN ({placeholders}) ORDER BY published_at DESC",
            event_ids
        )
        events = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        "topic": topic_dict,
        "events": events
    }


# ============================================================
# Calendar
# ============================================================
@router.get("/calendar")
async def list_calendar_events(
    country: Optional[str] = None,
    importance: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """List upcoming economic calendar events."""
    today = date.today().isoformat()
    
    conn = get_connection(settings.DATABASE_PATH)
    
    query = "SELECT * FROM calendar_events WHERE date >= ?"
    params = [today]
    
    if country:
        query += " AND country = ?"
        params.append(country)
    if importance:
        query += " AND importance = ?"
        params.append(importance)
    
    query += " ORDER BY date, time LIMIT ?"
    params.append(limit)
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return {"calendar_events": [dict(row) for row in rows]}


@router.get("/calendar/week")
async def get_week_calendar():
    """Get this week's calendar events."""
    from datetime import timedelta
    
    today = date.today()
    week_end = today + timedelta(days=7)
    
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        """SELECT * FROM calendar_events 
           WHERE date >= ? AND date <= ? 
           ORDER BY date, time""",
        (today.isoformat(), week_end.isoformat())
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {
        "calendar_events": [dict(row) for row in rows],
        "from": today.isoformat(),
        "to": week_end.isoformat()
    }


# ============================================================
# Run History
# ============================================================
@router.get("/runs")
async def list_runs(limit: int = Query(default=20, le=100)):
    """List processing runs."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        "SELECT * FROM run_history ORDER BY run_time DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"runs": [dict(row) for row in rows]}


@router.get("/runs/latest")
async def get_latest_run():
    """Get the latest processing run."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        "SELECT * FROM run_history ORDER BY run_time DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="No runs found")
    
    return dict(row)


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get single run details."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute("SELECT * FROM run_history WHERE id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return dict(row)


# ============================================================
# Refresh (Manual trigger)
# ============================================================
@router.post("/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks):
    """Manually trigger data refresh and analysis."""
    from processor.pipeline import Pipeline
    from database.session import close_engine
    import asyncio
    
    def run_pipeline():
        async def _run():
            # Close any existing engine from previous runs to avoid reusing
            # an engine bound to a different event loop
            await close_engine()
            pipeline = Pipeline()
            return await pipeline.run()
        
        try:
            result = asyncio.run(_run())
            return result
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Pipeline error: {e}", exc_info=True)
            return {"error": str(e)}
    
    background_tasks.add_task(run_pipeline)
    
    return {
        "status": "triggered",
        "message": "Pipeline started in background. Check /api/runs/latest for status.",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/refresh/ranking")
async def trigger_ranking_refresh():
    """Trigger only the ranking layer (apply decay)."""
    from processor.pipeline import Pipeline
    
    try:
        pipeline = Pipeline()
        result = await pipeline.run_ranking_only()
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Dashboard Summary
# ============================================================
@router.get("/dashboard")
async def get_dashboard_summary():
    """
    Get complete dashboard data in one call.
    
    Optimized for frontend to minimize API calls.
    """
    conn = get_connection(settings.DATABASE_PATH)
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "key_events": [],
        "other_news_count": 0,
        "indicators": {},
        "investigations": {
            "high_priority": [],
            "medium_priority": []
        },
        "hot_topics": [],
        "last_run": None
    }
    
    # Key events (top 15)
    cursor = conn.execute(
        """SELECT * FROM events 
           WHERE display_section = 'key_events' 
           ORDER BY current_score DESC LIMIT 15"""
    )
    result["key_events"] = [dict(r) for r in cursor.fetchall()]
    
    # Other news count
    cursor = conn.execute(
        "SELECT COUNT(*) as count FROM events WHERE display_section = 'other_news'"
    )
    row = cursor.fetchone()
    result["other_news_count"] = row['count'] if row else 0
    
    # Key indicators by group
    for group_id, group_info in INDICATOR_GROUPS.items():
        cursor = conn.execute(
            "SELECT * FROM indicators WHERE category = ? ORDER BY name",
            (group_id,)
        )
        indicators = [dict(r) for r in cursor.fetchall()]
        if indicators:
            result["indicators"][group_id] = {
                "display_name": group_info["display_name"],
                "items": indicators
            }
    
    # Open investigations
    cursor = conn.execute(
        """SELECT i.*, e.title as source_event_title
           FROM investigations i
           LEFT JOIN events e ON i.source_event_id = e.id
           WHERE i.status IN ('open', 'updated')
           ORDER BY CASE i.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"""
    )
    investigations = [dict(r) for r in cursor.fetchall()]
    result["investigations"]["high_priority"] = [i for i in investigations if i.get('priority') == 'high']
    result["investigations"]["medium_priority"] = [i for i in investigations if i.get('priority') != 'high']
    
    # Hot topics
    cursor = conn.execute(
        """SELECT * FROM topic_frequency 
           WHERE is_hot = TRUE 
           ORDER BY occurrence_count DESC LIMIT 10"""
    )
    result["hot_topics"] = [dict(r) for r in cursor.fetchall()]
    
    # Last run
    cursor = conn.execute(
        "SELECT * FROM run_history ORDER BY run_time DESC LIMIT 1"
    )
    last_run = cursor.fetchone()
    if last_run:
        result["last_run"] = dict(last_run)
    
    conn.close()
    return result
