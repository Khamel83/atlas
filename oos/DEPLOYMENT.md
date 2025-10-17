# OOS Context Engineering - Deployment Guide

## 🎯 Deployment Options

### Option 1: MCP Server (Recommended for Claude Code)

This integrates directly with Claude Code to provide slash commands and automatic optimization.

#### Setup Steps

1. **Locate Your Claude Code MCP Configuration**
   ```bash
   # Usually located at:
   # macOS: ~/Library/Application Support/Claude/mcp_settings.json
   # Linux: ~/.config/Claude/mcp_settings.json
   # Windows: %APPDATA%/Claude/mcp_settings.json
   ```

2. **Add OOS Context Engineering Server**
   ```json
   {
     "mcpServers": {
       "oos-context": {
         "command": "python3",
         "args": ["/path/to/your/oos/mcp_server.py"],
         "cwd": "/path/to/your/oos",
         "env": {
           "PYTHONPATH": "/path/to/your/oos/src"
         }
       }
     }
   }
   ```

3. **Install Dependencies**
   ```bash
   cd /path/to/your/oos
   pip install fastapi uvicorn pydantic
   ```

4. **Restart Claude Code**
   - Close Claude Code completely
   - Reopen Claude Code
   - Slash commands should now be available

#### Verification
Test with: `/help-me test the context engineering system`

### Option 2: Standalone Tools (For Terminal Users)

If you prefer to use the tools directly:

1. **Set Up Python Environment**
   ```bash
   cd /path/to/your/oos
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or venv\Scripts\activate  # Windows
   pip install -r requirements/base.txt
   ```

2. **Test Core Components**
   ```bash
   # Test clarification workflow
   python3 bin/clarification_cli.py

   # Test code health tools
   ./bin/oos-doctor

   # Test token optimization
   python3 -m src.token_optimization --test
   ```

## 🔧 Configuration

### Environment Variables
```bash
# Optional: Set custom configuration
export OOS_CONTEXT_BUDGET=4000        # Default token budget
export OOS_AUTO_OPTIMIZE=true         # Enable auto-optimization
export OOS_LOG_LEVEL=info             # Logging level
export OOS_CACHE_DIR=/tmp/oos-cache    # Cache directory
```

### Configuration File
Create `config/context_engineering.json`:
```json
{
  "token_budget": 4000,
  "auto_optimize": true,
  "optimization_strategies": [
    "text_compression",
    "code_compression",
    "filesystem_offloading"
  ],
  "clarification_confidence_threshold": 0.7,
  "meta_ai_enabled": true,
  "auto_documentation": true
}
```

## 🚀 Testing Your Installation

### Quick Test Suite
```bash
# Run all context engineering tests
python3 -m pytest tests/test_context_engineering.py -v

# Test individual components
python3 -c "
from src.clarification_workflow import get_clarification_workflow
from src.token_optimization import estimate_context_tokens
print('✅ Context engineering components loaded successfully')
"
```

### Interactive Test
```bash
# Start clarification CLI
python3 bin/clarification_cli.py

# Choose option 1, enter: "I want to optimize my database"
# Verify it generates clarification questions
# Choose option 2 to test meta-AI prompt generation
```

### Claude Code Integration Test
In Claude Code:
```
/help-me test the context engineering integration
```

Should respond with analysis, optimization, and structured assistance.

## 🔍 Troubleshooting

### Common Issues

#### 1. "Command not found" errors
```bash
# Ensure Python 3.7+ is installed
python3 --version

# Install missing dependencies
pip install -r requirements/base.txt
```

#### 2. MCP Server not loading
- Check file paths are absolute in MCP configuration
- Verify Python can import modules: `python3 -c "import sys; sys.path.insert(0, 'src'); from clarification_workflow import *"`
- Check Claude Code logs for MCP errors

#### 3. Import errors
```bash
# Fix Python path
export PYTHONPATH="/path/to/your/oos/src:$PYTHONPATH"

# Or add to your shell profile
echo 'export PYTHONPATH="/path/to/your/oos/src:$PYTHONPATH"' >> ~/.bashrc
```

#### 4. Permission errors
```bash
# Make scripts executable
chmod +x bin/*

# Fix ownership if needed
sudo chown -R $USER:$USER /path/to/your/oos
```

### Debug Mode
Enable detailed logging:
```bash
export OOS_LOG_LEVEL=debug
export OOS_DEBUG=true
```

### Health Check
```bash
# Run system health check
./bin/oos-doctor

# This will verify:
# - All dependencies installed
# - Python modules can be imported
# - Configuration is valid
# - Git integration works
# - File permissions are correct
```

## 📊 Performance Tuning

### Token Budget Optimization
```json
{
  "token_budget": 6000,          // Higher for complex projects
  "compression_ratio": 0.6,      // More aggressive compression
  "cache_size": 100,             // Larger cache for better performance
  "batch_optimization": true     // Process multiple requests together
}
```

### Memory Usage
```bash
# Monitor memory usage
python3 -c "
import psutil
from src.token_optimization import *
print(f'Memory usage: {psutil.Process().memory_info().rss / 1024 / 1024:.1f} MB')
"
```

## 🔄 Updates and Maintenance

### Updating OOS Context Engineering
```bash
cd /path/to/your/oos
git pull origin master

# Reinstall dependencies if needed
pip install -r requirements/base.txt

# Restart Claude Code to reload MCP server
```

### Backup Configuration
```bash
# Backup your settings
cp config/context_engineering.json config/context_engineering.json.backup
cp ~/.config/Claude/mcp_settings.json ~/.config/Claude/mcp_settings.json.backup
```

## 🎯 Production Deployment

### For Team/Organization Use

1. **Centralized MCP Server**
   ```bash
   # Run as a service
   uvicorn mcp_server:app --host 0.0.0.0 --port 8000

   # Update team Claude Code configs to point to central server
   {
     "mcpServers": {
       "oos-context": {
         "command": "curl",
         "args": ["-X", "POST", "http://your-server:8000/mcp"]
       }
     }
   }
   ```

2. **Docker Deployment**
   ```dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY . .
   RUN pip install -r requirements/base.txt
   EXPOSE 8000
   CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

3. **Environment Management**
   ```bash
   # Use environment-specific configs
   cp config/context_engineering.prod.json config/context_engineering.json
   export OOS_ENV=production
   ```

## ✅ Success Checklist

After deployment, verify:

- [ ] `/help-me` command works in Claude Code
- [ ] Context optimization reduces token usage
- [ ] Meta-clarification generates external AI prompts
- [ ] Smart commit messages work with git
- [ ] Documentation checks identify missing docs
- [ ] Auto-fix resolves consistency issues
- [ ] All tests pass: `python3 -m pytest tests/`

Your OOS Context Engineering system is now ready for production use! 🎉