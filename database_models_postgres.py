# データベースモデル（PostgreSQL対応版）
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import json
import os
from config import DATABASE_URL

Base = declarative_base()

class DocumentPattern(Base):
    """書類パターンのデータベースモデル"""
    __tablename__ = 'document_patterns'
    
    id = Column(Integer, primary_key=True)
    category = Column(String(200), nullable=False)  # 書類カテゴリ
    ocr_text_sample = Column(Text)  # OCR結果のサンプルテキスト
    regex_patterns = Column(JSONB)  # PostgreSQL用JSONB型（より高速）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    success_count = Column(Integer, default=0)  # 成功回数
    failure_count = Column(Integer, default=0)  # 失敗回数
    
    def add_pattern(self, pattern):
        """新しい正規表現パターンを追加"""
        patterns = self.regex_patterns or []
        if pattern not in patterns:
            patterns.append(pattern)
            self.regex_patterns = patterns
            
    def get_patterns(self):
        """正規表現パターンのリストを取得"""
        return self.regex_patterns or []

class ExtractionHistory(Base):
    """抽出履歴のデータベースモデル"""
    __tablename__ = 'extraction_history'
    
    id = Column(Integer, primary_key=True)
    document_category = Column(String(200))
    ocr_text = Column(Text)
    used_patterns = Column(JSONB)  # 使用した正規表現パターン
    extracted_values = Column(JSONB)  # 抽出された値
    user_corrections = Column(JSONB)  # ユーザーによる修正
    created_at = Column(DateTime, default=datetime.now)

# データベースの初期化
def init_database():
    """データベースとテーブルを初期化"""
    # 環境変数からデータベースURLを取得
    database_url = os.getenv('DATABASE_URL', DATABASE_URL)
    
    # Heroku等のpostgres://をpostgresql://に変換
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """データベースセッションを取得"""
    engine = init_database()
    Session = sessionmaker(bind=engine)
    return Session()

def find_similar_document(ocr_text, session, threshold=0.7):
    """類似した書類パターンを検索"""
    from difflib import SequenceMatcher
    
    all_patterns = session.query(DocumentPattern).all()
    best_match = None
    best_score = 0
    
    for pattern in all_patterns:
        if pattern.ocr_text_sample:
            # テキストの類似度を計算
            similarity = SequenceMatcher(None, ocr_text[:500], pattern.ocr_text_sample[:500]).ratio()
            if similarity > best_score and similarity > threshold:
                best_score = similarity
                best_match = pattern
    
    return best_match, best_score

def save_document_pattern(category, ocr_text, regex_patterns, session):
    """書類パターンを保存"""
    pattern = DocumentPattern(
        category=category,
        ocr_text_sample=ocr_text[:1000],  # 最初の1000文字を保存
        regex_patterns=regex_patterns
    )
    session.add(pattern)
    session.commit()
    return pattern

def update_pattern_success(pattern_id, session):
    """パターンの成功回数を更新"""
    pattern = session.query(DocumentPattern).get(pattern_id)
    if pattern:
        pattern.success_count += 1
        session.commit()

def update_pattern_failure(pattern_id, new_patterns, session):
    """パターンの失敗を記録し、新しいパターンを追加"""
    pattern = session.query(DocumentPattern).get(pattern_id)
    if pattern:
        pattern.failure_count += 1
        for new_pattern in new_patterns:
            pattern.add_pattern(new_pattern)
        pattern.updated_at = datetime.now()
        session.commit()
