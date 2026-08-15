#!/usr/bin/env python3
"""
GOTXA SIEM/SOAR REST API - Report Download & Status Endpoints
"""

from flask import Blueprint, request, g, send_file
from datetime import datetime
import os
from sqlalchemy import or_

from app.models import db, Report, AuditEvent
from app.auth import authenticate, require_permission, error_response, success_response

api = Blueprint('api_reports', __name__, url_prefix='/api')

@api.route('/reports/<report_id>/download', methods=['GET'])
@authenticate
@require_permission('reports.read')
def download_report(report_id):
    """Download generated PDF report."""
    try:
        import os
        
        # Search by both id and report_id
        report = db.session.query(Report).filter(
            or_(Report.id == report_id, Report.report_id == report_id)
        ).first()
        
        if not report:
            return error_response('NotFound', 'Report not found', 404)
        
        if report.status != 'completed':
            return error_response('BadRequest', f'Report status is {report.status}, not completed', 400)
        
        if not report.file_path or not os.path.exists(report.file_path):
            return error_response('NotFound', 'Report file not found on server', 404)
        
        # Log download
        audit = AuditEvent(
            correlation_id=report.report_id,
            actor_id=g.user.id,
            action='report.downloaded',
            resource_type='Report',
            resource_id=str(report.id),
            reason=f'Downloaded by {g.user.username}'
        )
        db.session.add(audit)
        db.session.commit()
        
        return send_file(
            report.file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{report.report_id}_{report.type}.pdf'
        )
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/reports/<report_id>/status', methods=['GET'])
@authenticate
def get_report_status(report_id):
    """Check generation status and download URL."""
    try:
        # Search by both id and report_id
        report = db.session.query(Report).filter(
            or_(Report.id == report_id, Report.report_id == report_id)
        ).first()
        
        if not report:
            return error_response('NotFound', 'Report not found', 404)
        
        response = {
            'report_id': report.report_id,
            'status': report.status,
            'type': report.type,
            'requested_at': report.created_at.isoformat() if report.created_at else None,
            'generated_at': report.generated_at.isoformat() if report.generated_at else None
        }
        
        if report.status == 'completed':
            response['download_url'] = f'/api/reports/{report.report_id}/download'
            response['file_size'] = report.file_size
        elif report.status == 'failed':
            response['error_message'] = report.error_message
        
        return success_response(response)
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/reports/<report_id>', methods=['GET'])
@authenticate
def get_report(report_id):
    """Get report metadata and details."""
    try:
        # Search by both id and report_id
        report = db.session.query(Report).filter(
            or_(Report.id == report_id, Report.report_id == report_id)
        ).first()
        
        if not report:
            return error_response('NotFound', 'Report not found', 404)
        
        return success_response({
            'id': report.id,
            'report_id': report.report_id,
            'type': report.type,
            'format': report.format,
            'status': report.status,
            'requested_by': report.requested_by.username if report.requested_by else None,
            'created_at': report.created_at.isoformat() if report.created_at else None,
            'generated_at': report.generated_at.isoformat() if report.generated_at else None,
            'file_size': report.file_size,
            'date_from': report.date_from.isoformat() if report.date_from else None,
            'date_to': report.date_to.isoformat() if report.date_to else None
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/reports', methods=['GET'])
@authenticate
def list_reports():
    """List all reports for current user or team."""
    try:
        # Get reports for user
        reports = db.session.query(Report).filter(
            Report.requested_by_id == g.user.id
        ).order_by(Report.created_at.desc()).limit(50).all()
        
        items = []
        for report in reports:
            items.append({
                'report_id': report.report_id,
                'type': report.type,
                'status': report.status,
                'created_at': report.created_at.isoformat() if report.created_at else None,
                'generated_at': report.generated_at.isoformat() if report.generated_at else None,
                'file_size': report.file_size
            })
        
        return success_response({
            'items': items,
            'total': len(items)
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)
