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
# 2. LOG SOURCE INGESTION METRICS
# ============================================================================

@api.route('/data-sources', methods=['GET'])
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
