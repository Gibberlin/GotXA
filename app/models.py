"""
SQLAlchemy ORM models for SIEM/SOAR platform.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Index, func

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
        Index('idx_logs_host', 'host'),
        Index('idx_logs_level', 'level'),
        Index('idx_logs_timestamp', 'timestamp'),
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
    
    __table_args__ = (
        Index('idx_alerts_host', 'host'),
        Index('idx_alerts_severity', 'severity'),
        Index('idx_alerts_timestamp', 'timestamp'),
        Index('idx_alerts_status', 'status'),
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
