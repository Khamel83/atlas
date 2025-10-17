# Atlas Web Dashboard User Guide

## Accessing the Dashboard

To access the Atlas cognitive dashboard, open your web browser and navigate to:
```
https://atlas.khamel.com/ask/html
```

If you're accessing Atlas from another device on your network, replace `localhost` with the IP address of your Atlas server:
```
http://192.168.1.100:8000/ask/html
```

## Cognitive Features Overview

The Atlas dashboard provides access to six powerful cognitive features that help you understand and explore your content:

### 1. Proactive Content Surfacer

**Purpose**: Surfaces forgotten but relevant content from your knowledge base

The Proactive Surfacer identifies content that you may have forgotten about but is still relevant to your current interests. It helps prevent the "I know I read about this somewhere" problem by bringing forgotten insights back to your attention.

**How to use**:
1. Click "Proactive Surfacer" in the navigation menu
2. Browse the list of forgotten content items
3. Click on any item to revisit and re-engage with the content

**When to use**:
- When you're looking for information but can't remember where you saved it
- During research on a topic you've previously explored
- As a weekly/monthly review of your content library

### 2. Temporal Relationships

**Purpose**: Identifies time-based patterns and relationships in your content

The Temporal Engine analyzes when content was created or updated to identify patterns and connections between topics over time. It can reveal how your interests have evolved or highlight content that was created around the same time.

**How to use**:
1. Click "Temporal Relationships" in the navigation menu
2. Review the timeline of content relationships
3. Look for patterns in when similar topics were explored

**When to use**:
- To understand the evolution of your interests over time
- To find content created during specific periods
- To identify gaps in your content collection

### 3. Socratic Question Generator

**Purpose**: Creates thought-provoking questions based on your content

The Socratic Question Engine analyzes your content and generates questions designed to promote deeper thinking and understanding. These questions can help you engage more critically with material and discover new insights.

**How to use**:
1. Click "Socratic Questions" in the navigation menu
2. Paste content into the text area
3. Click "Generate Questions"
4. Review the generated questions and consider your responses

**When to use**:
- When studying or reviewing material
- To prepare for discussions or presentations
- To deepen understanding of complex topics

### 4. Active Recall System

**Purpose**: Implements spaced repetition for effective learning

The Active Recall Engine uses spaced repetition principles to help you remember important information. It identifies content that is due for review based on optimal timing for memory retention.

**How to use**:
1. Click "Active Recall" in the navigation menu
2. Review items that are due for recall
3. Test your memory of the content
4. Mark items as reviewed to update the repetition schedule

**When to use**:
- For studying and memorization
- To maintain knowledge of important concepts
- As part of a daily learning routine

### 5. Pattern Detector

**Purpose**: Identifies themes, connections, and trends in your content

The Pattern Detector analyzes your entire content library to identify common themes, frequently occurring concepts, and connections between different pieces of content.

**How to use**:
1. Click "Pattern Detector" in the navigation menu
2. Review the identified patterns and themes
3. Explore connections between related content

**When to use**:
- To discover unexpected connections between topics
- To identify your main areas of interest
- To find content that could be grouped or organized differently

### 6. Recommendations Engine

**Purpose**: Suggests new content based on your existing library

The Recommendation Engine suggests new content that might interest you based on analysis of your existing collection. It can help you discover new resources and expand your knowledge base.

**How to use**:
1. Click "Recommendations" in the navigation menu (if available)
2. Browse suggested content
3. Save interesting items to your library

**When to use**:
- When looking for new content to explore
- To diversify your content collection
- To discover resources related to your interests

## Mobile Usage

The Atlas web dashboard is fully responsive and works on mobile devices:

### Mobile Navigation
- Use the hamburger menu (☰) to access features on small screens
- Swipe left/right to navigate between sections
- Tap and hold on content to access quick actions

### Mobile-Specific Features
- Voice input for the Socratic Question Generator
- Camera integration for scanning documents directly into Atlas
- Share sheet integration for saving web content from mobile browsers

## Keyboard Shortcuts

Speed up your workflow with these keyboard shortcuts:

| Shortcut | Action |
|----------|--------|
| `Ctrl+1` | Navigate to Proactive Surfacer |
| `Ctrl+2` | Navigate to Temporal Relationships |
| `Ctrl+3` | Navigate to Socratic Questions |
| `Ctrl+4` | Navigate to Active Recall |
| `Ctrl+5` | Navigate to Pattern Detector |
| `Ctrl+R` | Refresh current view |
| `Ctrl+F` | Focus search input |
| `Esc` | Close modals and dialogs |

## Feature Comparison

When to use each cognitive feature:

| Feature | Best For | Frequency of Use |
|---------|----------|------------------|
| Proactive Surfacer | Rediscovering forgotten content | Weekly |
| Temporal Relationships | Understanding content evolution | Monthly |
| Socratic Questions | Deepening understanding | As needed |
| Active Recall | Memorization and retention | Daily |
| Pattern Detector | Discovering connections | Weekly |
| Recommendations | Finding new content | Weekly |

## Getting Started Tutorial

### First Week with Atlas

**Day 1**: Explore the dashboard
- Browse each feature to understand what's available
- Try the Socratic Question Generator with a piece of content you're studying

**Day 3**: Set up your workflow
- Create bookmarks or shortcuts to the dashboard
- Identify which features are most relevant to your use case

**Day 7**: Integrate into routine
- Use Active Recall for daily review
- Check Proactive Surfacer weekly for forgotten content
- Review patterns monthly to understand your interests

## Troubleshooting

### Dashboard not loading
- Ensure Atlas service is running: `python atlas_service_manager.py status`
- Check that port 8000 is not blocked by firewall
- Verify network connectivity if accessing from another device

### Features not working
- Check the Atlas logs for error messages: `tail -f logs/atlas_service.log`
- Ensure all required dependencies are installed
- Restart the Atlas service: `python atlas_service_manager.py restart`

### Slow performance
- Check system resources: `htop`
- Reduce the amount of content being processed simultaneously
- Consider upgrading system hardware if consistently running out of resources

## Advanced Tips

### Customizing the Dashboard
- Modify templates in `/web/templates/` to change the appearance
- Add custom CSS in the `<style>` section of HTML templates
- Create new features by adding routes to `web/app.py`

### Automating Access
- Create a bookmark with a JavaScript snippet to automatically open specific features
- Use browser extensions to add Atlas integration to any webpage
- Set up scheduled access with cron jobs or task schedulers

## Support

For help with the web dashboard:
- Check the Atlas documentation: `/docs/user-guides/`
- Visit GitHub Discussions: https://github.com/your-username/atlas/discussions
- Join the community Discord: https://discord.gg/atlas

For bug reports:
- File an issue on GitHub: https://github.com/your-username/atlas/issues
- Include screenshots and error messages when possible
- Describe steps to reproduce the issue