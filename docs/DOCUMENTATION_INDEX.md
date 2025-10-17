# 📚 Atlas Documentation Index

**Navigate to any Atlas documentation within 3 clicks**

## 🎉 Atlas is 100% Production Ready!

**New users start here:**
- **[Quick Start Guide](../quick_start_package/QUICK_START.md)** - Get Atlas running in 10 minutes
- **[One-Command Install](../quick_install.sh)** - Automated setup script
- **[Apple Shortcuts](../shortcuts/)** - Install from phone: `./get_mobile_url.sh` or computer: `./install_shortcuts.sh`

## 🚀 Getting Started

### Essential First Steps
- **[Setup Guide](user-guides/SETUP_GUIDE.md)** - Complete system installation for non-technical users
- **[Mac User Guide](user-guides/MAC_USER_GUIDE.md)** - Mac-specific integration and shortcuts
- **[Quick Start: Add Your First Content](user-guides/INGESTION_GUIDE.md#quick-start-add-your-first-content-5-minute-tutorial)** - Get content into Atlas in 10 minutes

## 📖 User Guides

### Content & Ingestion
- **[Ingestion Guide](user-guides/INGESTION_GUIDE.md)** - Every way to get content into Atlas
- **[Mobile Guide](user-guides/MOBILE_GUIDE.md)** - Using Atlas on iPhone and iPad
- **[Automation Guide](user-guides/AUTOMATION_GUIDE.md)** - Set up automated content workflows

### Discovery & Search
- **[Search Guide](user-guides/SEARCH_GUIDE.md)** - Finding and exploring your content
- **[Web Dashboard Guide](user-guides/WEB_DASHBOARD_GUIDE.md)** - Using Atlas cognitive features

### Maintenance
- **[Maintenance Guide](user-guides/MAINTENANCE_GUIDE.md)** - System upkeep and data protection

## 🛠️ Technical Documentation

### System Architecture
- **[CLAUDE.md](CLAUDE.md)** - Project context and development guidelines
- **[Atlas Implementation Status](ATLAS_IMPLEMENTATION_STATUS.md)** - Detailed feature inventory
- **[Component Index](ATLAS_COMPONENT_INDEX.md)** - All system components

### API & Development
- **[API Documentation](api/)** - FastAPI endpoints and examples
- **[Configuration Guide](helpers/config.py)** - Environment variables and settings

## 🔧 Troubleshooting

### Common Issues
- **[System Health Check](helpers/resource_monitor.py)** - Diagnose system issues
- **[Atlas Status](atlas_status.py)** - Check service status
- **[Process Management](helpers/bulletproof_process_manager.py)** - Memory and process monitoring

### Emergency Procedures
```bash
# Emergency stop everything
sudo systemctl stop atlas.service
pkill -f "atlas_"

# Check system health
./venv/bin/python helpers/resource_monitor.py

# Restart services
sudo systemctl start atlas.service
```

## 🎯 Quick Navigation

### By User Type
- **New Users**: [Setup Guide](docs/user-guides/SETUP_GUIDE.md) → [Mac User Guide](docs/user-guides/MAC_USER_GUIDE.md) → [Ingestion Guide](docs/user-guides/INGESTION_GUIDE.md)
- **Power Users**: [Automation Guide](docs/user-guides/AUTOMATION_GUIDE.md) → [Search Guide](docs/user-guides/SEARCH_GUIDE.md) → [Maintenance Guide](docs/user-guides/MAINTENANCE_GUIDE.md)
- **Developers**: [CLAUDE.md](CLAUDE.md) → [API Documentation](api/) → [Component Index](ATLAS_COMPONENT_INDEX.md)

### By Task
- **Installing Atlas**: [Setup Guide](docs/user-guides/SETUP_GUIDE.md)
- **Adding Content**: [Ingestion Guide](docs/user-guides/INGESTION_GUIDE.md)
- **Finding Content**: [Search Guide](docs/user-guides/SEARCH_GUIDE.md)
- **Using on Phone**: [Mobile Guide](docs/user-guides/MOBILE_GUIDE.md)
- **Automating Workflows**: [Automation Guide](docs/user-guides/AUTOMATION_GUIDE.md)
- **System Maintenance**: [Maintenance Guide](docs/user-guides/MAINTENANCE_GUIDE.md)

## 📱 Platform-Specific Guides

### macOS
- [Mac User Guide](docs/user-guides/MAC_USER_GUIDE.md) - Apple Shortcuts, Safari integration
- [Apple Shortcuts](apple_shortcuts/) - Ready-to-install shortcuts

### iOS/iPadOS
- [Mobile Guide](docs/user-guides/MOBILE_GUIDE.md) - iPhone/iPad workflows
- [Voice Commands & Siri](docs/user-guides/MOBILE_GUIDE.md#voice-commands) - Hands-free content capture

## 🔍 Search Documentation

Can't find what you're looking for? Use these commands:

```bash
# Search all documentation
grep -r "your search term" docs/

# Search user guides only
grep -r "your search term" docs/user-guides/

# Search technical docs
grep -r "your search term" *.md helpers/
```

## 📊 Documentation Stats

- **User Guides**: 8 comprehensive guides
- **Total Pages**: 450+ pages of documentation
- **Last Updated**: August 28, 2025
- **Maintenance**: Documentation updated automatically with system changes

---

**💡 Tip**: Bookmark this page for instant access to all Atlas documentation!