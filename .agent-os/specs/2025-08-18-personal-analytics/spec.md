# Personal Usage Analytics for Knowledge Optimization

**Date**: August 18, 2025
**Status**: 🎯 PLANNED
**Priority**: MEDIUM - Personal Optimization
**Parent Task**: Personal Knowledge System Completion

## Executive Summary

Create **simple usage analytics** to understand your personal knowledge consumption patterns and optimize Atlas for your actual usage. Focus on **actionable insights** rather than fancy dashboards - what content provides value, what sources are noise, and how to improve your knowledge capture workflow.

**Goal**: Provide data-driven insights to optimize your personal knowledge system based on actual usage patterns.

## Current Status Analysis

### ✅ What We Have
- Atlas ingesting articles, podcasts, transcripts automatically
- Enhanced search with speaker attribution and topics
- Daily reports showing ingestion statistics
- Background processing with comprehensive logging

### 🎯 What We Need
- **Search pattern analysis** - What you actually search for and find useful
- **Content quality scoring** - Which sources provide value vs noise
- **Usage insights** - Time spent reading, topics of interest, valuable content
- **Source optimization** - Which inputs produce high-value content
- **Personal trend analysis** - How your interests and knowledge focus evolves

## Implementation Strategy

### Phase 1: Usage Tracking (1 hour)
**Objective**: Track search queries, content access, and user interactions

**Atomic Tasks**:
1. **Search analytics tracking** (`helpers/usage_tracker.py`)
   - Log search queries and results clicked
   - Track time spent on content
   - Record successful vs unsuccessful searches
   - Content rating and feedback collection

2. **Content access logging**
   - Track which ingested content gets accessed
   - Measure content value through usage patterns
   - Identify high-value vs ignored content

### Phase 2: Quality Analysis (0.5 hours)
**Objective**: Analyze content quality and source value

**Atomic Tasks**:
1. **Source quality scoring** (`analytics/source_analyzer.py`)
   - Calculate value score per content source
   - Identify noisy vs high-signal sources
   - Track content-to-access ratios by source
   - Flag sources for optimization or removal

2. **Content quality metrics**
   - Length vs engagement correlation
   - Topic relevance to personal interests
   - Search result relevance scoring

### Phase 3: Personal Insights (0.5 hours)
**Objective**: Generate actionable insights for personal optimization

**Atomic Tasks**:
1. **Personal analytics dashboard** (`analytics/personal_insights.py`)
   - CLI-based insights report (no fancy UI)
   - Weekly/monthly usage summaries
   - Content recommendation optimization
   - Personal knowledge gap identification

2. **Optimization recommendations**
   - Source filtering suggestions
   - Search query improvement tips
   - Content discovery optimization
   - Knowledge capture workflow refinements

## Expected Outcomes

### Usage Understanding
- **Search patterns**: What you actually look for in your knowledge base
- **Content value**: Which ingested content provides real value
- **Time allocation**: How much time spent on different content types
- **Interest evolution**: How your knowledge focus changes over time

### Optimization Insights
- **Source tuning**: Remove noisy sources, amplify valuable ones
- **Search improvement**: Better queries based on successful patterns
- **Content curation**: Focus ingestion on actually useful sources
- **Workflow refinement**: Optimize capture and discovery processes

### Personal Trends
- **Knowledge growth**: Track expansion of expertise areas
- **Interest shifts**: Identify changing focus areas
- **Learning effectiveness**: Measure knowledge retention and application
- **Content gaps**: Discover areas needing more content

## Technical Architecture

### Core Components
1. **Usage Tracker** (`helpers/usage_tracker.py`)
   ```python
   class UsageTracker:
       def log_search(self, query, results, selected_result)
       def log_content_access(self, content_id, time_spent)
       def log_content_rating(self, content_id, rating, feedback)
       def track_source_value(self, source, access_count, rating)
   ```

2. **Analytics Engine** (`analytics/personal_insights.py`)
   ```python
   class PersonalAnalytics:
       def analyze_search_patterns(self, time_period)
       def calculate_source_quality_scores(self)
       def identify_content_gaps(self)
       def generate_optimization_recommendations(self)
   ```

3. **CLI Reports** (`scripts/analytics_report.py`)
   ```bash
   python scripts/analytics_report.py --weekly
   python scripts/analytics_report.py --sources
   python scripts/analytics_report.py --optimize
   ```

### Database Schema Updates
```sql
-- Track search and usage patterns
CREATE TABLE usage_analytics (
    id INTEGER PRIMARY KEY,
    event_type TEXT, -- search, access, rating
    content_id TEXT,
    query TEXT,
    timestamp TIMESTAMP,
    metadata TEXT, -- JSON additional data
    value_score REAL
);

-- Track source quality over time
CREATE TABLE source_quality (
    source TEXT PRIMARY KEY,
    total_content INTEGER,
    accessed_content INTEGER,
    avg_rating REAL,
    quality_score REAL,
    last_updated TIMESTAMP
);
```

### Integration Points
- **Search API**: Automatic usage logging on searches
- **Content access**: Track when content is viewed/exported
- **Background service**: Periodic analytics processing
- **Daily reports**: Include analytics summary

## Success Criteria

- [ ] Search patterns tracked and analyzed for optimization
- [ ] Content quality scoring identifies valuable vs noisy sources
- [ ] Personal usage insights provide actionable recommendations
- [ ] CLI reports show meaningful trends and patterns
- [ ] Source optimization suggestions improve content quality

## Implementation Complexity

- **Low complexity**: Simple event logging and aggregation
- **No UI required**: CLI-based reports and insights
- **Privacy-focused**: All analytics stay local, personal use only
- **Actionable focus**: Insights that actually improve your workflow

---

**Expected Impact**: Data-driven optimization of personal knowledge capture and discovery based on actual usage patterns and content value.

*This task focuses on personal optimization insights, not general analytics or user tracking.*