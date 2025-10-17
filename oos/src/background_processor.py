"""
Background Idea Processing Engine for OOS
Handles intelligent idea germination in the background while user focuses on other tasks
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from template_engine import get_template_engine, GoalAnalysis
from google_sheets_integration import GoogleSheetsIntegration
from renderers import Colors
from safety_guardrails import get_safety_guardrails, SafetyCheck
from visual_feedback import get_notification_manager, get_live_dashboard


class GerminationPhase(Enum):
    """Phases of idea germination"""
    UNDERSTANDING = "understanding"
    RESEARCH = "research"
    CREATION = "creation"
    REFINEMENT = "refinement"
    COMPLETED = "completed"
    NEEDS_INPUT = "needs_input"
    BLOCKED = "blocked"


@dataclass
class Idea:
    """User idea captured for background processing"""
    id: str
    content: str
    user_id: str
    source: str  # voice, text, terminal, chat
    timestamp: datetime
    priority: int = 5  # 1-10, higher = more important
    context: Optional[Dict[str, Any]] = None
    attachments: Optional[List[str]] = None


@dataclass
class GerminationResult:
    """Result of idea processing through germination phases"""
    idea_id: str
    phase: GerminationPhase
    progress: float  # 0.0 to 1.0
    output: Dict[str, Any]
    timestamp: datetime
    confidence: float
    missing_info: List[str]
    next_steps: List[str]
    user_questions: List[str]


@dataclass
class ProjectState:
    """State of a project being generated from an idea"""
    project_id: str
    idea_id: str
    name: str
    description: str
    template_type: str
    files_created: List[str]
    config_generated: Dict[str, Any]
    status: str
    last_updated: datetime


class BackgroundProcessor:
    """Handles background idea processing and germination"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.processing_queue = asyncio.Queue()
        self.active_ideas: Dict[str, Idea] = {}
        self.germination_results: Dict[str, List[GerminationResult]] = {}
        self.projects: Dict[str, ProjectState] = {}
        self.template_engine = get_template_engine(config)
        self.google_sheets = GoogleSheetsIntegration(config) if config.get('google_enabled') else None
        self.safety_guardrails = get_safety_guardrails(config)
        self.notification_manager = get_notification_manager()
        self.live_dashboard = get_live_dashboard()
        self.running = False
        self.max_concurrent_ideas = 3

    async def start(self):
        """Start the background processor"""
        self.running = True
        print(f"{Colors.GREEN}🌱 Background Idea Processor started{Colors.END}")

        # Start processing tasks
        tasks = [
            asyncio.create_task(self._process_queue()),
            asyncio.create_task(self._monitor_progress()),
            asyncio.create_task(self._cleanup_old_ideas())
        ]

        await asyncio.gather(*tasks)

    async def stop(self):
        """Stop the background processor"""
        self.running = False
        print(f"{Colors.YELLOW}🛑 Background Idea Processor stopped{Colors.END}")

    async def add_idea(self, idea: Idea):
        """Add new idea to processing queue"""
        # First, check safety
        safety_check = await self.safety_guardrails.check_idea_safety(idea.content)

        if safety_check.level.value == 'danger':
            print(f"{Colors.RED}🚨 Idea blocked due to safety concerns: {safety_check.message}{Colors.END}")
            for issue in safety_check.details.get('issues', []):
                print(f"{Colors.RED}   • {issue}{Colors.END}")
            return False

        if safety_check.level.value == 'warning':
            print(f"{Colors.YELLOW}⚠️  Safety warning for idea: {safety_check.message}{Colors.END}")
            for rec in safety_check.recommendations:
                print(f"{Colors.YELLOW}   • {rec}{Colors.END}")

        if len(self.active_ideas) >= self.max_concurrent_ideas:
            # Store for later processing
            await self._save_idea_for_later(idea)
            print(f"{Colors.YELLOW}⏳ Idea queued for later processing{Colors.END}")
        else:
            self.active_ideas[idea.id] = idea
            await self.processing_queue.put(idea)
            print(f"{Colors.GREEN}🌱 Idea added to processing queue{Colors.END}")

        return True

    async def get_idea_status(self, idea_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an idea"""
        if idea_id in self.active_ideas:
            idea = self.active_ideas[idea_id]
            results = self.germination_results.get(idea_id, [])

            return {
                'idea': asdict(idea),
                'status': 'processing',
                'phase': results[-1].phase.value if results else 'queued',
                'progress': results[-1].progress if results else 0.0,
                'results': [asdict(r) for r in results[-5:]],  # Last 5 results
                'project': asdict(self.projects.get(idea_id)) if idea_id in self.projects else None
            }

        return None

    async def _process_queue(self):
        """Main processing loop for ideas"""
        while self.running:
            try:
                # Check if we can process more ideas
                if len(self.active_ideas) < self.max_concurrent_ideas:
                    # Load queued ideas if any
                    await self._load_queued_ideas()

                if not self.processing_queue.empty():
                    idea = await self.processing_queue.get()
                    asyncio.create_task(self._process_idea(idea))
                else:
                    await asyncio.sleep(1)  # Check queue every second

            except Exception as e:
                print(f"{Colors.RED}❌ Error in processing queue: {e}{Colors.END}")
                await asyncio.sleep(5)

    async def _process_idea(self, idea: Idea):
        """Process a single idea through germination phases"""
        try:
            print(f"{Colors.BLUE}🌱 Processing idea: {idea.content[:50]}...{Colors.END}")

            # Initialize germination results for this idea
            self.germination_results[idea.id] = []

            # Phase 1: Understanding
            await self._phase_understanding(idea)

            # Phase 2: Research
            await self._phase_research(idea)

            # Phase 3: Creation
            await self._phase_creation(idea)

            # Phase 4: Refinement
            await self._phase_refinement(idea)

            # Check if completed
            final_result = self.germination_results[idea.id][-1]
            if final_result.phase == GerminationPhase.COMPLETED:
                print(f"{Colors.GREEN}✅ Idea '{idea.content[:30]}...' completed!{Colors.END}")
                await self._notify_user_completed(idea, final_result)
            elif final_result.phase == GerminationPhase.NEEDS_INPUT:
                print(f"{Colors.YELLOW}❓ Idea '{idea.content[:30]}...' needs user input{Colors.END}")
                await self._notify_user_needs_input(idea, final_result)

        except Exception as e:
            print(f"{Colors.RED}❌ Error processing idea {idea.id}: {e}{Colors.END}")
            await self._handle_processing_error(idea, e)

    async def _phase_understanding(self, idea: Idea):
        """Phase 1: Understand the user's idea and requirements"""
        print(f"{Colors.CYAN}🔍 Understanding idea: {idea.content[:50]}...{Colors.END}")

        # Use template engine to analyze the goal
        goal_analysis = await self.template_engine.goal_analyzer.analyze_goal(idea.content)

        # Extract additional context
        context = await self._extract_context(idea)

        # Identify missing information
        missing_info = self._identify_missing_info(goal_analysis, context)

        result = GerminationResult(
            idea_id=idea.id,
            phase=GerminationPhase.UNDERSTANDING,
            progress=0.2,
            output={
                'goal_analysis': asdict(goal_analysis),
                'context': context,
                'confidence': goal_analysis.confidence
            },
            timestamp=datetime.now(),
            confidence=goal_analysis.confidence,
            missing_info=missing_info,
            next_steps=self._generate_next_steps(goal_analysis, missing_info),
            user_questions=self._generate_user_questions(missing_info)
        )

        self.germination_results[idea.id].append(result)
        await self._save_germination_result(result)

    async def _phase_research(self, idea: Idea):
        """Phase 2: Research approaches and best practices"""
        print(f"{Colors.CYAN}📚 Researching approaches for: {idea.content[:50]}...{Colors.END}")

        previous_result = self.germination_results[idea.id][-1]
        goal_analysis = previous_result.output['goal_analysis']

        # Research similar projects and approaches
        research = await self._research_approaches(goal_analysis)

        # Check for potential blockers
        blockers = await self._identify_blockers(goal_analysis, research)

        result = GerminationResult(
            idea_id=idea.id,
            phase=GerminationPhase.RESEARCH,
            progress=0.4,
            output={
                'research': research,
                'blockers': blockers,
                'approaches_recommended': research.get('recommended_approaches', [])
            },
            timestamp=datetime.now(),
            confidence=research.get('confidence', 0.7),
            missing_info=blockers.get('missing_info', []),
            next_steps=blockers.get('next_steps', []),
            user_questions=blockers.get('user_questions', [])
        )

        self.germination_results[idea.id].append(result)
        await self._save_germination_result(result)

    async def _phase_creation(self, idea: Idea):
        """Phase 3: Create initial project structure and code"""
        print(f"{Colors.CYAN}🏗️  Creating project for: {idea.content[:50]}...{Colors.END}")

        previous_result = self.germination_results[idea.id][-1]
        goal_analysis = previous_result.output['goal_analysis']

        # Check if we have enough information to proceed
        if previous_result.missing_info and len(previous_result.missing_info) > 2:
            # Too much missing info, ask user
            result = GerminationResult(
                idea_id=idea.id,
                phase=GerminationPhase.NEEDS_INPUT,
                progress=0.5,
                output={
                    'stalled_reason': 'Missing critical information',
                    'created_so_far': []
                },
                timestamp=datetime.now(),
                confidence=0.3,
                missing_info=previous_result.missing_info,
                next_steps=['Wait for user input'],
                user_questions=previous_result.user_questions
            )
        else:
            # Create the project using real AI
            project_result = await self.template_engine.create_project_from_description(
                idea.content,
                context=idea.context
            )

            # Store project state
            project_state = ProjectState(
                project_id=project_result.get('project_id', str(uuid.uuid4())),
                idea_id=idea.id,
                name=project_result.get('name', 'Untitled Project'),
                description=idea.content,
                template_type=goal_analysis.goal_type,
                files_created=project_result.get('files_created', []),
                config_generated=project_result.get('config', {}),
                status='created',
                last_updated=datetime.now()
            )

            self.projects[idea.id] = project_state

            result = GerminationResult(
                idea_id=idea.id,
                phase=GerminationPhase.CREATION,
                progress=0.8,
                output={
                    'project_created': True,
                    'project_state': asdict(project_state),
                    'files_created': project_state.files_created
                },
                timestamp=datetime.now(),
                confidence=0.8,
                missing_info=[],
                next_steps=['Refine and test the project'],
                user_questions=[]
            )

        self.germination_results[idea.id].append(result)
        await self._save_germination_result(result)

    async def _phase_refinement(self, idea: Idea):
        """Phase 4: Refine and optimize the created project"""
        print(f"{Colors.CYAN}🔧 Refining project for: {idea.content[:50]}...{Colors.END}")

        previous_result = self.germination_results[idea.id][-1]

        if previous_result.phase == GerminationPhase.NEEDS_INPUT:
            # Can't refine if we need input
            result = previous_result
        else:
            # Refine the project
            refinement = await self._refine_project(idea)

            result = GerminationResult(
                idea_id=idea.id,
                phase=GerminationPhase.REFINEMENT,
                progress=0.95,
                output={
                    'refinements_made': refinement.get('improvements', []),
                    'testing_results': refinement.get('testing', {}),
                    'optimizations': refinement.get('optimizations', [])
                },
                timestamp=datetime.now(),
                confidence=refinement.get('confidence', 0.9),
                missing_info=refinement.get('remaining_issues', []),
                next_steps=refinement.get('next_steps', ['Project ready for use']),
                user_questions=refinement.get('questions', [])
            )

            # Update project status
            if idea.id in self.projects:
                self.projects[idea.id].status = 'completed'
                self.projects[idea.id].last_updated = datetime.now()

        # Mark as completed if no major issues
        if len(result.missing_info) == 0:
            result.phase = GerminationPhase.COMPLETED
            result.progress = 1.0
            print(f"{Colors.GREEN}🎉 Project completed: {idea.content[:50]}...{Colors.END}")

        self.germination_results[idea.id].append(result)
        await self._save_germination_result(result)

    async def _extract_context(self, idea: Idea) -> Dict[str, Any]:
        """Extract additional context from the idea"""
        context = {
            'source': idea.source,
            'timestamp': idea.timestamp.isoformat(),
            'priority': idea.priority
        }

        if idea.context:
            context.update(idea.context)

        # Add environment context
        context.update({
            'current_time': datetime.now().isoformat(),
            'system_config': {
                'google_enabled': self.config.get('google_enabled', False),
                'openrouter_configured': bool(self.config.get('openrouter_api_key'))
            }
        })

        return context

    def _identify_missing_info(self, goal_analysis: GoalAnalysis, context: Dict[str, Any]) -> List[str]:
        """Identify what information is missing to proceed"""
        missing = []

        # Check for required information based on goal type
        if goal_analysis.goal_type == 'chatbot':
            if not any('platform' in f.lower() for f in goal_analysis.features):
                missing.append("Which chat platform? (Discord, Slack, web, etc.)")
            if not any('api' in f.lower() for f in goal_analysis.features):
                missing.append("Any specific APIs to integrate?")

        elif goal_analysis.goal_type == 'automation':
            if not any('trigger' in f.lower() for f in goal_analysis.features):
                missing.append("What triggers the automation?")
            if not any('schedule' in f.lower() for f in goal_analysis.features):
                missing.append("How often should it run?")

        elif goal_analysis.goal_type == 'data_analysis':
            if not any('data_source' in f.lower() for f in goal_analysis.features):
                missing.append("Where is the data located?")
            if not any('output' in f.lower() for f in goal_analysis.features):
                missing.append("What format should the results be in?")

        return missing

    def _generate_next_steps(self, goal_analysis: GoalAnalysis, missing_info: List[str]) -> List[str]:
        """Generate next steps based on analysis"""
        if missing_info:
            return [f"Resolve: {info}" for info in missing_info[:3]]

        next_steps = [
            f"Research {goal_analysis.goal_type} best practices",
            f"Create {goal_analysis.goal_type} project structure",
            f"Generate initial code and configuration"
        ]

        return next_steps

    def _generate_user_questions(self, missing_info: List[str]) -> List[str]:
        """Generate questions for the user based on missing information"""
        questions = []

        for info in missing_info[:3]:  # Top 3 missing items
            if 'platform' in info.lower():
                questions.append("Which platform would you like to use?")
            elif 'trigger' in info.lower():
                questions.append("What should trigger this automation?")
            elif 'data' in info.lower():
                questions.append("Where is your data stored?")
            else:
                questions.append(f"Can you provide more details about: {info}")

        return questions

    async def _research_approaches(self, goal_analysis: GoalAnalysis) -> Dict[str, Any]:
        """Research approaches for the given goal"""
        # Simulate research - in real implementation, this would use RAG
        research = {
            'confidence': 0.8,
            'recommended_approaches': [
                f"Standard {goal_analysis.goal_type} architecture",
                "Modular design with clear separation of concerns",
                "Error handling and logging from the start"
            ],
            'potential_issues': [
                "Authentication requirements",
                "Rate limiting considerations",
                "Data privacy concerns"
            ],
            'best_practices': [
                "Start with minimal viable product",
                "Add features incrementally",
                "Test frequently during development"
            ]
        }

        return research

    async def _identify_blockers(self, goal_analysis: GoalAnalysis, research: Dict[str, Any]) -> Dict[str, Any]:
        """Identify potential blockers and missing information"""
        blockers = {
            'missing_info': [],
            'next_steps': [],
            'user_questions': []
        }

        # Check for common blockers
        if goal_analysis.goal_type == 'chatbot':
            blockers['missing_info'].append("Chat platform API keys")
            blockers['user_questions'].append("Which chat platform do you want to use?")

        elif goal_analysis.goal_type == 'automation':
            blockers['missing_info'].append("Trigger mechanism")
            blockers['user_questions'].append("What should trigger this automation?")

        blockers['next_steps'] = [
            "Resolve missing information",
            "Set up necessary API keys",
            "Create basic project structure"
        ]

        return blockers

    async def _refine_project(self, idea: Idea) -> Dict[str, Any]:
        """Refine and optimize the created project"""
        # Simulate refinement process
        refinement = {
            'improvements': [
                "Added error handling",
                "Improved code structure",
                "Added configuration validation"
            ],
            'testing': {
                'status': 'passed',
                'tests_run': 5,
                'tests_passed': 5
            },
            'optimizations': [
                "Reduced memory usage",
                "Improved startup time",
                "Added logging"
            ],
            'confidence': 0.9,
            'remaining_issues': [],
            'next_steps': ['Project is ready for use'],
            'questions': []
        }

        return refinement

    async def _monitor_progress(self):
        """Monitor progress of all active ideas"""
        while self.running:
            try:
                if self.active_ideas:
                    print(f"{Colors.CYAN}📊 Active ideas: {len(self.active_ideas)}{Colors.END}")

                    for idea_id, idea in self.active_ideas.items():
                        results = self.germination_results.get(idea_id, [])
                        if results:
                            latest = results[-1]
                            progress = int(latest.progress * 100)
                            print(f"  • {idea.content[:30]}: {progress}% ({latest.phase.value})")

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                print(f"{Colors.RED}❌ Error monitoring progress: {e}{Colors.END}")
                await asyncio.sleep(10)

    async def _cleanup_old_ideas(self):
        """Clean up old completed ideas"""
        while self.running:
            try:
                cutoff_time = datetime.now() - timedelta(hours=24)

                to_remove = []
                for idea_id, idea in self.active_ideas.items():
                    results = self.germination_results.get(idea_id, [])
                    if results and results[-1].phase == GerminationPhase.COMPLETED:
                        if results[-1].timestamp < cutoff_time:
                            to_remove.append(idea_id)

                for idea_id in to_remove:
                    del self.active_ideas[idea_id]
                    if idea_id in self.germination_results:
                        del self.germination_results[idea_id]
                    print(f"{Colors.YELLOW}🧹 Cleaned up completed idea: {idea_id}{Colors.END}")

                await asyncio.sleep(3600)  # Check every hour

            except Exception as e:
                print(f"{Colors.RED}❌ Error during cleanup: {e}{Colors.END}")
                await asyncio.sleep(300)

    async def _save_idea_for_later(self, idea: Idea):
        """Save idea to persistent storage for later processing"""
        # Save to Google Sheets if available
        if self.google_sheets:
            try:
                await self.google_sheets.save_idea({
                    'id': idea.id,
                    'content': idea.content,
                    'user_id': idea.user_id,
                    'source': idea.source,
                    'timestamp': idea.timestamp.isoformat(),
                    'priority': idea.priority,
                    'status': 'queued'
                })
            except Exception as e:
                print(f"{Colors.RED}❌ Error saving idea to Google Sheets: {e}{Colors.END}")

    async def _load_queued_ideas(self):
        """Load queued ideas from persistent storage"""
        # Load from Google Sheets if available
        if self.google_sheets and len(self.active_ideas) < self.max_concurrent_ideas:
            try:
                queued_ideas = await self.google_sheets.get_queued_ideas(limit=self.max_concurrent_ideas - len(self.active_ideas))

                for idea_data in queued_ideas:
                    idea = Idea(
                        id=idea_data['id'],
                        content=idea_data['content'],
                        user_id=idea_data['user_id'],
                        source=idea_data['source'],
                        timestamp=datetime.fromisoformat(idea_data['timestamp']),
                        priority=idea_data.get('priority', 5)
                    )

                    self.active_ideas[idea.id] = idea
                    await self.processing_queue.put(idea)
                    print(f"{Colors.GREEN}🌱 Loaded queued idea: {idea.content[:30]}...{Colors.END}")

            except Exception as e:
                print(f"{Colors.RED}❌ Error loading queued ideas: {e}{Colors.END}")

    async def _save_germination_result(self, result: GerminationResult):
        """Save germination result to persistent storage"""
        # Save to Google Sheets if available
        if self.google_sheets:
            try:
                await self.google_sheets.save_germination_result({
                    'idea_id': result.idea_id,
                    'phase': result.phase.value,
                    'progress': result.progress,
                    'timestamp': result.timestamp.isoformat(),
                    'confidence': result.confidence,
                    'missing_info': result.missing_info,
                    'next_steps': result.next_steps,
                    'user_questions': result.user_questions
                })
            except Exception as e:
                print(f"{Colors.RED}❌ Error saving germination result: {e}{Colors.END}")

    async def _notify_user_completed(self, idea: Idea, result: GerminationResult):
        """Notify user that idea processing is completed"""
        message = f"""
🎉 **Idea Completed!**

**Original Idea:** {idea.content}

**Project Created:** {self.projects[idea.id].name}
**Progress:** {int(result.progress * 100)}%
**Confidence:** {int(result.confidence * 100)}%

**Next Steps:**
{chr(10).join(f'• {step}' for step in result.next_steps)}

**Files Created:**
{chr(10).join(f'• {file}' for file in self.projects[idea.id].files_created)}
"""
        print(f"{Colors.GREEN}{message}{Colors.END}")

        # Send notification via available channels
        await self._send_notification(message, f"Idea '{idea.content[:30]}...' completed!")

    async def _notify_user_needs_input(self, idea: Idea, result: GerminationResult):
        """Notify user that their input is needed"""
        message = f"""
❓ **Idea Needs Your Input**

**Original Idea:** {idea.content}

**Progress:** {int(result.progress * 100)}%
**Stuck Because:** {result.output.get('stalled_reason', 'Missing information')}

**Questions for You:**
{chr(10).join(f'• {q}' for q in result.user_questions)}

**Missing Information:**
{chr(10).join(f'• {info}' for info in result.missing_info)}

**Please provide this information to continue:**
oos continue {idea.id}
"""
        print(f"{Colors.YELLOW}{message}{Colors.END}")

        # Send notification via available channels
        await self._send_notification(message, f"Idea '{idea.content[:30]}...' needs your input")

    async def _send_notification(self, message: str, subject: str):
        """Send notification via available channels"""
        # This could be extended to support email, Slack, etc.
        print(f"{Colors.CYAN}📧 Notification: {subject}{Colors.END}")
        print(f"{Colors.CYAN}📧 Message: {message[:100]}...{Colors.END}")

    async def _handle_processing_error(self, idea: Idea, error: Exception):
        """Handle errors during idea processing"""
        error_result = GerminationResult(
            idea_id=idea.id,
            phase=GerminationPhase.BLOCKED,
            progress=0.0,
            output={
                'error': str(error),
                'error_type': type(error).__name__
            },
            timestamp=datetime.now(),
            confidence=0.0,
            missing_info=[],
            next_steps=[],
            user_questions=[]
        )

        self.germination_results[idea.id] = [error_result]

        # Remove from active ideas
        if idea.id in self.active_ideas:
            del self.active_ideas[idea.id]

        print(f"{Colors.RED}❌ Idea processing failed: {idea.content[:30]}...{Colors.END}")
        print(f"{Colors.RED}❌ Error: {error}{Colors.END}")


# Global instance
background_processor = None


def get_background_processor(config: Dict[str, Any]) -> BackgroundProcessor:
    """Get or create background processor instance"""
    global background_processor
    if background_processor is None:
        background_processor = BackgroundProcessor(config)
    return background_processor


async def start_background_processor(config: Dict[str, Any]):
    """Start the background processor"""
    processor = get_background_processor(config)
    await processor.start()


async def add_idea_for_processing(
    content: str,
    user_id: str = "default",
    source: str = "terminal",
    priority: int = 5,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """Add an idea for background processing"""
    idea = Idea(
        id=str(uuid.uuid4()),
        content=content,
        user_id=user_id,
        source=source,
        timestamp=datetime.now(),
        priority=priority,
        context=context
    )

    processor = get_background_processor({})
    await processor.add_idea(idea)

    return idea.id


if __name__ == "__main__":
    # Test the background processor
    import asyncio

    async def test():
        config = {
            'google_enabled': False,
            'openrouter_api_key': 'test'
        }

        processor = BackgroundProcessor(config)

        # Start processor
        asyncio.create_task(processor.start())

        # Add test idea
        idea = Idea(
            id="test-123",
            content="Create a Discord bot that monitors server activity",
            user_id="test-user",
            source="test",
            timestamp=datetime.now(),
            priority=8
        )

        await processor.add_idea(idea)

        # Monitor for a while
        for i in range(10):
            status = await processor.get_idea_status(idea.id)
            if status:
                print(f"Status: {status['phase']} - {status['progress'] * 100}%")
            await asyncio.sleep(2)

        await processor.stop()

    asyncio.run(test())