from fastapi import APIRouter, HTTPException, Depends, Form
from pydantic import BaseModel
from typing import List, Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ask.proactive.surfacer import SurfacingContext

from ask.proactive.surfacer import SurfacingContext

from ask.proactive.surfacer import ProactiveSurfacer
from ask.temporal.temporal_engine import TemporalEngine
from ask.socratic.question_engine import QuestionEngine
from ask.recall.recall_engine import RecallEngine
from ask.insights.pattern_detector import PatternDetector
COGNITIVE_AVAILABLE = True

from helpers.metadata_manager import MetadataManager
from helpers.config import load_config

router = APIRouter()

# Dependency to get metadata manager
def get_metadata_manager():
    config = load_config()
    return MetadataManager(config)

class ProactiveItem(BaseModel):
    title: str
    updated_at: str
    relevance_score: Optional[float] = None

class TemporalRelationship(BaseModel):
    from_title: str
    to_title: str
    days_apart: int
    relationship_type: str

class SocraticQuestion(BaseModel):
    content: str
    questions: List[str]

class RecallItem(BaseModel):
    title: str
    last_reviewed: Optional[str] = None

class Pattern(BaseModel):
    tags: List[tuple]
    sources: List[tuple]

@router.get("/surface", response_model=List[ProactiveItem])
async def get_proactive_content(
    limit: int = 5,
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """Get forgotten/stale content that should be surfaced"""
    if not COGNITIVE_AVAILABLE:
        raise HTTPException(status_code=501, detail="Cognitive features not available")

    try:
        surfacer = ProactiveSurfacer(manager)
        print(f"Using SurfacingContext: {SurfacingContext}")
        forgotten = surfacer.surface_content(context=SurfacingContext(max_results=limit))

        items = []
        for item in forgotten:
            items.append(ProactiveItem(
                title=item.title,
                updated_at=item.updated_at
            ))

        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting proactive content: {str(e)}")

@router.get("/temporal", response_model=List[TemporalRelationship])
async def get_temporal_relationships(
    max_delta_days: int = 7,
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """Get temporal relationships between content items"""
    if not COGNITIVE_AVAILABLE:
        raise HTTPException(status_code=501, detail="Cognitive features not available")

    try:
        engine = TemporalEngine(manager)
        relationships = engine.get_time_aware_relationships(max_delta_days=max_delta_days)

        items = []
        for item1, item2, days in relationships:
            items.append(TemporalRelationship(
                from_title=item1.title,
                to_title=item2.title,
                days_apart=days,
                relationship_type="temporal_proximity"
            ))

        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting temporal relationships: {str(e)}")

@router.post("/socratic", response_model=SocraticQuestion)
async def generate_socratic_questions(
    content: str = Form(...),
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """Generate Socratic questions from content"""
    if not COGNITIVE_AVAILABLE:
        raise HTTPException(status_code=501, detail="Cognitive features not available")

    try:
        engine = QuestionEngine(manager)
        question_objects = engine.generate_questions(content)

        # Extract question strings from SocraticQuestion objects
        questions = [q.question for q in question_objects]

        return SocraticQuestion(content=content, questions=questions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating questions: {str(e)}")

@router.get("/recall", response_model=List[RecallItem])
async def get_recall_items(
    limit: int = 5,
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """Get items that are due for spaced repetition review"""
    if not COGNITIVE_AVAILABLE:
        raise HTTPException(status_code=501, detail="Cognitive features not available")

    try:
        engine = RecallEngine(manager)
        due_items = engine.schedule_spaced_repetition(n=limit)

        items = []
        for item in due_items:
            items.append(RecallItem(
                title=item.title,
                last_reviewed=item.type_specific.get("last_reviewed") if item.type_specific else None
            ))

        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recall items: {str(e)}")

@router.get("/patterns", response_model=Pattern)
async def get_patterns(
    limit: int = 5,
    manager: MetadataManager = Depends(get_metadata_manager)
):
    """Get top tags and sources patterns"""
    if not COGNITIVE_AVAILABLE:
        raise HTTPException(status_code=501, detail="Cognitive features not available")

    try:
        detector = PatternDetector(manager)
        patterns = detector.find_patterns(n=limit)

        return Pattern(
            tags=patterns["top_tags"],
            sources=patterns["top_sources"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting patterns: {str(e)}")