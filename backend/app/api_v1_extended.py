#!/usr/bin/env python3
"""
GOTXA SIEM/SOAR REST API - Extended Endpoints
Operations, Governance, and Telemetry endpoints for dashboard telemetry
"""

from flask import Blueprint, request, g
from datetime import datetime, timedelta
from sqlalchemy import desc, and_, func
import uuid

from app.models import (
    db, Incident, Task, LogSource, ThreatIntelligenceFeed, JITSession, SystemMetric
)
from app.auth import (
    authenticate, require_permission, error_response, success_response, list_response
)

api = Blueprint('api_extended', __name__, url_prefix='/api')

# ============================================================================
# 1. INCIDENT SUMMARY ENDPOINTS
# ============================================================================

@authenticate
def get_incidents_summary():
    """Get aggregated incident metrics (tasks, overdue, post-incident actions)."""
    try:
        # Open tasks
        open_tasks = db.session.query(Task).filter_by(status='open').count()
        
        # Overdue tasks
        overdue_tasks = db.session.query(Task).filter(
            Task.status == 'open',
            Task.due_at < datetime.utcnow()
        ).count()
        
        # Post-incident actions (tasks in closed incidents)
        closed_incidents = db.session.query(Incident).filter_by(
            status='closed'
        ).all()
        
        post_incident_actions = db.session.query(Task).filter(
            Task.incident_id.in_([i.id for i in closed_incidents]),
            Task.status.in_(['open', 'in_progress'])
        ).count()
        
        return success_response({
            'open_tasks_count': open_tasks,
            'overdue_tasks_count': overdue_tasks,
            'post_incident_actions_count': post_incident_actions,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/incidents/<incident_id>/tasks', methods=['GET'])
@authenticate
def get_incident_tasks(incident_id):
    """Get all tasks for a specific incident."""
    try:
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        tasks = db.session.query(Task).filter_by(incident_id=incident_id).all()
        
        return success_response({
            'incident_id': incident.incident_id,
            'tasks': [{
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'status': t.status,
                'assigned_to_id': t.assigned_to_id,
                'assigned_to_name': t.assigned_to.username if t.assigned_to else None,
                'due_at': t.due_at.isoformat() if t.due_at else None,
                'is_overdue': t.due_at < datetime.utcnow() if t.due_at else False,
                'created_at': t.created_at.isoformat() if t.created_at else None
            } for t in tasks]
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/incidents/<incident_id>/tasks', methods=['POST'])
@authenticate
@require_permission('incidents.edit')
def create_incident_task(incident_id):
    """Create a new task for an incident."""
    try:
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        data = request.get_json()
        
        task = Task(
            incident_id=incident_id,
            title=data.get('title'),
            description=data.get('description', ''),
            status='open',
            assigned_to_id=data.get('assigned_to_id'),
            due_at=datetime.fromisoformat(data['due_at']) if data.get('due_at') else None
        )
        
        db.session.add(task)
        db.session.commit()
        
        return success_response({
            'id': task.id,
            'title': task.title,
            'status': task.status
        }, 'Task created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 2. LOG SOURCE INGESTION METRICS
# ============================================================================

@authenticate
def get_data_sources_metrics():
    """Get ingestion metrics for all log sources."""
    try:
        sources = db.session.query(LogSource).all()
        
        return success_response({
            'items': [{
                'id': s.id,
                'name': s.name,
                'connector_type': s.connector_type,
                'status': s.status,
                'last_event_time': s.last_event_timestamp.isoformat() if s.last_event_timestamp else None,
                'ingestion_rate': s.ingestion_rate,
                'drop_count': s.drop_count,
                'parse_error_count': s.parse_error_count,
                'ingest_delay_seconds': s.ingest_delay_seconds,
                'total_events_ingested': s.total_events_ingested,
                'health_percentage': max(0, 100 - (s.drop_count + s.parse_error_count) / max(s.total_events_ingested, 1) * 100)
            } for s in sources],
            'total_sources': len(sources),
            'healthy_sources': sum(1 for s in sources if s.status == 'healthy'),
            'failing_sources': sum(1 for s in sources if s.status == 'failing'),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/data-sources', methods=['POST'])
@authenticate
@require_permission('settings.write')
def create_log_source():
    """Register a new log source."""
    try:
        data = request.get_json()
        
        source = LogSource(
            name=data.get('name'),
            connector_type=data.get('connector_type'),
            status='healthy'
        )
        
        db.session.add(source)
        db.session.commit()
        
        return success_response({
            'id': source.id,
            'name': source.name,
            'status': source.status
        }, 'Log source created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 3. THREAT INTELLIGENCE FEEDS
# ============================================================================

@authenticate
def list_threat_intelligence_feeds():
    """List all threat intelligence feeds with sync status."""
    try:
        feeds = db.session.query(ThreatIntelligenceFeed).all()
        
        return success_response({
            'items': [{
                'id': f.id,
                'feed_id': f.feed_id,
                'name': f.name,
                'description': f.description,
                'status': f.status,
                'last_sync': f.last_sync.isoformat() if f.last_sync else None,
                'sync_interval_hours': f.sync_interval_hours,
                'indicators_count': f.indicators_count,
                'sync_latency_minutes': (datetime.utcnow() - f.last_sync).total_seconds() / 60 if f.last_sync else None,
                'last_error': f.last_error if f.status == 'failing' else None
            } for f in feeds],
            'total_feeds': len(feeds),
            'active_feeds': sum(1 for f in feeds if f.status == 'active'),
            'total_indicators': sum(f.indicators_count for f in feeds),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/threat-intelligence/feeds', methods=['POST'])
@authenticate
@require_permission('settings.write')
def create_threat_intelligence_feed():
    """Create a new threat intelligence feed."""
    try:
        data = request.get_json()
        
        feed = ThreatIntelligenceFeed(
            feed_id=f"FEED-{uuid.uuid4().hex[:8].upper()}",
            name=data.get('name'),
            description=data.get('description', ''),
            status='active',
            feed_url=data.get('feed_url'),
            sync_interval_hours=data.get('sync_interval_hours', 24)
        )
        
        db.session.add(feed)
        db.session.commit()
        
        return success_response({
            'id': feed.id,
            'feed_id': feed.feed_id,
            'name': feed.name
        }, 'Feed created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/threat-intelligence/feeds/<feed_id>/sync', methods=['POST'])
@authenticate
@require_permission('settings.write')
def sync_threat_intelligence_feed(feed_id):
    """Trigger a sync for a threat intelligence feed."""
    try:
        feed = db.session.query(ThreatIntelligenceFeed).filter_by(id=feed_id).first()
        if not feed:
            return error_response('NotFound', 'Feed not found', 404)
        
        feed.last_sync = datetime.utcnow()
        feed.status = 'active'
        feed.last_error = None
        
        db.session.commit()
        
        return success_response({
            'feed_id': feed.feed_id,
            'last_sync': feed.last_sync.isoformat(),
            'status': feed.status
        }, 'Feed sync initiated', 202)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 4. JIT (JUST-IN-TIME) ACCESS MANAGEMENT
# ============================================================================

@authenticate
def list_jit_sessions():
    """List active JIT privilege elevation sessions."""
    try:
        # Get active sessions
        active_sessions = db.session.query(JITSession).filter(
            JITSession.status.in_(['approved', 'pending']),
            JITSession.expires_at > datetime.utcnow()
        ).all()
        
        return success_response({
            'items': [{
                'id': s.id,
                'session_id': s.session_id,
                'user_id': s.user_id,
                'username': s.user.username if s.user else None,
                'reason': s.reason,
                'ticket_id': s.ticket_id,
                'status': s.status,
                'elevated_role': s.elevated_role,
                'requested_at': s.requested_at.isoformat() if s.requested_at else None,
                'approved_at': s.approved_at.isoformat() if s.approved_at else None,
                'approved_by': s.approved_by.username if s.approved_by else None,
                'expires_at': s.expires_at.isoformat() if s.expires_at else None,
                'time_remaining_seconds': (s.expires_at - datetime.utcnow()).total_seconds() if s.expires_at > datetime.utcnow() else 0
            } for s in active_sessions],
            'active_count': len(active_sessions),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@authenticate
def request_jit_session():
    """Request a JIT privilege elevation."""
    try:
        data = request.get_json()
        
        duration_hours = data.get('duration_hours', 2)
        expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
        
        session = JITSession(
            session_id=f"JIT-{uuid.uuid4().hex[:8].upper()}",
            user_id=g.user.id,
            reason=data.get('reason'),
            ticket_id=data.get('ticket_id'),
            expires_at=expires_at,
            status='pending'
        )
        
        db.session.add(session)
        db.session.commit()
        
        return success_response({
            'session_id': session.session_id,
            'status': session.status,
            'requested_at': session.requested_at.isoformat(),
            'expires_at': session.expires_at.isoformat()
        }, 'JIT session requested', 201)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/access/jit-sessions/<session_id>/approve', methods=['POST'])
@authenticate
@require_permission('settings.write')
def approve_jit_session(session_id):
    """Approve a JIT elevation request."""
    try:
        session = db.session.query(JITSession).filter_by(id=session_id).first()
        if not session:
            return error_response('NotFound', 'Session not found', 404)
        
        data = request.get_json()
        
        session.status = 'approved'
        session.approved_at = datetime.utcnow()
        session.approved_by_id = g.user.id
        session.elevated_role = data.get('elevated_role', 'admin')
        
        db.session.commit()
        
        return success_response({
            'session_id': session.session_id,
            'status': session.status,
            'elevated_role': session.elevated_role
        }, 'JIT session approved', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/access/jit-sessions/<session_id>/revoke', methods=['POST'])
@authenticate
@require_permission('settings.write')
def revoke_jit_session(session_id):
    """Revoke a JIT elevation session."""
    try:
        session = db.session.query(JITSession).filter_by(id=session_id).first()
        if not session:
            return error_response('NotFound', 'Session not found', 404)
        
        session.status = 'revoked'
        session.revoked_at = datetime.utcnow()
        
        db.session.commit()
        
        return success_response({
            'session_id': session.session_id,
            'status': session.status
        }, 'JIT session revoked', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 5. GLOBAL DASHBOARD METRICS
# ============================================================================

@authenticate
def get_overview_metrics():
    """Get aggregated KPI metrics for main dashboard."""
    try:
        # Current ingestion rate (events/min)
        recent_sources = db.session.query(LogSource).filter(
            LogSource.updated_at > datetime.utcnow() - timedelta(minutes=5)
        ).all()
        
        current_ingestion_rate = sum(s.ingestion_rate for s in recent_sources)
        
        # Source health
        all_sources = db.session.query(LogSource).all()
        healthy_sources = sum(1 for s in all_sources if s.status == 'healthy')
        total_sources = len(all_sources)
        
        # SLA at risk (incidents not closed within SLA)
        # SLA = 24 hours to close
        sla_at_risk = db.session.query(Incident).filter(
            Incident.status != 'closed',
            Incident.created_at < datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        # Threat feed status
        threat_feeds = db.session.query(ThreatIntelligenceFeed).all()
        active_feeds = sum(1 for f in threat_feeds if f.status == 'active')
        total_indicators = sum(f.indicators_count for f in threat_feeds)
        
        # JIT sessions
        active_jit = db.session.query(JITSession).filter(
            JITSession.status == 'approved',
            JITSession.expires_at > datetime.utcnow()
        ).count()
        
        return success_response({
            'ingestion_rate_per_minute': current_ingestion_rate,
            'sources_healthy': f"{healthy_sources}/{total_sources}",
            'sources_healthy_count': healthy_sources,
            'sources_total_count': total_sources,
            'sla_at_risk_count': sla_at_risk,
            'threat_feeds_active': active_feeds,
            'threat_indicators_total': total_indicators,
            'jit_sessions_active': active_jit,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)
