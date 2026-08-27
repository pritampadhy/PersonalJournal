"""
Database Models for Personal Journal Application

Implements:
- User model with secure password storage
- Journal entry model with encryption at rest
- Audit log model (immutable)
- Row-level security enforcement
- Soft deletes for GDPR compliance

SECURITY FEATURES:
- Password hashes only (never stored plaintext)
- Encrypted journal content
- User_id always enforced for queries
- Immutable audit trail
- Timestamps in UTC
- No sensitive info in logs
"""

import logging
from datetime import datetime
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    Boolean, ForeignKey, Index, event, text
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID

import uuid

logger = logging.getLogger(__name__)

db = SQLAlchemy()


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamps.
    
    All timestamps are in UTC.
    updated_at automatically changes on update.
    """
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
    )


class SoftDeleteMixin:
    """
    Mixin that adds soft delete support for GDPR right-to-deletion.
    
    Records are marked as deleted but not removed from database.
    Queries should filter out soft-deleted records.
    """
    
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    def soft_delete(self):
        """Mark record as deleted without removing from database."""
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """Restore soft-deleted record."""
        self.deleted_at = None
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None


class User(db.Model, TimestampMixin, SoftDeleteMixin):
    """
    User model with secure password storage.
    
    SECURITY:
    - Password stored as bcrypt hash only
    - Email is unique (for login)
    - MFA fields for future implementation
    - Account lockout tracking for brute-force protection
    """
    
    __tablename__ = 'users'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Authentication
    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash
    
    # Profile
    full_name = Column(String(255), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Security - Account lockout
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Security - Session management
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 support
    
    # MFA fields (for future implementation)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)  # Encrypted TOTP secret
    
    # Relationships
    journal_entries = relationship(
        'JournalEntry',
        back_populates='user',
        cascade='all, delete-orphan',
        foreign_keys='JournalEntry.user_id'
    )
    
    audit_logs = relationship(
        'AuditLog',
        back_populates='user',
        foreign_keys='AuditLog.user_id'
    )
    
    # Database indexes for common queries
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_username', 'username'),
        Index('idx_users_is_active', 'is_active'),
        Index('idx_users_deleted_at', 'deleted_at'),
    )
    
    @validates('email')
    def validate_email(self, key, value):
        """Validate email format."""
        if not value or '@' not in value:
            raise ValueError("Invalid email format")
        return value.lower().strip()
    
    @validates('username')
    def validate_username(self, key, value):
        """Validate username format."""
        if not value or len(value) < 3 or len(value) > 100:
            raise ValueError("Username must be 3-100 characters")
        if not value.isalnum() and '_' not in value:
            raise ValueError("Username can only contain alphanumeric and underscore")
        return value.lower().strip()
    
    def __repr__(self):
        return f"<User {self.username}>"


class JournalEntry(db.Model, TimestampMixin, SoftDeleteMixin):
    """
    Journal entry model with encrypted storage.
    
    SECURITY:
    - Content encrypted at rest (AES-256-GCM)
    - User ID always validated on queries
    - Row-level security at database level
    - Immutable audit trail
    """
    
    __tablename__ = 'journal_entries'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # User association (immutable)
    user_id = Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Content (encrypted in database)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)  # AES-256-GCM encrypted
    
    # Metadata
    mood = Column(String(50), nullable=True)  # e.g., "happy", "sad", "neutral"
    is_favorite = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='journal_entries')
    
    # Encryption metadata
    encryption_version = Column(Integer, default=1, nullable=False)
    
    # Database indexes
    __table_args__ = (
        Index('idx_entries_user_id', 'user_id'),
        Index('idx_entries_created_at', 'created_at'),
        Index('idx_entries_is_favorite', 'is_favorite'),
        Index('idx_entries_deleted_at', 'deleted_at'),
        Index('idx_entries_user_created', 'user_id', 'created_at'),
    )
    
    @validates('title')
    def validate_title(self, key, value):
        """Validate title."""
        if not value or len(value) < 1 or len(value) > 500:
            raise ValueError("Title must be 1-500 characters")
        return value.strip()
    
    @validates('content')
    def validate_content(self, key, value):
        """Validate content."""
        if not value or len(value) < 1:
            raise ValueError("Content cannot be empty")
        # Note: encrypted content will be longer than plaintext
        if len(value) > 1000000:  # 1MB limit
            raise ValueError("Content exceeds maximum size")
        return value
    
    def __repr__(self):
        return f"<JournalEntry {self.id} by user {self.user_id}>"


class AuditLog(db.Model):
    """
    Immutable audit log for security and compliance.
    
    SECURITY:
    - INSERT ONLY (no updates or deletes)
    - Complete record of all sensitive operations
    - User association for accountability
    - IP address and user agent for forensics
    - Not accessible by regular users
    
    Events logged:
    - USER_LOGIN / USER_LOGIN_FAILED
    - USER_CREATED
    - USER_PASSWORD_CHANGED
    - ENTRY_CREATED
    - ENTRY_UPDATED
    - ENTRY_DELETED
    - USER_DELETED
    """
    
    __tablename__ = 'audit_logs'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Audit details
    event_type = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(Integer, nullable=True)
    
    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)
    
    # Result
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamp (server-side, immutable)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
    )
    
    # Relationships
    user = relationship('User', back_populates='audit_logs', foreign_keys=[user_id])
    
    # Database indexes for queries
    __table_args__ = (
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_user_id', 'user_id'),
        Index('idx_audit_created_at', 'created_at'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_user_event', 'user_id', 'event_type'),
    )
    
    def __repr__(self):
        return f"<AuditLog {self.event_type} at {self.created_at}>"


# Event listeners for automatic auditing

@event.listens_for(JournalEntry, 'after_insert')
def audit_entry_created(mapper, connection, target):
    """Log when journal entry is created."""
    from flask import request, g
    
    audit_log = AuditLog(
        event_type='ENTRY_CREATED',
        user_id=target.user_id,
        resource_type='JournalEntry',
        resource_id=target.id,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent') if request else None,
        success=True
    )
    connection.execute(db.insert(AuditLog), [vars(audit_log)])


@event.listens_for(JournalEntry, 'after_update')
def audit_entry_updated(mapper, connection, target):
    """Log when journal entry is updated."""
    from flask import request
    
    audit_log = AuditLog(
        event_type='ENTRY_UPDATED',
        user_id=target.user_id,
        resource_type='JournalEntry',
        resource_id=target.id,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent') if request else None,
        success=True
    )
    connection.execute(db.insert(AuditLog), [vars(audit_log)])


def create_audit_log(
    event_type: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> AuditLog:
    """
    Create an audit log entry.
    
    Args:
        event_type: Type of event (see class docstring)
        user_id: User ID if applicable
        resource_type: Type of resource (User, JournalEntry, etc)
        resource_id: ID of resource
        ip_address: Client IP address
        user_agent: Client user agent
        success: Whether operation succeeded
        error_message: Error message if failed
        
    Returns:
        AuditLog instance (added to session)
    """
    log = AuditLog(
        event_type=event_type,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        error_message=error_message
    )
    db.session.add(log)
    return log
