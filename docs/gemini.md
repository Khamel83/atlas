# Gemini Agent Instructions for Atlas

**📚 PRIMARY REFERENCE**: Check `agents.md` for complete development guidelines.

## 🚨 CRITICAL DATABASE REQUIREMENT

**MANDATORY**: Use centralized database configuration ALWAYS. User content depends on this.

```python
# ✅ ALWAYS USE
from helpers.database_config import get_database_path, get_database_connection

conn = get_database_connection()
```

**❌ NEVER USE**: Hardcoded paths like `"data/atlas.db"` or `Path.home() / "dev" / "atlas" / "atlas.db"`

## 🎯 Gemini-Specific Guidelines

- **Multimodal Strength**: Use your vision capabilities for UI/UX improvements
- **Reasoning Excellence**: Apply systematic problem-solving to Atlas architecture
- **Code Understanding**: Leverage your ability to understand complex codebases
- **Documentation**: Always update both CLAUDE.md and agents.md when making changes

## 🗃️ Database Usage Pattern

```python
def gemini_atlas_function():
    """Example pattern for Gemini implementations"""
    from helpers.database_config import get_database_connection

    with get_database_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM content WHERE ...")
        return cursor.fetchall()
```

## 🤖 Archon Integration

Use MCP tools for task management:
- `mcp__archon__list_tasks` - Get tasks to work on
- `mcp__archon__update_task` - Update task status
- `mcp__archon__perform_rag_query` - Search knowledge base

## 🚀 Quick Commands

```bash
# Check database path
python3 -c "from helpers.database_config import get_database_path; print(get_database_path())"

# System health
python atlas_status.py --detailed

# Run tests
python3 -m pytest tests/test_web_endpoints.py -v
```

## 📝 Development Rules

1. **Always check agents.md first** - Complete guidelines there
2. **Use centralized database config** - Critical requirement
3. **Update documentation in sync** - CLAUDE.md + agents.md simultaneously
4. **Test thoroughly** - Atlas has automated testing framework
5. **Follow existing patterns** - Check existing code before creating new patterns

## 🔍 Gemini Advantages for Atlas

- **UI Analysis**: Can analyze screenshots and suggest improvements
- **Code Review**: Strong at finding patterns and inconsistencies
- **Architecture**: Good at understanding system-level relationships
- **Problem Solving**: Systematic approach to complex debugging

**Remember**: Database consistency prevents critical user-facing failures. This is non-negotiable.