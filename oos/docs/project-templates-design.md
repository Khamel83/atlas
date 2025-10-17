# Goal-Oriented Project Templates Design

## 🎯 Vision

Create intelligent project templates that guide non-technical users from idea to working AI project through step-by-step natural language interactions. Each template understands the user's goal and provides personalized guidance.

## 📋 Template Philosophy

- **Goal-First**: Start with "What do you want to accomplish?" not "What technology do you want?"
- **Progressive Disclosure**: Reveal complexity only as needed
- **Natural Language**: Users describe what they want in plain English
- **Automatic Everything**: Setup, configuration, and deployment handled automatically
- **Guided Journey**: Each step explains what's happening and why

## 🏗️ Template Architecture

```
Template Structure:
├── metadata.json           # Template info and capabilities
├── goals.yaml              # Supported goals and variations
├── steps/                  # Step-by-step guidance
│   ├── 01-discovery.py     # Understand user needs
│   ├── 02-planning.py      # Create project plan
│   ├── 03-setup.py         # Automatic setup
│   ├── 04-implementation.py # Generate code
│   ├── 05-testing.py       # Validate and test
│   └── 06-deployment.py    # Deploy and share
├── components/             # Reusable code components
├── prompts/               # AI prompts for each step
└── examples/              # Real-world examples
```

## 🤖 Core Template Types

### 1. AI Chatbot Template
**Goal**: Create conversational AI assistants for any purpose

**Supported Variations:**
- Customer Service Bot
- Personal Assistant
- FAQ Bot
- Language Learning Tutor
- Content Creation Helper
- Emotional Support Companion

**Natural Language Understanding:**
```
User: "I want a chatbot that helps customers with product questions"
→ Detected: Customer Service Bot + Product Knowledge
→ Steps: Product catalog integration + FAQ system + Handoff to human
```

### 2. Web Automation Template
**Goal**: Automate repetitive web tasks without coding

**Supported Variations:**
- Social Media Poster
- Price Monitor
- Content Scraper
- Form Filler
- Email Automation
- Report Generator

**Natural Language Understanding:**
```
User: "I need to check prices on Amazon every day and email me when they drop"
→ Detected: Price Monitoring + Email Alerts + Amazon Target
→ Steps: Price extraction + Database storage + Email alerts + Scheduling
```

### 3. Data Analysis Template
**Goal**: Turn data into insights and reports automatically

**Supported Variations:**
- Sales Analyzer
- Social Media Insights
- Survey Results Processor
- Financial Reporter
- Website Analytics
- Data Visualization

**Natural Language Understanding:**
```
User: "I have CSV files of sales data and want weekly reports with charts"
→ Detected: CSV Processing + Weekly Reports + Data Visualization
→ Steps: Data import + Analysis pipeline + Chart generation + Email reports
```

### 4. Personal Assistant Template
**Goal**: Create AI helpers for personal productivity

**Supported Variations:**
- Calendar Manager
- Email Organizer
- Task Automator
- Note Taker
- Habit Tracker
- Decision Helper

**Natural Language Understanding:**
```
User: "Help me manage my calendar and suggest meeting times based on my preferences"
→ Detected: Calendar Management + Scheduling + Preference Learning
→ Steps: Calendar sync + Preference analysis + Meeting optimization
```

## 🔧 Implementation Details

### Template Engine
```python
class TemplateEngine:
    """Main template processing engine"""

    def __init__(self, config, google_integration):
        self.config = config
        self.google_integration = google_integration
        self.templates = self._load_templates()

    async def understand_goal(self, user_description: str) -> GoalAnalysis:
        """Understand what user wants to accomplish"""
        # Use AI to analyze natural language description
        # Extract: goal type, features, complexity, requirements

        return GoalAnalysis(
            goal_type="chatbot",
            confidence=0.85,
            features=["customer_service", "product_knowledge"],
            complexity="medium",
            estimated_time="2 hours",
            user_needs=["answer product questions", "handle common issues"]
        )

    async def select_template(self, goal_analysis: GoalAnalysis) -> ProjectTemplate:
        """Select the best template for user's goal"""
        # Match goal to best template
        template = self.templates[goal_analysis.goal_type]

        # Customize template based on user's specific needs
        return template.customize(goal_analysis)

    async def guide_project_creation(self, template: ProjectTemplate):
        """Guide user through step-by-step project creation"""
        for step in template.steps:
            await self._execute_step(step)

            # Check for Google Sheets integration
            if self.google_integration.is_configured():
                await self._sync_progress_to_sheets(step)
```

### Step-by-Step Guidance System
```python
class ProjectStep:
    """Individual step in project creation"""

    def __init__(self, name: str, description: str, actions: List[Action]):
        self.name = name
        self.description = description
        self.actions = actions
        self.status = "pending"

    async def execute(self, context: ProjectContext):
        """Execute this step with user context"""
        print(f"{Colors.CYAN}Step: {self.name}{Colors.END}")
        print(f"{Colors.WHITE}{self.description}{Colors.END}")

        for action in self.actions:
            await action.execute(context)

        self.status = "completed"
        self._update_progress_in_sheets(context)

class DiscoveryStep(ProjectStep):
    """Step 1: Understand user's needs"""

    def __init__(self):
        super().__init__(
            name="Discover Your Project",
            description="Let's understand what you want to build and why",
            actions=[
                AskAboutGoal(),
                AskAboutFeatures(),
                AskAboutUsers(),
                ConfirmUnderstanding()
            ]
        )

class ImplementationStep(ProjectStep):
    """Step 4: Generate working code"""

    def __init__(self):
        super().__init__(
            name="Build Your Project",
            description="Creating your AI project based on your requirements",
            actions=[
                GenerateCode(),
                SetupDependencies(),
                CreateConfiguration(),
                TestComponents()
            ]
        )
```

### Natural Language Processing
```python
class GoalAnalyzer:
    """Analyze user's natural language description"""

    async def analyze(self, description: str) -> GoalAnalysis:
        """Extract goal, features, and requirements from text"""

        # Use OpenRouter to analyze the description
        prompt = f"""
        Analyze this project description and extract:
        1. Main goal type (chatbot, automation, data_analysis, personal_assistant)
        2. Key features needed
        3. Target users
        4. Data sources needed
        5. Integration requirements
        6. Estimated complexity

        Description: "{description}"

        Return JSON with analysis.
        """

        analysis = await self._call_ai(prompt)

        return GoalAnalysis(
            goal_type=analysis['goal_type'],
            features=analysis['features'],
            target_users=analysis['target_users'],
            complexity=analysis['complexity'],
            confidence=analysis['confidence'],
            user_needs=analysis['user_needs']
        )
```

## 📱 User Experience Flow

### Initial Interaction
```bash
$ oos create

🚀 OOS Project Creator
What would you like to build? (describe in plain English)

> I want a chatbot that helps customers with product questions and can hand off to human agents when needed

🤔 Understanding your goal...
✅ Detected: Customer Service Chatbot with Human Handoff
📋 Features: Product knowledge base, FAQ system, human escalation, conversation history

⏱️  Estimated time: 2-3 hours
🔧 Technical requirements: None (we handle everything)

Continue with this plan? (Y/n): y
```

### Step-by-Step Guidance
```bash
Step 1 of 6: Discover Your Project
=====================================
Let's understand your customers and products better...

📝 What types of products will this chatbot help with?
> Electronics and software products

📝 Do you have existing product documentation or FAQ?
> Yes, we have a knowledge base in Notion

📝 How should the chatbot handle questions it can't answer?
> Escalate to human support team via email

✅ Great! I'll create a chatbot that:
- Understands electronics and software products
- Uses your Notion knowledge base
- Escalates complex questions to your team
Press Enter to continue...
```

### Automatic Progress
```bash
Step 4 of 6: Build Your Project
=====================================
Creating your customer service chatbot...

🔧 Setting up knowledge base integration... ✅
🤖 Training AI on your products... ✅
💬 Creating conversation flows... ✅
📧 Setting up human escalation... ✅
🧪 Testing components... ✅

✅ Your chatbot is ready!

Next: Test it out and customize as needed
```

## 🌐 Google Sheets Integration

Each template creates a structured spreadsheet:

**Chatbot Template Sheet:**
- **Config**: Project settings, AI model, knowledge sources
- **Conversations**: Chat logs and improvements
- **Knowledge**: Product information and FAQs
- **Analytics**: User interactions and success rates
- **Improvements**: Suggested enhancements based on usage

**Automation Template Sheet:**
- **Config**: Target websites, schedules, triggers
- **Tasks**: Automation history and results
- **Data**: Extracted information and trends
- **Alerts**: Notifications and conditions
- **Optimization**: Performance improvements

## 🎯 Template Examples

### Customer Service Chatbot
**What it creates:**
- AI-powered conversation handler
- Knowledge base integration (Notion, website, docs)
- Human escalation system
- Conversation analytics
- Performance dashboard

**User interaction:**
```python
# Generated code
class CustomerServiceBot:
    def __init__(self, knowledge_base, escalation_email):
        self.knowledge = load_knowledge_base(knowledge_base)
        self.escalation = EscalationSystem(escalation_email)

    async def handle_message(self, user_message):
        # Find answer in knowledge base
        answer = await self.search_knowledge(user_message)

        if answer.confidence < 0.7:
            # Escalate to human
            return await self.escalate_to_human(user_message)

        return answer.response
```

### Price Monitoring Automation
**What it creates:**
- Web scraper for target sites
- Price tracking database
- Email/SMS alert system
- Historical price charts
- Trend analysis

**User interaction:**
```python
# Generated code
class PriceMonitor:
    def __init__(self, products, alert_threshold=0.1):
        self.products = products
        self.threshold = alert_threshold

    async def check_prices(self):
        for product in self.products:
            current_price = await self.scrape_price(product.url)

            if current_price < product.last_price * (1 - self.threshold):
                await self.send_price_alert(product, current_price)

            product.last_price = current_price
```

## 📊 Template Benefits

1. **Zero Technical Knowledge**: Users describe what they want, not how to build it
2. **Guided Discovery**: System helps users understand their own requirements
3. **Automatic Implementation**: All code, setup, and configuration handled automatically
4. **Progressive Learning**: Users learn as they go, but aren't overwhelmed
5. **Real Results**: Working projects, not just tutorials
6. **Universal Access**: Projects available on all devices via Google Sheets
7. **Continuous Improvement**: Templates learn from user feedback and usage

## 🚀 Implementation Plan

### Phase 1: Core Template System
- [ ] Template engine and goal analyzer
- [ ] Basic chatbot and automation templates
- [ ] Step-by-step guidance framework
- [ ] Integration with existing CLI

### Phase 2: Enhanced Templates
- [ ] Data analysis and personal assistant templates
- [ ] Natural language processing improvements
- [ ] Google Sheets integration for project data
- [ ] Component library for reusable code

### Phase 3: Intelligence
- [ ] AI-powered template customization
- [ ] Usage-based template improvements
- [ ] Advanced error handling and recovery
- [ ] Performance optimization

### Phase 4: Ecosystem
- [ ] Template sharing and discovery
- [ ] Community template gallery
- [ ] Template versioning and updates
- [ ] Integration with third-party services

This template system transforms OOS from a simple project creator into an intelligent project development partner that guides users from idea to working AI application through natural conversation.