"""
SQLAlchemy ORM models for SIEM/SOAR platform.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Log(db.Model):
    """
    Represents an ingested security event/log.
    """
    __tablename__ = 'logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    level = db.Column(db.String(10), nullable=False, default='INFO')
    message = db.Column(db.Text, nullable=False)
    host = db.Column(db.String(255), nullable=False)
    ingested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    alerts = db.relationship('Alert', backref='log', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_logs_host', 'host'),
        db.Index('idx_logs_level', 'level'),
        db.Index('idx_logs_timestamp', 'timestamp'),
    )
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level,
            'message': self.message,
            'host': self.host,
            'ingested_at': self.ingested_at.isoformat() if self.ingested_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Alert(db.Model):
    """
    Represents a triggered security alert/incident.
    """
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    host = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.String(10), nullable=False)  # HIGH, MEDIUM, LOW
    rule = db.Column(db.String(255), nullable=False)
    log_message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Open')  # Open, Investigating, Resolved
    log_id = db.Column(db.Integer, db.ForeignKey('logs.id', ondelete='CASCADE'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    soar_actions = db.relationship('SoarAction', backref='alert', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_alerts_host', 'host'),
        db.Index('idx_alerts_severity', 'severity'),
        db.Index('idx_alerts_timestamp', 'timestamp'),
        db.Index('idx_alerts_status', 'status'),
    )
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'host': self.host,
            'severity': self.severity,
            'rule': self.rule,
            'log_message': self.log_message,
            'status': self.status,
            'log_id': self.log_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SoarAction(db.Model):
    """
    Represents an automated SOAR response action taken against a detected threat.
    Every action executed by the SOAR engine is recorded here for full audit trail.
    """
    __tablename__ = 'soar_actions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alert_id = db.Column(db.Integer, db.ForeignKey('alerts.id', ondelete='CASCADE'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)       # ip_block, container_isolate, service_restart, rate_limit, credential_lock, log_escalation, monitor_escalation
    target = db.Column(db.String(255), nullable=False)            # IP address, container name, service name
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, executing, completed, failed
    description = db.Column(db.Text, nullable=False)              # Human-readable explanation
    playbook = db.Column(db.String(100), nullable=False)          # Which playbook triggered this
    executed_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    result_detail = db.Column(db.Text, nullable=True)             # Execution output / error details
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_soar_actions_alert_id', 'alert_id'),
        db.Index('idx_soar_actions_status', 'status'),
        db.Index('idx_soar_actions_action_type', 'action_type'),
        db.Index('idx_soar_actions_created_at', 'created_at'),
    )
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'action_type': self.action_type,
            'target': self.target,
            'status': self.status,
            'description': self.description,
            'playbook': self.playbook,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result_detail': self.result_detail,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
