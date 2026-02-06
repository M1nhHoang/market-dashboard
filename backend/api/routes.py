"""
API Routes - All endpoint definitions for Market Intelligence Dashboard

Endpoints organized by:
- Health Check
- Indicators (current values and history)
- Events (key events, other news, archive)
- Investigations
- Topics (hot topics)
- Calendar (economic events)
- System (runs, refresh)
"""
import json
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
    
    if grouped and not category:
        # Group by category
        grouped_data = {}
        for group_id, group_info in INDICATOR_GROUPS.items():
            grouped_data[group_id] = {
                "display_name": group_info["display_name"],
                "indicators": [
                    ind for ind in indicators 
                    if ind.get('category') == group_id or ind.get('id') in group_info.get("indicators", [])
                ]
            }
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
        for field in ['chain_steps', 'needs_investigation', 'affected_indicators']:
            if analysis_dict.get(field):
                try:
                    analysis_dict[field] = json.loads(analysis_dict[field])
                except:
                    pass
        result["causal_analysis"] = analysis_dict
    
    # Get related investigations
    cursor = conn.execute(
        """SELECT * FROM investigations 
           WHERE source_event_id = ? OR resolved_by_event_id = ?""",
        (event_id, event_id)
    )
    investigations = [dict(r) for r in cursor.fetchall()]
    if investigations:
        result["related_investigations"] = investigations
    
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
# Investigations
# ============================================================
@router.get("/investigations")
async def list_investigations(
    status: Optional[str] = Query(default=None, description="open, updated, resolved, stale, escalated")
):
    """List investigations, defaults to open/updated."""
    conn = get_connection(settings.DATABASE_PATH)
    
    if status == "all":
        cursor = conn.execute(
            """SELECT i.*, e.title as source_event_title
               FROM investigations i
               LEFT JOIN events e ON i.source_event_id = e.id
               ORDER BY i.created_at DESC"""
        )
    elif status:
        cursor = conn.execute(
            """SELECT i.*, e.title as source_event_title
               FROM investigations i
               LEFT JOIN events e ON i.source_event_id = e.id
               WHERE i.status = ?
               ORDER BY i.created_at DESC""",
            (status,)
        )
    else:
        # Default: open and updated
        cursor = conn.execute(
            """SELECT i.*, e.title as source_event_title
               FROM investigations i
               LEFT JOIN events e ON i.source_event_id = e.id
               WHERE i.status IN ('open', 'updated')
               ORDER BY 
                   CASE i.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                   i.created_at DESC"""
        )
    
    rows = cursor.fetchall()
    conn.close()
    
    return {"investigations": [dict(row) for row in rows]}


@router.get("/investigations/all")
async def list_all_investigations(limit: int = Query(default=50, le=200)):
    """List all investigations including resolved."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        """SELECT i.*, e.title as source_event_title
           FROM investigations i
           LEFT JOIN events e ON i.source_event_id = e.id
           ORDER BY i.updated_at DESC LIMIT ?""",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"investigations": [dict(row) for row in rows]}


@router.get("/investigations/{investigation_id}")
async def get_investigation(investigation_id: str):
    """Get single investigation with evidence timeline."""
    conn = get_connection(settings.DATABASE_PATH)
    
    # Get investigation
    cursor = conn.execute(
        """SELECT i.*, e.title as source_event_title
           FROM investigations i
           LEFT JOIN events e ON i.source_event_id = e.id
           WHERE i.id = ?""",
        (investigation_id,)
    )
    inv = cursor.fetchone()
    
    if not inv:
        conn.close()
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    result = dict(inv)
    
    # Parse JSON fields
    for field in ['related_indicators', 'related_templates']:
        if result.get(field):
            try:
                result[field] = json.loads(result[field])
            except:
                pass
    
    # Get evidence timeline
    cursor = conn.execute(
        """SELECT ie.*, e.title as event_title, e.category, e.base_score
           FROM investigation_evidence ie
           LEFT JOIN events e ON ie.event_id = e.id
           WHERE ie.investigation_id = ?
           ORDER BY ie.added_at DESC""",
        (investigation_id,)
    )
    evidence = [dict(r) for r in cursor.fetchall()]
    result["evidence_timeline"] = evidence
    
    # Get source event details
    if inv["source_event_id"]:
        cursor = conn.execute(
            "SELECT * FROM events WHERE id = ?",
            (inv["source_event_id"],)
        )
        source_event = cursor.fetchone()
        if source_event:
            result["source_event"] = dict(source_event)
    
    conn.close()
    return result


@router.get("/investigations/{investigation_id}/evidence")
async def get_investigation_evidence(investigation_id: str):
    """Get all evidence for an investigation."""
    conn = get_connection(settings.DATABASE_PATH)
    cursor = conn.execute(
        """SELECT ie.*, e.title as event_title, e.summary as event_summary
           FROM investigation_evidence ie
           LEFT JOIN events e ON ie.event_id = e.id
           WHERE ie.investigation_id = ?
           ORDER BY ie.added_at DESC""",
        (investigation_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return {"evidence": [dict(row) for row in rows]}


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
    
    def run_pipeline():
        try:
            pipeline = Pipeline()
            result = pipeline.run()
            return result
        except Exception as e:
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
        result = pipeline.run_ranking_only()
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
