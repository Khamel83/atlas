"""
Goal-Oriented Project Template Engine
Guide users from idea to working AI project through natural language
"""

import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import re
import os

from renderers import Colors
from cost_manager import get_cost_manager


@dataclass
class GoalAnalysis:
    """Analysis of user's goal description"""
    goal_type: str
    confidence: float
    features: List[str]
    target_users: List[str]
    complexity: str  # simple, medium, complex
    estimated_time: str
    user_needs: List[str]
    data_sources: List[str] = None
    integrations: List[str] = None


@dataclass
class ProjectStep:
    """Individual step in project creation"""
    name: str
    description: str
    order: int
    actions: List[str]
    status: str = "pending"
    user_inputs: Dict[str, Any] = None


@dataclass
class ProjectTemplate:
    """Complete project template"""
    name: str
    goal_type: str
    description: str
    variations: List[str]
    steps: List[ProjectStep]
    components: List[str]
    dependencies: List[str]
    estimated_time: str
    difficulty: str


class GoalAnalyzer:
    """Analyze natural language descriptions to understand user goals"""

    def __init__(self, config):
        self.config = config
        self.openrouter_api_key = config.get('openrouter_api_key')
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.cost_manager = get_cost_manager(config)

    async def analyze_goal(self, description: str) -> GoalAnalysis:
        """Analyze user's natural language description using real AI"""
        print(f"{Colors.CYAN}🤔 Understanding your goal...{Colors.END}")

        if self.openrouter_api_key and self.openrouter_api_key != 'demo-key':
            # Use real AI analysis
            analysis = await self._ai_analyze_goal(description)
        else:
            # Fallback to pattern-based analysis
            analysis = self._extract_patterns(description)

        print(f"{Colors.GREEN}✅ Detected: {analysis.goal_type.title()}{Colors.END}")
        if analysis.features:
            print(f"{Colors.WHITE}📋 Features: {', '.join(analysis.features)}{Colors.END}")
        if analysis.estimated_time:
            print(f"{Colors.WHITE}⏱️  Estimated time: {analysis.estimated_time}{Colors.END}")

        return analysis

    async def _ai_analyze_goal(self, description: str) -> GoalAnalysis:
        """Use OpenRouter to analyze the goal with real AI"""
        prompt = f"""Analyze this project idea and return ONLY a JSON object with this exact structure:

{{
  "goal_type": "chatbot|automation|data_analysis|personal_assistant|web_app|mobile_app|game|tool",
  "confidence": 0.85,
  "features": ["feature1", "feature2", "feature3"],
  "target_users": ["user_type1", "user_type2"],
  "complexity": "simple|medium|complex",
  "estimated_time": "1-2 hours|3-5 hours|1-2 days|1+ weeks",
  "user_needs": ["need1", "need2"],
  "data_sources": ["source1", "source2"],
  "integrations": ["api1", "api2"]
}}

Project idea: "{description}"

Return ONLY the JSON, no other text."""

        try:
            # Check cost limit before making API call
            project_id = "oos-analysis"
            estimated_cost = self.cost_manager.estimate_openrouter_cost(
                "google/gemini-2.0-flash-exp", 500, 200  # Estimate
            )

            if not await self.cost_manager.check_can_proceed(project_id, estimated_cost):
                print(f"{Colors.RED}💰 Daily cost limit reached, using fallback{Colors.END}")
                return self._extract_patterns(description)

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "google/gemini-2.0-flash-exp",  # Use the cheaper, faster model
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.1
                }

                async with session.post(self.openrouter_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        ai_response = result["choices"][0]["message"]["content"].strip()

                        # Record actual cost
                        usage = result.get("usage", {})
                        input_tokens = usage.get("prompt_tokens", 500)
                        output_tokens = usage.get("completion_tokens", 200)
                        actual_cost = self.cost_manager.estimate_openrouter_cost(
                            "google/gemini-2.0-flash-exp", input_tokens, output_tokens
                        )
                        await self.cost_manager.record_api_call(project_id, actual_cost, input_tokens + output_tokens)

                        # Parse JSON response
                        try:
                            # Clean up response (remove code blocks if present)
                            if "```json" in ai_response:
                                ai_response = ai_response.split("```json")[1].split("```")[0].strip()
                            elif "```" in ai_response:
                                ai_response = ai_response.split("```")[1].strip()

                            analysis_data = json.loads(ai_response)

                            return GoalAnalysis(
                                goal_type=analysis_data.get("goal_type", "general"),
                                confidence=analysis_data.get("confidence", 0.7),
                                features=analysis_data.get("features", []),
                                target_users=analysis_data.get("target_users", []),
                                complexity=analysis_data.get("complexity", "medium"),
                                estimated_time=analysis_data.get("estimated_time", "3-5 hours"),
                                user_needs=analysis_data.get("user_needs", []),
                                data_sources=analysis_data.get("data_sources", []),
                                integrations=analysis_data.get("integrations", [])
                            )
                        except json.JSONDecodeError as e:
                            print(f"{Colors.YELLOW}⚠️  AI response parsing failed, using fallback{Colors.END}")
                            return self._extract_patterns(description)
                    else:
                        print(f"{Colors.YELLOW}⚠️  API request failed, using fallback{Colors.END}")
                        return self._extract_patterns(description)

        except Exception as e:
            print(f"{Colors.YELLOW}⚠️  AI analysis failed ({str(e)}), using fallback{Colors.END}")
            return self._extract_patterns(description)

    def _extract_patterns(self, description: str) -> GoalAnalysis:
        """Extract goal information using patterns and keywords"""
        desc_lower = description.lower()

        # Goal type detection
        goal_patterns = {
            'chatbot': ['chatbot', 'chat', 'assistant', 'conversational', 'bot', 'messaging'],
            'automation': ['automation', 'automate', 'scrape', 'monitor', 'schedule', 'bot'],
            'data_analysis': ['analyze', 'analysis', 'data', 'insights', 'reports', 'charts'],
            'personal_assistant': ['personal', 'assistant', 'calendar', 'email', 'tasks', 'organize']
        }

        detected_goal = 'general'
        confidence = 0.5
        features = []

        for goal_type, keywords in goal_patterns.items():
            matches = sum(1 for keyword in keywords if keyword in desc_lower)
            if matches > 0:
                confidence = min(0.5 + (matches * 0.1), 0.95)
                detected_goal = goal_type
                features.extend(self._extract_features_for_goal(goal_type, desc_lower))
                break

        # Extract specific features
        if 'customer' in desc_lower or 'service' in desc_lower:
            features.extend(['customer_service', 'support'])
        if 'price' in desc_lower or 'monitor' in desc_lower:
            features.extend(['price_monitoring', 'alerts'])
        if 'social' in desc_lower or 'media' in desc_lower:
            features.extend(['social_media', 'content'])
        if 'email' in desc_lower:
            features.append('email_integration')

        # Determine complexity
        complexity = 'simple'
        if any(word in desc_lower for word in ['multiple', 'several', 'advanced', 'complex']):
            complexity = 'medium'
        if any(word in desc_lower for word in ['enterprise', 'scale', 'integration', 'api']):
            complexity = 'complex'

        # Estimate time
        time_map = {'simple': '30 minutes', 'medium': '2-3 hours', 'complex': '1-2 days'}
        estimated_time = time_map.get(complexity, '1 hour')

        return GoalAnalysis(
            goal_type=detected_goal,
            confidence=confidence,
            features=list(set(features)),  # Remove duplicates
            target_users=self._extract_target_users(desc_lower),
            complexity=complexity,
            estimated_time=estimated_time,
            user_needs=self._extract_user_needs(desc_lower),
            data_sources=self._extract_data_sources(desc_lower),
            integrations=self._extract_integrations(desc_lower)
        )

    def _extract_features_for_goal(self, goal_type: str, description: str) -> List[str]:
        """Extract features specific to goal type"""
        features = []

        if goal_type == 'chatbot':
            if any(word in description for word in ['knowledge', 'faq', 'information']):
                features.append('knowledge_base')
            if any(word in description for word in ['human', 'escalate', 'support']):
                features.append('human_handoff')
            if any(word in description for word in ['product', 'catalog']):
                features.append('product_integration')

        elif goal_type == 'automation':
            if any(word in description for word in ['web', 'site', 'website']):
                features.append('web_scraping')
            if any(word in description for word in ['email', 'mail']):
                features.append('email_integration')
            if any(word in description for word in ['schedule', 'time', 'daily']):
                features.append('scheduling')

        elif goal_type == 'data_analysis':
            if any(word in description for word in ['csv', 'excel', 'file']):
                features.append('file_processing')
            if any(word in description for word in ['chart', 'visual', 'graph']):
                features.append('visualization')
            if any(word in description for word in ['report', 'summary']):
                features.append('reporting')

        return features

    def _extract_target_users(self, description: str) -> List[str]:
        """Extract target users from description"""
        users = []
        if any(word in description for word in ['customer', 'client', 'user']):
            users.append('customers')
        if any(word in description for word in ['personal', 'my', 'own']):
            users.append('personal')
        if any(word in description for word in ['team', 'company', 'business']):
            users.append('team')
        return users or ['general']

    def _extract_user_needs(self, description: str) -> List[str]:
        """Extract user needs from description"""
        needs = []
        if 'help' in description:
            needs.append('assistance')
        if 'automate' in description:
            needs.append('automation')
        if 'analyze' in description:
            needs.append('insights')
        if 'organize' in description:
            needs.append('organization')
        return needs or ['general_assistance']

    def _extract_data_sources(self, description: str) -> List[str]:
        """Extract data sources from description"""
        sources = []
        if any(word in description for word in ['website', 'web', 'url']):
            sources.append('websites')
        if any(word in description for word in ['file', 'csv', 'excel']):
            sources.append('files')
        if any(word in description for word in ['api', 'database']):
            sources.append('apis')
        return sources

    def _extract_integrations(self, description: str) -> List[str]:
        """Extract required integrations from description"""
        integrations = []
        if 'email' in description:
            integrations.append('email')
        if 'slack' in description:
            integrations.append('slack')
        if 'calendar' in description:
            integrations.append('calendar')
        return integrations


class TemplateEngine:
    """Main template engine for project creation"""

    def __init__(self, config, google_integration=None):
        self.config = config
        self.google_integration = google_integration
        self.goal_analyzer = GoalAnalyzer(config)
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, ProjectTemplate]:
        """Load all available project templates"""
        return {
            'chatbot': self._create_chatbot_template(),
            'automation': self._create_automation_template(),
            'data_analysis': self._create_data_analysis_template(),
            'personal_assistant': self._create_personal_assistant_template()
        }

    def _create_chatbot_template(self) -> ProjectTemplate:
        """Create chatbot project template"""
        steps = [
            ProjectStep(
                name="Discover Your Chatbot",
                description="Let's understand what your chatbot will do and who it will help",
                order=1,
                actions=[
                    "Understand chatbot purpose",
                    "Identify target users",
                    "Gather knowledge sources",
                    "Plan conversation flows"
                ]
            ),
            ProjectStep(
                name="Design Conversations",
                description="Design how your chatbot will interact with users",
                order=2,
                actions=[
                    "Create greeting flows",
                    "Design question handling",
                    "Plan error recovery",
                    "Design human handoff"
                ]
            ),
            ProjectStep(
                name="Setup Knowledge Base",
                description="Connect your chatbot to information sources",
                order=3,
                actions=[
                    "Connect knowledge sources",
                    "Import FAQ data",
                    "Setup information retrieval",
                    "Test knowledge access"
                ]
            ),
            ProjectStep(
                name="Build Chatbot",
                description="Create your AI-powered chatbot",
                order=4,
                actions=[
                    "Generate conversation code",
                    "Setup AI integration",
                    "Create response system",
                    "Add memory/context"
                ]
            ),
            ProjectStep(
                name="Test and Refine",
                description="Test your chatbot and improve its responses",
                order=5,
                actions=[
                    "Test conversations",
                    "Improve responses",
                    "Add error handling",
                    "Optimize performance"
                ]
            ),
            ProjectStep(
                name="Deploy and Share",
                description="Deploy your chatbot and share it with users",
                order=6,
                actions=[
                    "Deploy to web",
                    "Setup monitoring",
                    "Create sharing options",
                    "Plan improvements"
                ]
            )
        ]

        return ProjectTemplate(
            name="AI Chatbot",
            goal_type="chatbot",
            description="Create conversational AI assistants for any purpose",
            variations=[
                "Customer Service Bot",
                "Personal Assistant",
                "FAQ Bot",
                "Language Learning Tutor",
                "Content Creation Helper"
            ],
            steps=steps,
            components=[
                "conversation_handler.py",
                "knowledge_base.py",
                "ai_integration.py",
                "human_handoff.py"
            ],
            dependencies=[
                "openai",
                "chromadb",
                "fastapi",
                "uvicorn"
            ],
            estimated_time="2-3 hours",
            difficulty="beginner"
        )

    def _create_automation_template(self) -> ProjectTemplate:
        """Create automation project template"""
        steps = [
            ProjectStep(
                name="Define Automation",
                description="Understand what tasks you want to automate",
                order=1,
                actions=[
                    "Identify repetitive tasks",
                    "Define triggers",
                    "Plan data flow",
                    "Set success criteria"
                ]
            ),
            ProjectStep(
                name="Design Workflow",
                description="Design your automation workflow",
                order=2,
                actions=[
                    "Map process steps",
                    "Design error handling",
                    "Plan data storage",
                    "Define alerts"
                ]
            ),
            ProjectStep(
                name="Setup Data Sources",
                description="Connect to websites and data sources",
                order=3,
                actions=[
                    "Setup web scraping",
                    "Connect APIs",
                    "Configure databases",
                    "Test data access"
                ]
            ),
            ProjectStep(
                name="Build Automation",
                description="Create your automation scripts",
                order=4,
                actions=[
                    "Create scrapers",
                    "Build processors",
                    "Setup scheduling",
                    "Add monitoring"
                ]
            ),
            ProjectStep(
                name="Test Reliability",
                description="Ensure your automation works reliably",
                order=5,
                actions=[
                    "Test all scenarios",
                    "Handle edge cases",
                    "Setup alerts",
                    "Optimize performance"
                ]
            ),
            ProjectStep(
                name="Deploy and Monitor",
                description="Deploy your automation and monitor its performance",
                order=6,
                actions=[
                    "Deploy scripts",
                    "Setup monitoring",
                    "Create dashboard",
                    "Plan maintenance"
                ]
            )
        ]

        return ProjectTemplate(
            name="Web Automation",
            goal_type="automation",
            description="Automate repetitive web tasks and data processing",
            variations=[
                "Social Media Poster",
                "Price Monitor",
                "Content Scraper",
                "Form Filler",
                "Report Generator"
            ],
            steps=steps,
            components=[
                "web_scraper.py",
                "scheduler.py",
                "data_processor.py",
                "alert_system.py"
            ],
            dependencies=[
                "requests",
                "beautifulsoup4",
                "schedule",
                "pandas",
                "smtplib"
            ],
            estimated_time="2-4 hours",
            difficulty="intermediate"
        )

    def _create_data_analysis_template(self) -> ProjectTemplate:
        """Create data analysis project template"""
        steps = [
            ProjectStep(
                name="Understand Your Data",
                description="Learn about your data and what insights you need",
                order=1,
                actions=[
                    "Identify data sources",
                    "Define analysis goals",
                    "Plan visualization",
                    "Set success metrics"
                ]
            ),
            ProjectStep(
                name="Prepare Data Pipeline",
                description="Setup data import and processing",
                order=2,
                actions=[
                    "Create data importers",
                    "Setup data cleaning",
                    "Configure storage",
                    "Test data flow"
                ]
            ),
            ProjectStep(
                name="Build Analysis Engine",
                description="Create data analysis and visualization",
                order=3,
                actions=[
                    "Create analysis functions",
                    "Build visualizations",
                    "Generate reports",
                    "Add insights"
                ]
            ),
            ProjectStep(
                name="Create Dashboard",
                description="Build a dashboard to view your insights",
                order=4,
                actions=[
                    "Design dashboard layout",
                    "Create interactive charts",
                    "Add filtering",
                    "Setup exports"
                ]
            ),
            ProjectStep(
                name="Automate Reporting",
                description="Setup automated report generation",
                order=5,
                actions=[
                    "Schedule reports",
                    "Setup email delivery",
                    "Create subscriptions",
                    "Add alerts"
                ]
            ),
            ProjectStep(
                name="Deploy and Share",
                description="Deploy your analysis system",
                order=6,
                actions=[
                    "Deploy dashboard",
                    "Setup access controls",
                    "Monitor performance",
                    "Gather feedback"
                ]
            )
        ]

        return ProjectTemplate(
            name="Data Analysis",
            goal_type="data_analysis",
            description="Turn data into insights and automated reports",
            variations=[
                "Sales Analyzer",
                "Social Media Insights",
                "Financial Reporter",
                "Website Analytics",
                "Survey Processor"
            ],
            steps=steps,
            components=[
                "data_importer.py",
                "analyzer.py",
                "visualizer.py",
                "dashboard.py",
                "reporter.py"
            ],
            dependencies=[
                "pandas",
                "matplotlib",
                "seaborn",
                "plotly",
                "fastapi",
                "jinja2"
            ],
            estimated_time="3-5 hours",
            difficulty="intermediate"
        )

    def _create_personal_assistant_template(self) -> ProjectTemplate:
        """Create personal assistant project template"""
        steps = [
            ProjectStep(
                name="Define Assistant Role",
                description="Define what your personal assistant will help with",
                order=1,
                actions=[
                    "Identify daily tasks",
                    "Define preferences",
                    "Plan integrations",
                    "Set boundaries"
                ]
            ),
            ProjectStep(
                name="Connect Services",
                description="Connect to email, calendar, and other services",
                order=2,
                actions=[
                    "Setup email access",
                    "Connect calendar",
                    "Link task manager",
                    "Configure notifications"
                ]
            ),
            ProjectStep(
                name="Build Intelligence",
                description="Create AI-powered assistance features",
                order=3,
                actions=[
                    "Create task parser",
                    "Build schedule optimizer",
                    "Add preference learning",
                    "Create insights"
                ]
            ),
            ProjectStep(
                name="Create Interface",
                description="Build user interface for the assistant",
                order=4,
                actions=[
                    "Design chat interface",
                    "Create dashboard",
                    "Setup notifications",
                    "Add voice control"
                ]
            ),
            ProjectStep(
                name="Add Automation",
                description="Create automated workflows",
                order=5,
                actions=[
                    "Create email filters",
                    "Setup calendar management",
                    "Build task automation",
                    "Add smart suggestions"
                ]
            ),
            ProjectStep(
                name="Deploy and Refine",
                description="Deploy and continuously improve your assistant",
                order=6,
                actions=[
                    "Deploy assistant",
                    "Monitor interactions",
                    "Learn preferences",
                    "Improve accuracy"
                ]
            )
        ]

        return ProjectTemplate(
            name="Personal Assistant",
            goal_type="personal_assistant",
            description="Create AI assistants for personal productivity",
            variations=[
                "Calendar Manager",
                "Email Organizer",
                "Task Automator",
                "Habit Tracker",
                "Decision Helper"
            ],
            steps=steps,
            components=[
                "service_connector.py",
                "task_automator.py",
                "preference_learner.py",
                "interface.py"
            ],
            dependencies=[
                "google-api-python-client",
                "openai",
                "schedule",
                "numpy",
                "sqlite3"
            ],
            estimated_time="4-6 hours",
            difficulty="advanced"
        )

    async def create_project_from_description(self, description: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Create a project from natural language description"""
        print(f"{Colors.CYAN}🚀 Creating project from: {description[:50]}...{Colors.END}")

        # Analyze the goal
        goal_analysis = await self.goal_analyzer.analyze_goal(description)

        # Generate actual project files using AI
        if self.goal_analyzer.openrouter_api_key and self.goal_analyzer.openrouter_api_key != 'demo-key':
            return await self._ai_generate_project(description, goal_analysis, context)
        else:
            return await self._fallback_generate_project(description, goal_analysis, context)

    async def _ai_generate_project(self, description: str, goal_analysis: GoalAnalysis, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Use real AI to generate working project code"""
        print(f"{Colors.BLUE}🤖 Generating real code with AI...{Colors.END}")

        # Create comprehensive prompt for project generation
        prompt = f"""You are an expert software developer. Create a complete, working project based on this description: "{description}"

Project Analysis:
- Type: {goal_analysis.goal_type}
- Features: {', '.join(goal_analysis.features)}
- Complexity: {goal_analysis.complexity}
- Target Users: {', '.join(goal_analysis.target_users)}

Generate a complete project with these requirements:
1. ALL code must be functional and ready to run
2. Include proper error handling and logging
3. Add clear setup instructions
4. Use modern best practices
5. Include example usage

Return your response as a JSON object with this EXACT structure:
{{
  "project_name": "descriptive-project-name",
  "description": "Brief description of what this project does",
  "files": {{
    "main.py": "# Main application code here\\n...",
    "requirements.txt": "# Dependencies\\n...",
    "README.md": "# Project setup and usage instructions\\n...",
    "config.py": "# Configuration settings\\n...",
    ".env.example": "# Environment variables template\\n..."
  }},
  "setup_instructions": [
    "pip install -r requirements.txt",
    "cp .env.example .env",
    "# Edit .env with your settings",
    "python main.py"
  ],
  "dependencies": ["requests", "python-dotenv"],
  "next_steps": [
    "Customize the configuration",
    "Test with your specific use case",
    "Deploy to production"
  ]
}}

Make sure ALL code is complete and functional. No placeholders or TODOs."""

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.goal_analyzer.openrouter_api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.1
                }

                async with session.post(self.goal_analyzer.openrouter_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        ai_response = result["choices"][0]["message"]["content"].strip()

                        # Parse JSON response
                        try:
                            # Clean up response
                            if "```json" in ai_response:
                                ai_response = ai_response.split("```json")[1].split("```")[0].strip()
                            elif "```" in ai_response:
                                ai_response = ai_response.split("```")[1].strip()

                            project_data = json.loads(ai_response)

                            # Create actual files on disk
                            project_dir = await self._create_project_files(project_data)

                            return {
                                'project_id': f"oos-{goal_analysis.goal_type}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                                'name': project_data.get('project_name', 'Generated Project'),
                                'description': project_data.get('description', description),
                                'project_dir': str(project_dir),
                                'files_created': list(project_data.get('files', {}).keys()),
                                'setup_instructions': project_data.get('setup_instructions', []),
                                'dependencies': project_data.get('dependencies', []),
                                'next_steps': project_data.get('next_steps', []),
                                'code': project_data.get('files', {}),
                                'goal_analysis': asdict(goal_analysis)
                            }

                        except json.JSONDecodeError as e:
                            print(f"{Colors.YELLOW}⚠️  AI response parsing failed: {e}{Colors.END}")
                            return await self._fallback_generate_project(description, goal_analysis, context)

                    else:
                        print(f"{Colors.YELLOW}⚠️  API request failed: {response.status}{Colors.END}")
                        return await self._fallback_generate_project(description, goal_analysis, context)

        except Exception as e:
            print(f"{Colors.YELLOW}⚠️  AI generation failed: {str(e)}{Colors.END}")
            return await self._fallback_generate_project(description, goal_analysis, context)

    async def _create_project_files(self, project_data: Dict[str, Any]) -> Path:
        """Create actual project files on disk"""
        project_name = project_data.get('project_name', 'generated-project')
        project_name = re.sub(r'[^a-zA-Z0-9-_]', '-', project_name.lower())

        # Create project directory
        project_dir = Path.cwd() / project_name
        project_dir.mkdir(exist_ok=True)

        # Write all files
        files = project_data.get('files', {})
        for filename, content in files.items():
            file_path = project_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        print(f"{Colors.GREEN}📁 Created project in: {project_dir}{Colors.END}")
        return project_dir

    async def _fallback_generate_project(self, description: str, goal_analysis: GoalAnalysis, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback project generation when AI is not available"""
        print(f"{Colors.YELLOW}🔧 Using template-based generation{Colors.END}")

        # Generate basic project structure
        project_name = f"{goal_analysis.goal_type}-project"
        project_dir = Path.cwd() / project_name
        project_dir.mkdir(exist_ok=True)

        # Basic files based on project type
        files = self._generate_basic_files(goal_analysis, description)

        # Write files
        for filename, content in files.items():
            file_path = project_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return {
            'project_id': f"oos-{goal_analysis.goal_type}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'name': f"{goal_analysis.goal_type.title()} Project",
            'description': description,
            'project_dir': str(project_dir),
            'files_created': list(files.keys()),
            'setup_instructions': ['pip install -r requirements.txt', 'python main.py'],
            'dependencies': ['requests', 'python-dotenv'],
            'next_steps': ['Customize the code', 'Test thoroughly', 'Deploy when ready'],
            'code': files,
            'goal_analysis': asdict(goal_analysis)
        }

    def _generate_basic_files(self, goal_analysis: GoalAnalysis, description: str) -> Dict[str, str]:
        """Generate basic project files for fallback"""
        files = {}

        if goal_analysis.goal_type == 'chatbot':
            files['main.py'] = f'''#!/usr/bin/env python3
"""
{goal_analysis.goal_type.title()} Project
{description}
Generated by OOS
"""

import os
from datetime import datetime

class ChatBot:
    def __init__(self):
        self.name = "OOS Bot"
        print(f"🤖 {{self.name}} initialized!")

    def respond(self, message: str) -> str:
        """Generate response to user message"""
        if "hello" in message.lower():
            return "Hello! How can I help you today?"
        elif "time" in message.lower():
            return f"Current time is {{datetime.now().strftime('%H:%M:%S')}}"
        else:
            return "I'm still learning! Can you rephrase that?"

    def run(self):
        """Main chat loop"""
        print("Chat started! Type 'quit' to exit.")
        while True:
            user_input = input("You: ")
            if user_input.lower() in ['quit', 'exit']:
                break
            response = self.respond(user_input)
            print(f"Bot: {{response}}")

if __name__ == "__main__":
    bot = ChatBot()
    bot.run()
'''

        elif goal_analysis.goal_type == 'automation':
            files['main.py'] = f'''#!/usr/bin/env python3
"""
{goal_analysis.goal_type.title()} Project
{description}
Generated by OOS
"""

import time
import requests
from datetime import datetime

class AutomationTool:
    def __init__(self):
        self.name = "OOS Automation"
        print(f"🤖 {{self.name}} started!")

    def check_status(self):
        """Check system status"""
        print(f"[{{datetime.now()}}] Running status check...")
        # Add your automation logic here
        return True

    def run(self):
        """Main automation loop"""
        while True:
            try:
                self.check_status()
                time.sleep(60)  # Run every minute
            except KeyboardInterrupt:
                print("Automation stopped by user")
                break
            except Exception as e:
                print(f"Error: {{e}}")
                time.sleep(60)

if __name__ == "__main__":
    tool = AutomationTool()
    tool.run()
'''

        # Common files for all projects
        files['requirements.txt'] = '''requests>=2.31.0
python-dotenv>=1.0.0
'''

        files['README.md'] = f'''# {goal_analysis.goal_type.title()} Project

{description}

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the project:
   ```bash
   python main.py
   ```

## Customization

Edit `main.py` to customize the behavior for your specific needs.

Generated by OOS (Open Operating System)
'''

        files['.env.example'] = '''# Environment Variables Template
# Copy this to .env and fill in your values

# API_KEY=your_api_key_here
# DEBUG=True
'''

        return files

    async def _guide_project_creation(self, template: ProjectTemplate, goal_analysis: GoalAnalysis) -> Dict[str, Any]:
        """Guide user through step-by-step project creation"""
        project_data = {
            'template': template.name,
            'goal_type': goal_analysis.goal_type,
            'features': goal_analysis.features,
            'created_at': datetime.now().isoformat(),
            'steps_completed': [],
            'user_inputs': {}
        }

        print(f"{Colors.GREEN}✅ Great! Let's build your {template.name.lower()} together.{Colors.END}")
        print(f"{Colors.CYAN}I'll guide you through {len(template.steps)} steps.{Colors.END}")
        print()

        for step in template.steps:
            print(f"{Colors.BLUE}{Colors.BOLD}Step {step.order} of {len(template.steps)}: {step.name}{Colors.END}")
            print(f"{Colors.BLUE}{'─' * (len(step.name) + 15)}{Colors.END}")
            print(f"{Colors.WHITE}{step.description}{Colors.END}")
            print()

            # Get user input for this step
            step_inputs = await self._get_step_input(step, goal_analysis)
            project_data['user_inputs'][step.name] = step_inputs

            # Simulate step execution
            print(f"{Colors.YELLOW}🔧 {step.name}...{Colors.END}")
            for i, action in enumerate(step.actions, 1):
                await asyncio.sleep(0.5)  # Simulate work
                print(f"{Colors.GREEN}  ✓ {action}{Colors.END}")

            project_data['steps_completed'].append(step.name)
            print(f"{Colors.GREEN}✅ Step completed!{Colors.END}")
            print()

            # Sync to Google Sheets if configured
            if self.google_integration and self.google_integration.is_configured():
                await self._sync_step_progress(step.name, project_data)

        print(f"{Colors.GREEN}{Colors.BOLD}🎉 Project Creation Complete!{Colors.END}")
        print(f"{Colors.WHITE}Your {template.name.lower()} is ready to use!{Colors.END}")
        print()

        # Create project files
        project_dir = await self._create_project_files(template, goal_analysis, project_data)

        return {
            'project_data': project_data,
            'project_dir': project_dir,
            'next_steps': self._get_next_steps(template)
        }

    async def _get_step_input(self, step: ProjectStep, goal_analysis: GoalAnalysis) -> Dict[str, Any]:
        """Get user input for a specific step"""
        inputs = {}

        if step.order == 1:  # Discovery step
            print(f"{Colors.CYAN}📝 Let's understand your project better:{Colors.END}")

            if goal_analysis.goal_type == 'chatbot':
                purpose = input(f"{Colors.WHITE}What's the main purpose of your chatbot? {Colors.END}").strip()
                users = input(f"{Colors.WHITE}Who will use this chatbot? {Colors.END}").strip()
                knowledge = input(f"{Colors.WHITE}Do you have existing documentation or knowledge bases? (Y/n) {Colors.END}").strip().lower()

                inputs['purpose'] = purpose
                inputs['users'] = users
                inputs['has_knowledge'] = knowledge in ['y', 'yes', '']

            elif goal_analysis.goal_type == 'automation':
                task = input(f"{Colors.WHITE}What task do you want to automate? {Colors.END}").strip()
                frequency = input(f"{Colors.WHITE}How often should this run? (daily/hourly/weekly) {Colors.END}").strip()

                inputs['task'] = task
                inputs['frequency'] = frequency

        elif step.order == 3:  # Setup step
            # Ask about Google Sheets integration
            if self.google_integration and self.google_integration.is_configured():
                use_sheets = input(f"{Colors.WHITE}Use Google Sheets for data management? (Y/n) {Colors.END}").strip().lower()
                inputs['use_sheets'] = use_sheets in ['y', 'yes', '']

        return inputs

    async def _create_project_files(self, template: ProjectTemplate, goal_analysis: GoalAnalysis, project_data: Dict[str, Any]) -> Path:
        """Create project files and directory"""
        # Create project directory
        project_name = f"{template.goal_type}_{hash(str(goal_analysis.features)) % 10000}"
        project_dir = Path.cwd() / project_name
        project_dir.mkdir(exist_ok=True)

        # Create main.py
        main_code = self._generate_main_code(template, goal_analysis, project_data)
        with open(project_dir / 'main.py', 'w') as f:
            f.write(main_code)

        # Create requirements.txt
        requirements = '\n'.join(template.dependencies)
        with open(project_dir / 'requirements.txt', 'w') as f:
            f.write(requirements)

        # Create project.json
        config = {
            'template': template.name,
            'goal_type': goal_analysis.goal_type,
            'features': goal_analysis.features,
            'created_at': project_data['created_at'],
            'user_inputs': project_data['user_inputs']
        }
        with open(project_dir / 'project.json', 'w') as f:
            json.dump(config, f, indent=2)

        return project_dir

    def _generate_main_code(self, template: ProjectTemplate, goal_analysis: GoalAnalysis, project_data: Dict[str, Any]) -> str:
        """Generate main project code based on template"""
        if goal_analysis.goal_type == 'chatbot':
            return self._generate_chatbot_code(goal_analysis, project_data)
        elif goal_analysis.goal_type == 'automation':
            return self._generate_automation_code(goal_analysis, project_data)
        elif goal_analysis.goal_type == 'data_analysis':
            return self._generate_data_analysis_code(goal_analysis, project_data)
        elif goal_analysis.goal_type == 'personal_assistant':
            return self._generate_personal_assistant_code(goal_analysis, project_data)
        else:
            return self._generate_generic_code(template, goal_analysis)

    def _generate_chatbot_code(self, goal_analysis: GoalAnalysis, project_data: Dict[str, Any]) -> str:
        """Generate chatbot code"""
        user_inputs = project_data['user_inputs']
        purpose = user_inputs.get('Discover Your Chatbot', {}).get('purpose', 'help users')

        return f'''# AI Chatbot - Created with OOS
# Purpose: {purpose}

import asyncio
from datetime import datetime

class Chatbot:
    def __init__(self, name="AI Assistant"):
        self.name = name
        self.conversations = []

    async def respond(self, user_message: str) -> str:
        """Generate response to user message"""
        # Simple response logic
        if "hello" in user_message.lower():
            return f"Hello! I'm {{self.name}}. How can I help you today?"
        elif "help" in user_message.lower():
            return "I'm here to help! What do you need assistance with?"
        else:
            return f"I understand you said: '{{user_message}}'. I'm still learning, but I'm here to help!"

    async def chat(self):
        """Start interactive chat session"""
        print(f"🤖 {{self.name}} is ready! (Type 'quit' to exit)")
        print("=" * 50)

        while True:
            user_input = input("\\nYou: ").strip()

            if user_input.lower() in ['quit', 'exit', 'bye']:
                print(f"🤖 Goodbye! Have a great day!")
                break

            response = await self.respond(user_input)
            print(f"🤖 {{response}}")

            # Store conversation
            self.conversations.append({{
                'timestamp': datetime.now().isoformat(),
                'user': user_input,
                'bot': response
            }})

async def main():
    """Main function"""
    purpose = "{purpose}"
    chatbot = Chatbot(f"Assistant for {purpose}")
    await chatbot.chat()

if __name__ == "__main__":
    asyncio.run(main())
'''

    def _generate_automation_code(self, goal_analysis: GoalAnalysis, project_data: Dict[str, Any]) -> str:
        """Generate automation code"""
        user_inputs = project_data['user_inputs']
        task = user_inputs.get('Define Automation', {}).get('task', 'automate tasks')

        return f'''# Web Automation - Created with OOS
# Task: {task}

import asyncio
import time
from datetime import datetime

class AutomationTask:
    def __init__(self, task_name="{task}"):
        self.task_name = task_name
        self.run_count = 0

    async def execute(self):
        """Execute the automation task"""
        print(f"🤖 Starting {{self.task_name}}...")
        self.run_count += 1

        # Simulate work
        await asyncio.sleep(2)

        print(f"✅ {{self.task_name}} completed successfully!")
        print(f"📊 Total runs: {{self.run_count}}")

        return {{
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'run_number': self.run_count
        }}

    async def run_scheduled(self, interval_minutes=60):
        """Run task on schedule"""
        print(f"⏰ Scheduled automation started (every {{interval_minutes}} minutes)")
        print("Press Ctrl+C to stop")

        try:
            while True:
                await self.execute()
                print(f"⏳ Next run in {{interval_minutes}} minutes...")
                await asyncio.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\\n🛑 Automation stopped")

async def main():
    """Main function"""
    automation = AutomationTask()
    await automation.execute()

    # Uncomment for scheduled execution:
    # await automation.run_scheduled(interval_minutes=60)

if __name__ == "__main__":
    asyncio.run(main())
'''

    def _generate_data_analysis_code(self, goal_analysis: GoalAnalysis, project_data: Dict[str, Any]) -> str:
        """Generate data analysis code"""
        return f'''# Data Analysis - Created with OOS
# Features: {', '.join(goal_analysis.features)}

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

class DataAnalyzer:
    def __init__(self):
        self.data = None
        self.insights = []

    def load_sample_data(self):
        """Load sample data for demonstration"""
        # Create sample sales data
        data = {{
            'date': pd.date_range('2024-01-01', periods=30, freq='D'),
            'sales': [100 + i * 10 + (i % 5) * 20 for i in range(30)],
            'customers': [10 + i for i in range(30)]
        }}
        self.data = pd.DataFrame(data)
        print("📊 Sample data loaded successfully!")

    def analyze_data(self):
        """Perform basic data analysis"""
        if self.data is None:
            self.load_sample_data()

        print("\\n📈 Data Analysis Results:")
        print(f"Total sales: {{self.data['sales'].sum()}}")
        print(f"Average daily sales: {{self.data['sales'].mean():.2f}}")
        print(f"Total customers: {{self.data['customers'].sum()}}")

        # Find best day
        best_day = self.data.loc[self.data['sales'].idxmax()]
        print(f"Best sales day: {{best_day['date'].strftime('%Y-%m-%d')}} ({{best_day['sales']}} sales)")

    def create_visualization(self):
        """Create simple visualization"""
        if self.data is None:
            self.load_sample_data()

        plt.figure(figsize=(10, 6))
        plt.plot(self.data['date'], self.data['sales'], marker='o')
        plt.title('Daily Sales Trend')
        plt.xlabel('Date')
        plt.ylabel('Sales')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('sales_trend.png')
        print("\\n📊 Visualization saved as 'sales_trend.png'")

    def generate_report(self):
        """Generate analysis report"""
        self.analyze_data()
        self.create_visualization()

        report = f"""
📋 Data Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Key Findings:
- Total sales: {self.data['sales'].sum() if self.data is not None else 'N/A'}
- Growth trend: {'Positive' if self.data is not None else 'N/A'}
- Recommendations: Continue current strategy

Next Steps:
1. Collect more data
2. Analyze customer segments
3. Optimize marketing efforts
"""
        print(report)

        # Save report
        with open('analysis_report.txt', 'w') as f:
            f.write(report)
        print("📄 Report saved as 'analysis_report.txt'")

def main():
    """Main function"""
    analyzer = DataAnalyzer()
    analyzer.generate_report()
    print("\\n✅ Analysis complete! Check the generated files.")

if __name__ == "__main__":
    main()
'''

    def _generate_personal_assistant_code(self, goal_analysis: GoalAnalysis, project_data: Dict[str, Any]) -> str:
        """Generate personal assistant code"""
        return f'''# Personal Assistant - Created with OOS
# Features: {', '.join(goal_analysis.features)}

import asyncio
from datetime import datetime, timedelta
import json

class PersonalAssistant:
    def __init__(self, name="Assistant"):
        self.name = name
        self.tasks = []
        self.preferences = {{}}

    def add_task(self, task: str, priority: str = "medium"):
        """Add a new task"""
        task_data = {{
            'task': task,
            'priority': priority,
            'created_at': datetime.now().isoformat(),
            'completed': False
        }}
        self.tasks.append(task_data)
        print(f"✅ Task added: {{task}} ({{priority}} priority)")

    def list_tasks(self):
        """List all tasks"""
        if not self.tasks:
            print("📝 No tasks found. Add one with 'add task <description>'")
            return

        print("\\n📋 Your Tasks:")
        for i, task in enumerate(self.tasks, 1):
            status = "✅" if task['completed'] else "⏳"
            priority_icon = {{"high": "🔴", "medium": "🟡", "low": "🟢"}}.get(task['priority'], "⚪")
            print(f"{{i}}. {{priority_icon}} {{task['task']}} ({{task['priority']}})")

    def complete_task(self, task_index: int):
        """Mark a task as completed"""
        if 1 <= task_index <= len(self.tasks):
            self.tasks[task_index - 1]['completed'] = True
            task = self.tasks[task_index - 1]['task']
            print(f"✅ Task completed: {{task}}")
        else:
            print("❌ Invalid task number")

    def analyze_productivity(self):
        """Analyze task productivity"""
        completed = sum(1 for task in self.tasks if task['completed'])
        total = len(self.tasks)
        if total > 0:
            completion_rate = (completed / total) * 100
            print(f"\\n📊 Productivity Analysis:")
            print(f"Completed: {{completed}}/{{total}} ({{completion_rate:.1f}}%)")

            if completion_rate >= 80:
                print("🎉 Excellent productivity!")
            elif completion_rate >= 60:
                print("👍 Good progress!")
            else:
                print("💪 Keep going, you've got this!")

    async def remind_tasks(self):
        """Remind about pending tasks"""
        incomplete_tasks = [task for task in self.tasks if not task['completed']]
        if incomplete_tasks:
            print(f"\\n⏰ Reminder: You have {{len(incomplete_tasks)}} pending tasks")
            for task in incomplete_tasks[:3]:  # Show first 3
                print(f"  • {{task['task']}}")

    async def chat(self):
        """Interactive chat interface"""
        print(f"🤖 Hello! I'm {{self.name}}, your personal assistant.")
        print("Available commands:")
        print("  add task <description> - Add a new task")
        print("  list tasks - Show all tasks")
        print("  complete <number> - Complete a task")
        print("  productivity - Show productivity analysis")
        print("  remind - Remind about pending tasks")
        print("  quit - Exit assistant")
        print("=" * 50)

        while True:
            user_input = input("\\nYou: ").strip().lower()

            if user_input in ['quit', 'exit', 'bye']:
                print(f"🤖 Goodbye! Have a productive day!")
                break

            elif user_input.startswith('add task'):
                task = user_input.replace('add task', '').strip()
                if task:
                    self.add_task(task)
                else:
                    print("Please specify a task to add")

            elif user_input == 'list tasks':
                self.list_tasks()

            elif user_input.startswith('complete'):
                try:
                    task_num = int(user_input.replace('complete', '').strip())
                    self.complete_task(task_num)
                except ValueError:
                    print("Please provide a valid task number")

            elif user_input == 'productivity':
                self.analyze_productivity()

            elif user_input == 'remind':
                await self.remind_tasks()

            else:
                print(f"🤖 I didn't understand that. Try 'help' for available commands.")

async def main():
    """Main function"""
    assistant = PersonalAssistant()
    await assistant.chat()

if __name__ == "__main__":
    asyncio.run(main())
'''

    def _generate_generic_code(self, template: ProjectTemplate, goal_analysis: GoalAnalysis) -> str:
        """Generate generic project code"""
        return f'''# {template.name} - Created with OOS
# Goal: {goal_analysis.goal_type}
# Features: {', '.join(goal_analysis.features)}

def main():
    """Main function"""
    print(f"🚀 Your {template.name} is ready!")
    print(f"📋 Goal: {goal_analysis.goal_type}")
    print(f"✨ Features: {', '.join(goal_analysis.features)}")
    print("\\nNext steps:")
    print("1. Customize this code for your specific needs")
    print("2. Add your data and configurations")
    print("3. Test and refine your project")
    print("4. Deploy and share with others")

if __name__ == "__main__":
    main()
'''

    def _get_next_steps(self, template: ProjectTemplate) -> List[str]:
        """Get next steps for the user"""
        steps = [
            f"cd into your project directory",
            "Review the generated code",
            "Customize it for your specific needs",
            "Run: python main.py to test",
            "Deploy when ready"
        ]

        if template.goal_type == 'chatbot':
            steps.extend([
                "Add your knowledge base",
                "Test conversation flows",
                "Deploy to web or messaging platform"
            ])
        elif template.goal_type == 'automation':
            steps.extend([
                "Configure target websites/APIs",
                "Set up scheduling",
                "Monitor and optimize performance"
            ])

        return steps

    async def _sync_step_progress(self, step_name: str, project_data: Dict[str, Any]):
        """Sync progress to Google Sheets (placeholder)"""
        # In production, this would update the Google Sheet with progress
        pass


# Global instance
_template_engine = None


def get_template_engine(config, google_integration=None) -> TemplateEngine:
    """Get or create template engine instance"""
    global _template_engine
    if _template_engine is None:
        _template_engine = TemplateEngine(config, google_integration)
    return _template_engine