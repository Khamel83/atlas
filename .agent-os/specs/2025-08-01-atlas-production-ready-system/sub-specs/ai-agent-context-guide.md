# AI Agent Context Guide

This guide ensures any AI agent can execute Atlas tasks effectively by providing the exact context, files, and knowledge needed for each task type.

## Context Loading Strategy

### **Pre-Task Context Requirements**
Every AI agent must load this core context before starting any task:

#### **Always Required Files**
```
@.agent-os/product/mission-lite.md          # Core purpose and goals
@.agent-os/product/tech-stack.md            # Technical decisions and tools
@.agent-os/specs/2025-08-01-atlas-production-ready-system/spec-lite.md
```

#### **Phase-Specific Context**
```
Phase 1: @.agent-os/specs/.../sub-specs/technical-spec.md (Infrastructure section)
Phase 2: @.agent-os/specs/.../sub-specs/technical-spec.md (Performance section)
Phase 3: @.agent-os/specs/.../sub-specs/api-spec.md (Complete API specification)
Phase 4: @.agent-os/specs/.../sub-specs/reliability-best-practices.md
Phase 5: @.agent-os/specs/.../sub-specs/github-automation.md
Phase 6: All previous specs for comprehensive testing
```

## Task-Type Specific Context

### **Type 1: Test-First Implementation (TFI)**

#### **Required Context**
- **Current codebase**: Read relevant source files in helpers/, web/, ask/ directories
- **Existing tests**: Examine tests/ directory structure and patterns
- **Test framework**: Review conftest.py and existing test utilities

#### **Context Loading Pattern**
```python
# Step 1: Understand the feature area
Read: helpers/{relevant_module}.py
Read: tests/unit/test_{relevant_module}.py (if exists)

# Step 2: Understand testing patterns
Read: tests/conftest.py
Read: pytest.ini
Scan: tests/ directory structure

# Step 3: Understand integration points
Read: Related modules that will be called
Read: Any existing API endpoints in web/app.py
```

#### **Knowledge Requirements**
- **Testing Philosophy**: Atlas uses pytest with 90%+ coverage requirement
- **Code Style**: Black formatting, type hints required, docstrings for public functions
- **Error Handling**: All functions must handle failures gracefully with clear messages

### **Type 2: Configuration & Setup (CAS)**

#### **Required Context**
- **Current configuration**: .env.example, config/ directory
- **Deployment target**: Raspberry Pi constraints and capabilities
- **External dependencies**: requirements.txt and system dependencies

#### **Context Loading Pattern**
```python
# Step 1: Understand current configuration
Read: .env.example
Read: helpers/config.py
Scan: config/ directory

# Step 2: Understand deployment environment
Read: Dockerfile (if exists)
Read: scripts/ directory for existing setup scripts
Read: @.agent-os/specs/.../sub-specs/reliability-best-practices.md

# Step 3: Understand integration requirements
Read: Requirements for the specific service being configured
Check: Dependencies in requirements.txt
```

#### **Knowledge Requirements**
- **Environment Philosophy**: Local-first, privacy-preserving, minimal external dependencies
- **Resource Constraints**: Must work on Raspberry Pi 4 with limited resources
- **Security Requirements**: Secure by default, no unnecessary network exposure

### **Type 3: Integration & Connection (IAC)**

#### **Required Context**
- **System architecture**: How components interact
- **Data flow**: How data moves through the system
- **Error handling**: How failures propagate and are handled

#### **Context Loading Pattern**
```python
# Step 1: Understand system architecture
Read: README.md (system overview)
Read: All relevant modules being integrated
Scan: Database schema and relationships

# Step 2: Understand data flow
Read: helpers/base_ingestor.py (processing patterns)
Read: web/app.py (API patterns)
Read: ask/ modules (cognitive processing patterns)

# Step 3: Understand existing integrations
Read: Related integration code
Read: Error handling patterns in helpers/error_handler.py
```

#### **Knowledge Requirements**
- **Integration Patterns**: Template method pattern, strategy pattern usage
- **Data Consistency**: How to maintain data integrity across components
- **Performance Considerations**: Caching, async processing, resource management

### **Type 4: Documentation & Process (DAP)**

#### **Required Context**
- **Current documentation**: All existing docs/ and README files
- **Code implementation**: The actual working code to document
- **User workflows**: How features are intended to be used

#### **Context Loading Pattern**
```python
# Step 1: Survey existing documentation
Read: README.md
Scan: docs/ directory
Read: API documentation (if exists)

# Step 2: Understand implementation
Read: All source code for features being documented
Read: Tests to understand expected behavior
Read: Configuration files to understand options

# Step 3: Understand user perspective
Read: @.agent-os/product/mission.md (user stories)
Read: Existing user-facing documentation
Consider: Setup and troubleshooting scenarios
```

## Phase-Specific Context Requirements

### **Phase 1: Infrastructure Stabilization**

#### **Critical Knowledge**
- **Current State**: What's working vs. what's broken in existing system
- **Testing Gaps**: Why current tests fail and what needs fixing
- **Environment Issues**: Common setup problems and their solutions

#### **Key Files to Always Read**
```
helpers/config.py                    # Current configuration system
tests/conftest.py                   # Testing setup and fixtures
scripts/ directory                  # Existing automation scripts
.env.example                        # Environment configuration template
requirements.txt                    # Current dependencies
```

### **Phase 2: Core Feature Completion**

#### **Critical Knowledge**
- **Content Processing Pipeline**: How articles, videos, podcasts are processed
- **Cognitive Features**: How the 5 ask modules work and integrate
- **Performance Bottlenecks**: Known slow areas and optimization opportunities

#### **Key Files to Always Read**
```
helpers/article_fetcher.py          # Content ingestion patterns
ask/ all modules                    # Cognitive amplification features
helpers/metadata_manager.py         # Data access patterns
web/app.py                         # Current API structure
```

### **Phase 3: API Development**

#### **Critical Knowledge**
- **Existing API Patterns**: How web/app.py currently structures endpoints
- **Authentication Philosophy**: Personal use vs. secure access for other projects
- **Data Serialization**: How to expose internal data structures via API

#### **Key Files to Always Read**
```
web/app.py                         # Existing API implementation
helpers/metadata_manager.py        # Data access layer
@.agent-os/specs/.../sub-specs/api-spec.md  # Complete API requirements
ask/ all modules                   # Features to expose via API
```

### **Phase 4: Production Hardening**

#### **Critical Knowledge**
- **Deployment Environment**: Raspberry Pi constraints and systemd integration
- **Monitoring Philosophy**: What to monitor and how to alert
- **Backup Strategy**: What data is critical and how to preserve it

#### **Key Files to Always Read**
```
@.agent-os/specs/.../sub-specs/reliability-best-practices.md
scripts/ directory                  # Existing automation
Existing deployment files          # Docker, systemd configurations
Database schema files              # What needs backing up
```

### **Phase 5: Documentation & Automation**

#### **Critical Knowledge**
- **Complete System Understanding**: How all pieces work together
- **User Workflows**: Complete setup and usage procedures
- **Development Workflows**: How to maintain and extend the system

#### **Key Files to Always Read**
```
All previous documentation          # Complete system knowledge required
GitHub Actions workflows           # Existing automation patterns
scripts/ directory                 # All automation scripts
All source code                    # For accurate documentation
```

### **Phase 6: Final Integration & Testing**

#### **Critical Knowledge**
- **System Boundaries**: What constitutes complete functionality
- **Performance Expectations**: Realistic performance on target hardware
- **Production Readiness**: Security, reliability, maintainability standards

#### **Key Files to Always Read**
```
All specifications                  # Complete requirements knowledge
All source code                   # Full system understanding
All tests                        # Existing validation approaches
Production configuration          # Deployment and operational setup
```

## Context Management Best Practices

### **Before Starting Any Task**
1. **Load Core Context**: Always read mission-lite.md, tech-stack.md, spec-lite.md
2. **Identify Task Type**: TFI, CAS, IAC, or DAP - load appropriate context
3. **Check Dependencies**: Verify prerequisite tasks are actually complete
4. **Load Phase Context**: Read phase-specific documentation
5. **Survey Existing Code**: Understand current implementation patterns

### **During Task Execution**
1. **Maintain Context**: Don't lose sight of overall goals and constraints
2. **Document Decisions**: Record why specific approaches were chosen
3. **Test Assumptions**: Verify that prerequisites actually work as expected
4. **Follow Patterns**: Use existing code patterns and conventions

### **After Task Completion**
1. **Update Context**: Document any learnings or gotchas discovered
2. **Validate Integration**: Ensure task doesn't break existing functionality
3. **Update Documentation**: Keep context current for future agents
4. **Mark Dependencies**: Update dependency status for downstream tasks

## Common Context Pitfalls

### **Insufficient Context Loading**
- **Problem**: Starting task without understanding system architecture
- **Solution**: Always read mission, tech-stack, and related source files first

### **Outdated Context**
- **Problem**: Using old documentation that doesn't match current code
- **Solution**: Prioritize source code truth over documentation when conflicts exist

### **Missing Integration Context**
- **Problem**: Building features that don't integrate well with existing system
- **Solution**: Always understand how new work connects to existing patterns

### **Scope Creep from Insufficient Context**
- **Problem**: Task becomes much larger when implementation details are discovered
- **Solution**: Survey complete requirement before starting implementation

This context guide ensures consistent, high-quality task execution regardless of which AI agent is performing the work.