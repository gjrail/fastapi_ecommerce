from datetime import datetime

from sqlalchemy import Boolean, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, relationship

from app.database import Base


class Review(Base):
    __tablename__ = 'reviews'

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    product_id = mapped_column(Integer, ForeignKey('products.id'), nullable=False)
    comment = mapped_column(Text, nullable=True)
    comment_date = mapped_column(DateTime, default=datetime.now)
    grade = mapped_column(Integer, nullable=False)
    is_active = mapped_column(Boolean, default=True)

    user = relationship('User', back_populates='reviews')
    product = relationship('Product', back_populates='reviews')
