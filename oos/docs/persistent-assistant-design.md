# Persistent OOS Assistant Design

## 🎯 Vision

Transform OOS from a command-line tool into an always-present AI development partner that listens for "hey OOS" and continuously processes ideas in the background, maximizing the value of user's most limited resource: their time and attention.

## 🔄 Core User Experience

### **Before OOS:**
- 💭 User has idea while coding
- 🤔 "I should use OOS for this"
- ⏰ Switch contexts, run commands, provide input
- 📝 Manually track progress
- 😟担心 ideas get lost

### **After Persistent OOS:**
- 💭 User has idea while coding
- 🎤 Just say "hey OOS, build me a chatbot for customer support"
- 🌱 OOS activates and processes in background
- 📱 Continue coding, OOS handles everything
- ✅ Return later to completed/progressed work

## 🏗️ Architecture

```
Persistent OOS Architecture:
├── oos_daemon.py           # Background service that's always running
├── wake_word_detector.py   # Listens for "hey OOS" activation
├── idea_processor.py       # Processes and germinates ideas
├── project_manager.py      # Manages active projects and persistence
├── background_worker.py    # Handles long-running tasks
├── progress_tracker.py     # Tracks idea germination and progress
└── notification_system.py   # Alerts user when ideas need attention
```

## 🎤 Activation Methods

### 1. **Wake Word Detection**
```bash
# User is coding, has idea
User: "hey OOS, I need a price monitoring bot for Amazon"
OOS: "🎧 Got it! I'll start working on that Amazon price monitor. Anything specific?"
User: "Yeah, email me when prices drop more than 10%"
OOS: "✅ Got it. I'll work on this and ping you when I need more input."
```

### 2. **Message Prefix**
```bash
# In any chat, terminal, or IDE
User: "hey OOS can you analyze the sales data from last quarter?"
OOS: "🔍 Starting sales analysis for Q3 data..."
```

### 3. **Direct Command**
```bash
# Traditional method still works
oos "create automation to monitor website prices"
```

## 🌱 Idea Germination Process

### **Phase 1: Idea Capture (0-2 minutes)**
```
Input: Voice/text idea → OOS captures and analyzes
Output: Idea understanding, requirements extraction, confidence assessment
```

### **Phase 2: Background Processing (2-60 minutes)**
```
OOS works independently:
- Research best approaches
- Create project structure
- Generate initial code
- Setup integrations
- Test basic functionality
```

### **Phase 3: Intelligent Stalling (When Stuck)**
```
If OOS hits a blocker:
- Document what was accomplished
- Identify specific missing information
- Ask targeted questions
- Wait for user input
- Preserve all progress
```

### **Phase 4: Progress Notification**
```
OOS: "🌱 Your Amazon price monitor is growing!
✅ Created basic scraper
❓ Need: Your Amazon credentials to proceed
📊 Progress: 60% complete"
```

## 🔧 Implementation Components

### **OOS Daemon (Always Running)**
```python
class OOSDaemon:
    """Background service that manages all OOS interactions"""

    def __init__(self):
        self.active = False
        self.current_projects = {}
        self.idea_queue = []
        self.wake_word_active = True

    async def start(self):
        """Start the persistent OOS daemon"""
        self.wake_word_detector = WakeWordDetector()
        self.idea_processor = IdeaProcessor()
        self.background_worker = BackgroundWorker()

        # Start listening for wake word
        await self.wake_word_detector.start(self.on_wake_word_detected)

        # Process ideas in background
        await self.background_worker.start(self.process_idea_queue)

    async def on_wake_word_detected(self, audio_text: str):
        """Handle wake word activation"""
        if not self.active:
            await self.activate_session(audio_text)
        else:
            await self.process_user_input(audio_text)
```

### **Wake Word Detector**
```python
class WakeWordDetector:
    """Listens for 'hey OOS' activation"""

    def __init__(self):
        self.listening = True
        self.wake_phrases = [
            "hey oos",
            "hey oos",
            "oos can you",
            "oos i need",
            "oos create"
        ]

    async def start(self, callback):
        """Start listening for wake words"""
        # This would integrate with system audio input
        # For demo, we'll simulate with file monitoring
        await self.monitor_input_sources(callback)

    async def monitor_input_sources(self, callback):
        """Monitor various input sources for OOS activation"""
        sources = [
            self.monitor_microphone(),
            self.monitor_terminal(),
            self.monitor_ide_plugins(),
            self.monitor_chat_apps()
        ]

        await asyncio.gather(*sources)
```

### **Idea Processor**
```python
class IdeaProcessor:
    """Processes user ideas and germinates them into projects"""

    def __init__(self):
        self.template_engine = get_template_engine()
        self.google_sheets = get_sheets_integration()

    async def process_idea(self, idea: Idea) -> GerminationResult:
        """Process a single idea through germination phases"""

        # Phase 1: Understanding
        understanding = await self.understand_idea(idea)

        # Phase 2: Research
        research = await self.research_approaches(understanding)

        # Phase 3: Creation
        creation = await self.create_solution(understanding, research)

        # Phase 4: Refinement
        refinement = await self.refine_solution(creation)

        return GerminationResult(
            idea=idea,
            understanding=understanding,
            research=research,
            creation=creation,
            refinement=refinement,
            status=self.determine_next_status(refinement)
        )

    async def understand_idea(self, idea: Idea) -> IdeaUnderstanding:
        """Extract goals, requirements, and constraints from user input"""

        # Use existing template engine for goal analysis
        goal_analysis = await self.template_engine.goal_analyzer.analyze_goal(idea.content)

        # Extract additional context
        context = await self.extract_context(idea)

        return IdeaUnderstanding(
            goal=goal_analysis,
            context=context,
            confidence=goal_analysis.confidence,
            missing_info=self.identify_missing_info(goal_analysis, context)
        )
```

### **Background Worker**
```python
class BackgroundWorker:
    """Handles long-running tasks in the background"""

    async def start(self, idea_queue):
        """Process ideas from queue continuously"""
        while True:
            if idea_queue:
                idea = idea_queue.pop(0)
                await self.process_idea_background(idea)
            else:
                await asyncio.sleep(1)  # Check queue every second

    async def process_idea_background(self, idea: Idea):
        """Process single idea in background"""
        try:
            # Update status: Processing
            await self.update_idea_status(idea.id, "processing")

            # Process the idea
            result = await self.idea_processor.process_idea(idea)

            # Save result
            await self.save_germination_result(idea.id, result)

            # Notify user if needed
            if result.status == "needs_input":
                await self.notify_user_needs_input(idea, result)
            elif result.status == "completed":
                await self.notify_user_completed(idea, result)

        except Exception as e:
            await self.handle_processing_error(idea, e)
```

### **Project Persistence**
```python
class ProjectPersistence:
    """Manages project state across sessions"""

    def __init__(self, google_sheets):
        self.google_sheets = google_sheets
        self.local_cache = {}

    async def save_idea(self, idea: Idea):
        """Save idea to persistent storage"""
        # Save to Google Sheets for universal access
        if self.google_sheets.is_configured():
            await self.save_to_sheets(idea)

        # Save locally for offline access
        await self.save_locally(idea)

    async def get_idea_history(self, project_id: str = None):
        """Get all ideas for a project or globally"""
        ideas = []

        # Get from Google Sheets
        if self.google_sheets.is_configured():
            ideas.extend(await self.get_from_sheets(project_id))

        # Get from local cache
        ideas.extend(self.get_from_local_cache(project_id))

        return ideas
```

## 📱 User Interaction Flows

### **Flow 1: Voice Activation While Coding**
```bash
# User is working in IDE
User: "hey OOS, I need a way to automate my social media posts"

# OOS activates immediately
OOS: "🎧 Got it! Social media automation. Let me ask a few questions:"
OOS: "📝 Which platforms? (Twitter, LinkedIn, Instagram, etc.)"
User: "Twitter and LinkedIn"
OOS: "📝 How often? Daily, weekly, when you publish content?"
User: "Daily at 9 AM"
OOS: "✅ Perfect! I'll start building your social media automation. Ping you soon!"

# 30 minutes later...
OOS: "🌱 Your social media automation is growing! ✅ Created Twitter and LinkedIn posters 📝 Ready for your content templates 🚀 Need: API keys for both platforms. Want to add them now?"
```

### **Flow 2: Text Message in Chat**
```bash
# In Slack/Teams/Discord
User: "hey OOS can you analyze our customer support tickets from last month?"

# OOS responds in chat
OOS: "🔍 Starting customer support analysis for last month...
📊 I'll need access to your support ticket data.
📁 Where should I look? (Zendesk, Freshdesk, CSV export, etc.)"
```

### **Flow 3: Terminal Command**
```bash
# User remembers they have OOS while working
$ oos "create a dashboard to track website performance"

OOS: "🚀 Website performance dashboard starting...
📋 I'll create monitoring for: page load times, error rates, uptime
🌐 Need: Your website URL and any analytics API keys
⏱️  Estimated time: 2 hours"
```

## 🌐 Integration Points

### **IDE Integration**
```javascript
// VS Code extension
vscode.commands.registerCommand('oos.activate', () => {
    const input = vscode.window.showInputBox({
        prompt: 'What do you want OOS to help you with?'
    });

    input.then(value => {
        if (value) {
            // Send to OOS daemon
            oosDaemon.processInput(value);
        }
    });
});
```

### **Chat App Integration**
```python
# Slack bot integration
@app.message(re.compile(r'^(hey oos|oos\s+)', re.IGNORECASE))
async def handle_oos_activation(message, say):
    user_input = message['text'].replace(/^hey oos/i, '').strip()

    # Send to OOS daemon
    result = await oos_daemon.process_user_input(
        user_id=message['user'],
        input=user_input,
        source='slack'
    )

    await say(result['response'])
```

### **Voice Assistant Integration**
```python
# Voice activation through system audio
def on_speech_detected(text):
    if text.lower().startswith('hey oos'):
        idea = text[7:].strip()  # Remove "hey oos"

        # Send to OOS daemon
        asyncio.create_task(oos_daemon.process_user_input(
            user_id='voice',
            input=idea,
            source='voice'
        ))
```

## 💾 Data Persistence

### **Google Sheets Structure**
```
OOS Workspace (Google Drive)
├── active_ideas/           # Currently processing ideas
│   ├── idea_123/           # Individual idea workspace
│   │   ├── transcripts/    # Voice/text transcripts
│   │   ├── research/       # Research findings
│   │   ├── code/           # Generated code
│   │   └── progress/       # Progress tracking
│   └── idea_456/
├── completed_projects/      # Finished projects
└── knowledge_base/        # Learning from all projects
```

### **Local Cache Structure**
```
~/.oos/
├── daemon.pid              # Daemon process ID
├── active_projects.json    # Current project states
├── idea_queue.json         # Pending ideas
├── progress_cache/         # Cached progress data
└── logs/                  # Activity logs
```

## 🎯 Benefits

1. **Zero Context Switching**: Ideas captured immediately without breaking flow
2. **Continuous Processing**: OOS works while user focuses on other tasks
3. **Progressive Refinement**: Ideas improve over time with user input
4. **Universal Access**: Works from voice, text, IDE, chat apps
5. **Persistent Memory**: Never loses context or progress
6. **Intelligent Assistance**: Knows when to ask questions vs. work independently
7. **Maximized User Time**: Every minute of user input generates maximum value

## 🚀 Implementation Plan

### Phase 1: Core Daemon
- [ ] OOS daemon with background processing
- [ ] Basic wake word detection
- [ ] Idea queue management
- [ ] Local persistence

### Phase 2: Enhanced Processing
- [ ] Advanced idea germination
- [ ] Multi-source input integration
- [ ] Google Sheets persistence
- [ ] Progress notifications

### Phase 3: Ecosystem Integration
- [ ] IDE plugins (VS Code, IntelliJ)
- [ ] Chat app integrations (Slack, Discord)
- [ ] Voice assistant integration
- [ ] Mobile app access

### Phase 4: Intelligence
- [ ] Learning from user patterns
- [ ] Predictive assistance
- [ ] Advanced error recovery
- [ ] Collaborative features

This transforms OOS from a tool you remember to use into an AI partner that's always working for you in the background, turning your fleeting ideas into growing projects.