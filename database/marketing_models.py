"""Stub for marketing database models."""
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.orm import declarative_base

try:
    from database.models import Base
except ImportError:
    Base = declarative_base()

class Prospect(Base):
    __tablename__ = "prospects"
    __table_args__ = {"extend_existing": True}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), default="")
    email = Column(String(255), default="")
    phone = Column(String(50), default="")
    company = Column(String(255), default="")
    score = Column(Float, default=0.0)
    status = Column(String(50), default="new")
    source = Column(String(100), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = {"extend_existing": True}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), default="")
    status = Column(String(50), default="draft")
    channel = Column(String(100), default="")
    budget = Column(Float, default=0.0)
    spent = Column(Float, default=0.0)
    leads = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    created_at = Column(DateTime)

class MarketingMetric(Base):
    __tablename__ = "marketing_metrics"
    __table_args__ = {"extend_existing": True}
    
    id = Column(Integer, primary_key=True)
    metric_name = Column(String(255))
    metric_value = Column(Float, default=0.0)
    recorded_at = Column(DateTime)
