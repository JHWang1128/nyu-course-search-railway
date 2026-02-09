from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    saved_courses = relationship("SavedCourse", back_populates="user")
    feedback = relationship("CourseFeedback", back_populates="user")

class AppConfig(Base):
    __tablename__ = "app_config"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VerificationToken(Base):
    __tablename__ = "verification_tokens"
    email = Column(String, primary_key=True, index=True)
    token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)

class Course(Base):
    __tablename__ = "courses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_code = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    embedding = Column(Vector(768)) # Nomic embedding dimension
    catalog_data = Column(JSONB)
    updated_at = Column(DateTime, default=datetime.utcnow)

    saved_by = relationship("SavedCourse", back_populates="course")
    feedback = relationship("CourseFeedback", back_populates="course")

class SavedCourse(Base):
    __tablename__ = "saved_courses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="saved_courses")
    course = relationship("Course", back_populates="saved_by")

class CourseFeedback(Base):
    __tablename__ = "course_feedback"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"))
    is_positive = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="feedback")
    course = relationship("Course", back_populates="feedback")
