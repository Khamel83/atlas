"""
OOS Persistent Daemon
Always-listening AI assistant that processes ideas in the background
"""

import asyncio
import json
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from renderers import Colors
from background_processor import BackgroundProcessor, Idea as BackgroundIdea, get_background_processor


@dataclass
class Idea:
    """User idea that needs processing"""
    id: str
    content: str
    source: str  # voice, terminal, chat, ide
    user_id: str
    timestamp: str
    project_id: Optional[str] = None
    attachments: List[str] = None
    priority: str = "normal"  # low, normal, high, urgent


@dataclass
class IdeaUnderstanding:
    """Result of understanding user's idea"""
    goal_type: str
    features: List[str]
    requirements: List[str]
    constraints: List[str]
    confidence: float
    missing_info: List[str]
    estimated_effort: str


@dataclass
class GerminationResult:
    """Result of idea processing"""
    idea_id: str
    status: str  # processing, needs_input, completed, blocked
    progress: float  # 0.0 to 1.0
    understanding: IdeaUnderstanding
    artifacts: Dict[str, Any]
    next_steps: List[str]
    user_questions: List[str]
    created_at: str
    updated_at: str


class OOSDaemon:
    """Main OOS daemon that runs persistently in the background"""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.running = False
        self.config = self._load_config()

        # Initialize background processor
        self.background_processor = get_background_processor(self.config)

        # Legacy components for backward compatibility
        self.idea_queue: List[Idea] = []
        self.active_projects: Dict[str, GerminationResult] = {}
        self.processing_tasks: Dict[str, asyncio.Task] = {}

        # Initialize components
        self.idea_processor = IdeaProcessor(config_dir)
        self.persistence = ProjectPersistence(config_dir)
        self.notifications = NotificationSystem()

        # Daemon state
        self.start_time = datetime.now()
        self.ideas_processed = 0
        self.projects_created = 0

    async def start(self):
        """Start the OOS daemon"""
        print(f"{Colors.GREEN}🚀 Starting OOS Persistent Daemon{Colors.END}")
        print(f"{Colors.CYAN}🎧 Listening for 'hey OOS' activation...{Colors.END}")

        self.running = True

        # Load previous state
        await self.load_state()

        # Start background processor
        bg_processor_task = asyncio.create_task(self.background_processor.start())

        # Start legacy processing for backward compatibility
        processing_task = asyncio.create_task(self.process_idea_queue())

        # Start input monitoring
        monitor_task = asyncio.create_task(self.monitor_input_sources())

        # Setup signal handlers
        self.setup_signal_handlers()

        try:
            # Main daemon loop
            while self.running:
                await asyncio.sleep(1)
                await self.cleanup_completed_tasks()

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}🛑 Shutting down OOS daemon...{Colors.END}")
            await self.shutdown()

        except Exception as e:
            print(f"{Colors.RED}❌ Daemon error: {e}{Colors.END}")
            await self.shutdown()

    async def monitor_input_sources(self):
        """Monitor various input sources for OOS activation"""
        print(f"{Colors.BLUE}📡 Monitoring input sources...{Colors.END}")

        while self.running:
            try:
                # Monitor terminal for "hey OOS" commands
                await self.monitor_terminal()

                # Monitor file-based input (for demo)
                await self.monitor_input_file()

                # In production, would also monitor:
                # - Microphone for wake word detection
                # - IDE plugins
                # - Chat applications
                # - Voice assistants

                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"{Colors.RED}Input monitoring error: {e}{Colors.END}")
                await asyncio.sleep(1)

    async def monitor_terminal(self):
        """Monitor terminal input for OOS activation"""
        # Check for terminal commands that start with wake phrases
        wake_phrases = ["hey oos", "oos", "hey OOS", "OOS"]

        # Monitor for environment variable or signal file
        wake_file = self.config_dir / 'wake_signal.txt'
        if wake_file.exists():
            try:
                content = wake_file.read_text().strip()
                if content:
                    # Check if it starts with wake phrase
                    content_lower = content.lower()
                    activated = any(content_lower.startswith(phrase.lower()) for phrase in wake_phrases)

                    if activated:
                        # Remove wake phrase and process the idea
                        for phrase in wake_phrases:
                            if content_lower.startswith(phrase.lower()):
                                clean_content = content[len(phrase):].strip()
                                break

                        if clean_content:
                            print(f"{Colors.CYAN}🎧 Wake word detected: Processing '{clean_content}'{Colors.END}")

                            idea = Idea(
                                id=str(uuid.uuid4()),
                                content=clean_content,
                                source="terminal_wake",
                                user_id="user",
                                timestamp=datetime.now().isoformat(),
                                priority="high"  # Wake word activation gets higher priority
                            )

                            await self.add_idea(idea)

                    # Clear the wake signal file
                    wake_file.write_text("")

            except Exception as e:
                print(f"{Colors.RED}Error processing wake signal: {e}{Colors.END}")

    async def monitor_input_file(self):
        """Monitor input file for demo purposes"""
        input_file = self.config_dir / 'input.txt'

        if input_file.exists():
            try:
                content = input_file.read_text().strip()
                if content:
                    # Process the input
                    idea = Idea(
                        id=str(uuid.uuid4()),
                        content=content,
                        source="terminal",
                        user_id="demo_user",
                        timestamp=datetime.now().isoformat()
                    )

                    await self.add_idea(idea)

                    # Clear the input file
                    input_file.write_text("")

            except Exception as e:
                print(f"{Colors.RED}Error reading input file: {e}{Colors.END}")

    async def add_idea(self, idea: Idea):
        """Add new idea to processing queue"""
        print(f"{Colors.CYAN}💡 Idea captured: {idea.content[:50]}...{Colors.END}")

        # Convert to background processor idea format
        bg_idea = BackgroundIdea(
            id=idea.id,
            content=idea.content,
            user_id=idea.user_id,
            source=idea.source,
            timestamp=datetime.now(),
            priority=8 if idea.priority == "urgent" else 5 if idea.priority == "high" else 3,
            context={}
        )

        # Add to background processor
        await self.background_processor.add_idea(bg_idea)

        # Save idea to persistent storage
        await self.persistence.save_idea(idea)

        # Add to legacy queue for backward compatibility
        self.idea_queue.append(idea)

        # Notify user
        await self.notifications.notify_idea_received(idea)

    async def process_idea_queue(self):
        """Process ideas from the queue continuously"""
        print(f"{Colors.BLUE}⚙️  Idea processor started{Colors.END}")

        while self.running:
            try:
                if self.idea_queue:
                    idea = self.idea_queue.pop(0)

                    # Start processing this idea
                    task = asyncio.create_task(self.process_single_idea(idea))
                    self.processing_tasks[idea.id] = task

                    # Limit concurrent processing
                    if len(self.processing_tasks) >= 3:
                        await asyncio.sleep(1)

                else:
                    await asyncio.sleep(0.5)

            except Exception as e:
                print(f"{Colors.RED}Queue processing error: {e}{Colors.END}")
                await asyncio.sleep(1)

    async def process_single_idea(self, idea: Idea):
        """Process a single idea through germination"""
        try:
            print(f"{Colors.YELLOW}🌱 Processing idea: {idea.content[:30]}...{Colors.END}")

            # Update status: processing
            await self.persistence.update_idea_status(idea.id, "processing")

            # Process the idea
            result = await self.idea_processor.process_idea(idea)

            # Store result
            self.active_projects[idea.id] = result
            await self.persistence.save_germination_result(result)

            # Update statistics
            self.ideas_processed += 1
            if result.status == "completed":
                self.projects_created += 1

            # Notify user based on status
            if result.status == "needs_input":
                await self.notifications.request_user_input(idea, result)
            elif result.status == "completed":
                await self.notifications.notify_completion(idea, result)
            elif result.status == "blocked":
                await self.notifications.notify_blocked(idea, result)

            print(f"{Colors.GREEN}✅ Idea processed: {result.status} ({result.progress:.0%}){Colors.END}")

        except Exception as e:
            print(f"{Colors.RED}❌ Error processing idea {idea.id}: {e}{Colors.END}")
            await self.handle_processing_error(idea, e)

    async def handle_processing_error(self, idea: Idea, error: Exception):
        """Handle errors during idea processing"""
        error_result = GerminationResult(
            idea_id=idea.id,
            status="error",
            progress=0.0,
            understanding=IdeaUnderstanding(
                goal_type="unknown",
                features=[],
                requirements=[],
                constraints=[],
                confidence=0.0,
                missing_info=[],
                estimated_effort="unknown"
            ),
            artifacts={"error": str(error)},
            next_steps=["Please provide more clarity about what you want to build"],
            user_questions=["Can you describe your idea in more detail?"],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        await self.persistence.save_germination_result(error_result)
        await self.notifications.notify_error(idea, error)

    async def cleanup_completed_tasks(self):
        """Clean up completed processing tasks"""
        completed = [
            task_id for task_id, task in self.processing_tasks.items()
            if task.done()
        ]

        for task_id in completed:
            del self.processing_tasks[task_id]

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print(f"\n{Colors.YELLOW}📡 Received signal {signum}{Colors.END}")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def shutdown(self):
        """Gracefully shutdown the daemon"""
        print(f"{Colors.YELLOW}🔄 Shutting down OOS daemon...{Colors.END}")

        self.running = False

        # Stop background processor
        await self.background_processor.stop()

        # Wait for processing tasks to complete
        if self.processing_tasks:
            print(f"{Colors.YELLOW}⏳ Waiting for {len(self.processing_tasks)} tasks to complete...{Colors.END}")
            await asyncio.gather(*self.processing_tasks.values(), return_exceptions=True)

        # Save state
        await self.save_state()

        print(f"{Colors.GREEN}✅ OOS daemon stopped{Colors.END}")
        print(f"{Colors.CYAN}📊 Session stats: {self.ideas_processed} ideas processed, {self.projects_created} projects created{Colors.END}")

    async def save_state(self):
        """Save daemon state for recovery"""
        state = {
            'start_time': self.start_time.isoformat(),
            'ideas_processed': self.ideas_processed,
            'projects_created': self.projects_created,
            'active_projects': {k: asdict(v) for k, v in self.active_projects.items()}
        }

        state_file = self.config_dir / 'daemon_state.json'
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    async def load_state(self):
        """Load previous daemon state"""
        state_file = self.config_dir / 'daemon_state.json'

        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)

                self.start_time = datetime.fromisoformat(state['start_time'])
                self.ideas_processed = state.get('ideas_processed', 0)
                self.projects_created = state.get('projects_created', 0)

                # Load active projects
                for proj_id, proj_data in state.get('active_projects', {}).items():
                    # Reconstruct GerminationResult (simplified)
                    self.active_projects[proj_id] = GerminationResult(**proj_data)

                print(f"{Colors.GREEN}📂 Loaded previous state: {self.ideas_processed} ideas, {self.projects_created} projects{Colors.END}")

            except Exception as e:
                print(f"{Colors.YELLOW}⚠️  Could not load previous state: {e}{Colors.END}")

    def _load_config(self) -> Dict[str, Any]:
        """Load daemon configuration"""
        config_file = self.config_dir / 'config.json'

        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"{Colors.YELLOW}⚠️  Could not load config: {e}{Colors.END}")

        # Default configuration
        return {
            'google_enabled': False,
            'openrouter_api_key': '',
            'max_concurrent_ideas': 3,
            'cleanup_interval': 3600
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current daemon status"""
        return {
            'running': self.running,
            'uptime': str(datetime.now() - self.start_time),
            'ideas_processed': self.ideas_processed,
            'projects_created': self.projects_created,
            'queue_size': len(self.idea_queue),
            'active_tasks': len(self.processing_tasks),
            'active_projects': len(self.active_projects),
            'background_processor': {
                'active_ideas': len(self.background_processor.active_ideas),
                'max_concurrent': self.background_processor.max_concurrent_ideas
            }
        }


class IdeaProcessor:
    """Processes user ideas through germination phases"""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        from template_engine import get_template_engine
        from google_sheets_integration import get_sheets_integration

        self.template_engine = get_template_engine({'api_key': 'demo'})
        self.google_sheets = get_sheets_integration(config_dir)

    async def process_idea(self, idea: Idea) -> GerminationResult:
        """Process idea through germination phases"""

        # Phase 1: Understanding
        understanding = await self.understand_idea(idea)

        # Phase 2: Research & Planning
        research = await self.research_approaches(understanding)

        # Phase 3: Creation
        creation = await self.create_solution(idea, understanding, research)

        # Phase 4: Refinement
        refinement = await self.refine_solution(creation)

        # Determine status
        status = self.determine_status(refinement)

        return GerminationResult(
            idea_id=idea.id,
            status=status,
            progress=self.calculate_progress(refinement),
            understanding=understanding,
            artifacts=refinement,
            next_steps=self.extract_next_steps(refinement),
            user_questions=self.extract_user_questions(refinement),
            created_at=idea.timestamp,
            updated_at=datetime.now().isoformat()
        )

    async def understand_idea(self, idea: Idea) -> IdeaUnderstanding:
        """Extract goals and requirements from user input"""
        print(f"{Colors.BLUE}🔍 Understanding idea: {idea.content}{Colors.END}")

        try:
            # Use template engine for goal analysis
            goal_analysis = await self.template_engine.goal_analyzer.analyze_goal(idea.content)

            return IdeaUnderstanding(
                goal_type=goal_analysis.goal_type,
                features=goal_analysis.features,
                requirements=self.extract_requirements(goal_analysis),
                constraints=self.extract_constraints(idea.content),
                confidence=goal_analysis.confidence,
                missing_info=self.identify_missing_info(goal_analysis),
                estimated_effort=goal_analysis.estimated_time
            )

        except Exception as e:
            print(f"{Colors.RED}Error understanding idea: {e}{Colors.END}")
            return IdeaUnderstanding(
                goal_type="unknown",
                features=[],
                requirements=[],
                constraints=[],
                confidence=0.0,
                missing_info=["Could not understand the idea"],
                estimated_effort="unknown"
            )

    def extract_requirements(self, goal_analysis) -> List[str]:
        """Extract requirements from goal analysis"""
        requirements = []

        if goal_analysis.goal_type == "chatbot":
            requirements.extend(["AI model integration", "Conversation handling"])
            if "knowledge_base" in goal_analysis.features:
                requirements.append("Knowledge base integration")
            if "human_handoff" in goal_analysis.features:
                requirements.append("Human escalation system")

        elif goal_analysis.goal_type == "automation":
            requirements.extend(["Task scheduling", "Error handling"])
            if "web_scraping" in goal_analysis.features:
                requirements.append("Web scraping capabilities")
            if "email_integration" in goal_analysis.features:
                requirements.append("Email system integration")

        return requirements

    def extract_constraints(self, content: str) -> List[str]:
        """Extract constraints from user input"""
        constraints = []
        content_lower = content.lower()

        if any(word in content_lower for word in ['free', 'no cost', 'cheap']):
            constraints.append("Cost-effective solution")
        if any(word in content_lower for word in ['simple', 'easy', 'basic']):
            constraints.append("Simple implementation")
        if any(word in content_lower for word in ['fast', 'quick', 'immediate']):
            constraints.append("Quick deployment")

        return constraints

    def identify_missing_info(self, goal_analysis) -> List[str]:
        """Identify what information is missing"""
        missing = []

        if goal_analysis.confidence < 0.7:
            missing.append("More specific requirements needed")

        if not goal_analysis.features:
            missing.append("Specific features desired")

        if goal_analysis.goal_type == "unknown":
            missing.append("Clarify project type")

        return missing

    async def research_approaches(self, understanding: IdeaUnderstanding) -> Dict[str, Any]:
        """Research best approaches for the idea"""
        print(f"{Colors.BLUE}📚 Researching approaches for {understanding.goal_type}{Colors.END}")

        # Simulate research (in production, would use web search, docs, etc.)
        research = {
            'best_practices': [],
            'recommended_tools': [],
            'potential_challenges': [],
            'estimated_complexity': understanding.estimated_effort
        }

        if understanding.goal_type == "chatbot":
            research.update({
                'best_practices': ['Clear conversation flows', 'Error handling', 'User testing'],
                'recommended_tools': ['OpenAI API', 'LangChain', 'FastAPI'],
                'potential_challenges': ['API rate limits', 'Context management']
            })

        elif understanding.goal_type == "automation":
            research.update({
                'best_practices': ['Robust error handling', 'Logging', 'Scheduling'],
                'recommended_tools': ['Requests', 'BeautifulSoup', 'Schedule'],
                'potential_challenges': ['Website changes', 'Rate limiting']
            })

        return research

    async def create_solution(self, idea: Idea, understanding: IdeaUnderstanding, research: Dict[str, Any]) -> Dict[str, Any]:
        """Create initial solution based on research"""
        print(f"{Colors.BLUE}🛠️  Creating solution for {understanding.goal_type}{Colors.END}")

        creation = {
            'project_structure': self.generate_project_structure(understanding),
            'code_files': self.generate_initial_code(understanding),
            'dependencies': research['recommended_tools'],
            'setup_instructions': self.generate_setup_instructions(understanding)
        }

        return creation

    def generate_project_structure(self, understanding: IdeaUnderstanding) -> Dict[str, Any]:
        """Generate project directory structure"""
        base_name = understanding.goal_type.replace('_', '-')

        return {
            'directories': [
                f"{base_name}/",
                f"{base_name}/src/",
                f"{base_name}/tests/",
                f"{base_name}/docs/",
                f"{base_name}/config/"
            ],
            'files': [
                f"{base_name}/README.md",
                f"{base_name}/requirements.txt",
                f"{base_name}/src/main.py",
                f"{base_name}/config/settings.json"
            ]
        }

    def generate_initial_code(self, understanding: IdeaUnderstanding) -> Dict[str, str]:
        """Generate initial code files"""
        main_code = f"""# {understanding.goal_type.title()} Project
# Generated by OOS

import asyncio
from datetime import datetime

def main():
    print("🚀 {understanding.goal_type.title()} project starting...")
    # Add your implementation here

if __name__ == "__main__":
    main()
"""

        return {
            'main.py': main_code,
            'README.md': f"# {understanding.goal_type.title()} Project\n\nGenerated by OOS\n",
            'requirements.txt': "\n".join(research['recommended_tools']) if 'recommended_tools' in research else ""
        }

    def generate_setup_instructions(self, understanding: IdeaUnderstanding) -> List[str]:
        """Generate setup instructions"""
        return [
            f"Navigate to project directory: cd {understanding.goal_type}",
            "Install dependencies: pip install -r requirements.txt",
            "Run the project: python src/main.py",
            "Customize as needed for your specific use case"
        ]

    async def refine_solution(self, creation: Dict[str, Any]) -> Dict[str, Any]:
        """Refine and improve the initial solution"""
        print(f"{Colors.BLUE}🔧 Refining solution{Colors.END}")

        # Add refinements
        creation['refinements'] = [
            "Added error handling",
            "Improved code structure",
            "Added documentation",
            "Optimized performance"
        ]

        creation['quality_score'] = 0.85  # Simulated quality assessment

        return creation

    def determine_status(self, refinement: Dict[str, Any]) -> str:
        """Determine the status of idea processing"""
        quality_score = refinement.get('quality_score', 0.5)

        if quality_score >= 0.8:
            return "completed"
        elif quality_score >= 0.5:
            return "needs_input"
        else:
            return "blocked"

    def calculate_progress(self, refinement: Dict[str, Any]) -> float:
        """Calculate progress percentage"""
        quality_score = refinement.get('quality_score', 0.0)
        return min(quality_score, 1.0)

    def extract_next_steps(self, refinement: Dict[str, Any]) -> List[str]:
        """Extract next steps for the user"""
        return [
            "Review the generated code",
            "Test the basic functionality",
            "Customize for your specific needs",
            "Deploy to production"
        ]

    def extract_user_questions(self, refinement: Dict[str, Any]) -> List[str]:
        """Extract questions for the user"""
        return [
            "What specific features do you need?",
            "Do you have any existing data or APIs to integrate?",
            "What's your timeline for this project?"
        ]


class ProjectPersistence:
    """Manages project persistence across sessions"""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.data_dir = config_dir / 'persistence'
        self.data_dir.mkdir(exist_ok=True)

    async def save_idea(self, idea: Idea):
        """Save idea to persistent storage"""
        idea_file = self.data_dir / f"idea_{idea.id}.json"
        with open(idea_file, 'w') as f:
            json.dump(asdict(idea), f, indent=2)

    async def update_idea_status(self, idea_id: str, status: str):
        """Update idea processing status"""
        status_file = self.data_dir / f"status_{idea_id}.json"
        with open(status_file, 'w') as f:
            json.dump({
                'idea_id': idea_id,
                'status': status,
                'updated_at': datetime.now().isoformat()
            }, f, indent=2)

    async def save_germination_result(self, result: GerminationResult):
        """Save germination result"""
        result_file = self.data_dir / f"result_{result.idea_id}.json"
        with open(result_file, 'w') as f:
            json.dump(asdict(result), f, indent=2, default=str)


class NotificationSystem:
    """Handles user notifications"""

    async def notify_idea_received(self, idea: Idea):
        """Notify user that idea was received"""
        print(f"{Colors.GREEN}✅ Idea received! Processing: {idea.content[:30]}...{Colors.END}")

    async def request_user_input(self, idea: Idea, result: GerminationResult):
        """Request additional input from user"""
        print(f"\n{Colors.YELLOW}🤔 I need more information for your idea:{Colors.END}")
        print(f"{Colors.WHITE}Idea: {idea.content}{Colors.END}")
        print(f"{Colors.CYAN}Questions:{Colors.END}")
        for question in result.user_questions:
            print(f"  • {question}")

    async def notify_completion(self, idea: Idea, result: GerminationResult):
        """Notify user that idea processing is complete"""
        print(f"\n{Colors.GREEN}🎉 Your idea is ready!{Colors.END}")
        print(f"{Colors.WHITE}Idea: {idea.content}{Colors.END}")
        print(f"{Colors.CYAN}Progress: {result.progress:.0%} complete{Colors.END}")
        print(f"{Colors.CYAN}Next steps:{Colors.END}")
        for step in result.next_steps:
            print(f"  • {step}")

    async def notify_blocked(self, idea: Idea, result: GerminationResult):
        """Notify user that idea processing is blocked"""
        print(f"\n{Colors.RED}🚧 Idea processing blocked{Colors.END}")
        print(f"{Colors.WHITE}Idea: {idea.content}{Colors.END}")
        print(f"{Colors.YELLOW}Need to resolve:{Colors.END}")
        for question in result.user_questions:
            print(f"  • {question}")

    async def notify_error(self, idea: Idea, error: Exception):
        """Notify user of processing error"""
        print(f"\n{Colors.RED}❌ Error processing idea{Colors.END}")
        print(f"{Colors.WHITE}Idea: {idea.content}{Colors.END}")
        print(f"{Colors.RED}Error: {error}{Colors.END}")


# Global daemon instance
_daemon = None


def get_daemon(config_dir: Path) -> OOSDaemon:
    """Get or create daemon instance"""
    global _daemon
    if _daemon is None:
        _daemon = OOSDaemon(config_dir)
    return _daemon


async def start_daemon(config_dir: Path):
    """Start the OOS daemon"""
    daemon = get_daemon(config_dir)
    await daemon.start()


if __name__ == "__main__":
    # For standalone daemon execution
    config_dir = Path.home() / '.oos'
    config_dir.mkdir(exist_ok=True)

    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("   🚀 OOS Persistent Daemon                                   ║")
    print("   Always-listening AI development partner                     ║")
    print("                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    try:
        asyncio.run(start_daemon(config_dir))
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}👋 OOS daemon stopped by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}💥 Daemon crashed: {e}{Colors.END}")
        sys.exit(1)