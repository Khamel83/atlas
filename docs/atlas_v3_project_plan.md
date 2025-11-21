# Atlas v3 - Universal Content Processing System

## Project Overview

Atlas v3 is a complete rebuild focused on reliable content ingestion and processing. This version aims to integrate with existing workflows like Hyperduck → Velja → Downie to provide seamless content processing for non-video content while preserving existing video download workflows.

### Key Goals
- Reliable content ingestion without URL scheme complexities
- Smart content routing (videos to Downie, everything else to Atlas)
- Preservation of existing working workflows
- Scalable content processing architecture

### Project Status
**Status**: Planning
**Priority**: High
**Created**: October 6, 2025

---

## Core Architecture Tasks

### 1. Design Atlas v3 Core Architecture
**Priority**: High
**Status**: TODO

Design the core architecture for Atlas v3 focusing on:
- Simple, reliable content ingestion endpoints
- Content type detection and routing
- Integration with existing macOS workflows
- Scalable processing pipeline
- Clean separation from v2 complexity

**Architecture Principles**:
- Minimal moving parts
- Leverage existing working tools (Hyperduck/Velja)
- Content-aware routing
- Robust error handling and recovery
- Clear ingestion API endpoints

---

## Integration Strategy Tasks

### 2. Document Hyperduck/Velja/Downie Integration Strategy
**Priority**: High
**Status**: TODO

Research and document how to integrate Atlas v3 with the existing Hyperduck → Velja → Downie workflow to create a universal content ingestion pipeline.

#### Current Workflow Analysis
- **Hyperduck (iOS)**: Sends links via iCloud to Mac
- **Velja (Mac)**: Intercepts and routes ALL links to Downie
- **Downie**: Downloads videos reliably

#### Desired Workflow
- **Video links** → Downie (preserve existing behavior)
- **Non-video links** → Atlas v3 for content processing
- Maintain reliability of iCloud-based link sharing

#### Research Areas
- Velja automation capabilities (AppleScript, shell commands)
- Downie content detection and routing possibilities
- Custom URL schemes or integration features
- Content type detection strategies
- "Outside the bun" solutions found on Reddit

#### Deliverables
- Complete integration architecture document
- Implementation approach recommendation
- Risk assessment and fallback strategies

---

## Research Tasks

### 3. Research Reddit Hyperduck/Velja Integration Findings
**Priority**: Medium
**Status**: TODO

Find and analyze the Reddit discussion about Hyperduck and Velja integration that mentioned "outside the bun" solutions or clever workflow automation.

#### Research Focus
- Sindre Sorhus app integration patterns
- Advanced Velja routing capabilities
- Hyperduck automation features
- User-built workflows and solutions
- Non-obvious integration techniques

#### Deliverables
- Summary of Reddit findings
- Key insights for Atlas v3 integration
- Recommended approaches based on community solutions

---

## Implementation Roadmap

### Phase 1: Research & Architecture (Week 1)
1. **Complete Reddit research** - Find integration insights
2. **Document integration strategy** - Full technical plan
3. **Design core architecture** - System design and endpoints

### Phase 2: Prototype Development (Week 2)
1. **Build ingestion endpoints** - Simple URL接收 API
2. **Content type detection** - Smart routing logic
3. **Velja integration** - Automation and routing

### Phase 3: Testing & Refinement (Week 3)
1. **End-to-end testing** - Full workflow validation
2. **Error handling** - Robust fallback mechanisms
3. **Performance optimization** - Scalability improvements

### Phase 4: Deployment & Migration (Week 4)
1. **Production deployment** - Stable Atlas v3 system
2. **Workflow migration** - Smooth transition from v2
3. **Documentation** - User guides and API docs

---

## Integration Technical Considerations

### Velja Integration Points
- **AppleScript support** - Automation capabilities
- **Shell command execution** - Custom routing logic
- **URL scheme interception** - Content-based routing
- **Custom rules engine** - Advanced filtering

### Content Detection Strategies
- **URL pattern matching** - Video vs. content detection
- **HTTP HEAD requests** - Content type analysis
- **Domain whitelisting** - Known content sources
- **Machine learning** - Advanced classification (future)

### Fallback Mechanisms
- **Manual routing** - User override capabilities
- **Dual processing** - Send to both systems temporarily
- **Error recovery** - Graceful degradation
- **Logging & monitoring** - Track routing decisions

---

## Success Metrics

### Technical Metrics
- **Uptime**: 99.9%+ availability
- **Processing speed**: < 5 seconds from URL to processed content
- **Accuracy**: 95%+ correct content routing
- **Error rate**: < 1% failed processing attempts

### User Experience Metrics
- **Workflow preservation**: Zero disruption to existing video downloads
- **Reliability**: Consistent content processing without failures
- **Simplicity**: Minimal configuration required
- **Transparency**: Clear visibility into routing decisions

---

## Risk Assessment & Mitigation

### High Risks
1. **Velja automation limitations**
   - **Mitigation**: Research alternative automation tools
   - **Fallback**: Manual URL forwarding system

2. **Content detection accuracy**
   - **Mitigation**: Multi-layered detection approach
   - **Fallback**: User-defined routing rules

### Medium Risks
1. **Integration complexity**
   - **Mitigation**: Start with simple implementation
   - **Fallback**: Separate ingestion endpoints

2. **Performance bottlenecks**
   - **Mitigation**: Asynchronous processing architecture
   - **Fallback**: Queue-based processing

---

## Next Actions

### Immediate (This Week)
1. [ ] **Research Reddit findings** - Locate integration insights
2. [ ] **Document integration strategy** - Complete technical plan
3. [ ] **Design core architecture** - System specifications

### Short Term (Next 2 Weeks)
1. [ ] **Build ingestion prototype** - Basic URL接收 system
2. [ ] **Implement content detection** - Smart routing logic
3. [ ] **Test Velja integration** - Automation proof-of-concept

### Long Term (Next Month)
1. [ ] **Deploy production system** - Stable Atlas v3
2. [ ] **Migrate from v2** - Preserve existing data
3. [ ] **Optimize performance** - Scale for production use

---

## Project Resources

### Code Repository
- **Location**: `/home/ubuntu/dev/atlas/`
- **Current State**: v2 broken (see CLAUDE.md for details)
- **Database**: 25,831 content records to preserve

### Documentation
- **Current Status**: `rebuild_100225.md` - Complete audit
- **Architecture Decisions**: This document
- **Integration Plan**: Task #2 deliverable

### External Tools & Dependencies
- **Hyperduck**: iOS app for link sharing
- **Velja**: Mac app for URL routing and automation
- **Downie**: Video download tool (preserve existing workflow)
- **iCloud**: Link synchronization between iOS and Mac

---

## Contact & Collaboration

**Project Lead**: User
**AI Assistant**: Claude Code
**Status**: Ready for development when project owner returns

**Next Review**: After completion of research tasks
**Target Launch**: 4 weeks from project start

---

*Last Updated: October 6, 2025*
*Project Status: Planning - Ready for Development*