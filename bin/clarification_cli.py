#!/usr/bin/env python3
"""
Clarification Workflow CLI

Interactive command-line interface for the clarification workflow system.
Provides structured workflow: input → clarification → planning → execution
"""

import sys
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarification_workflow import (
    ClarificationWorkflow, ClarificationResponse, QuestionType,
    WorkflowStage, get_clarification_workflow
)


class ClarificationCLI:
    """Command-line interface for clarification workflow"""

    def __init__(self):
        self.workflow = get_clarification_workflow()
        self.current_session = None

    async def run_interactive(self):
        """Run interactive clarification session"""
        print("🔍 OOS Clarification Workflow")
        print("=" * 50)
        print()

        # Get user input
        user_input = input("💬 What would you like me to help you with?\n> ").strip()

        if not user_input:
            print("❌ No input provided")
            return

        try:
            # Start workflow
            print("\n🔄 Processing your request...")
            session = await self.workflow.start_workflow(user_input)
            self.current_session = session

            # Display cleaned input analysis
            self._display_input_analysis(session)

            # Handle clarification questions
            if session.questions:
                await self._handle_clarification_questions(session)
            else:
                print("✅ Input is clear, proceeding to planning...")

            # Generate and display plan
            if session.stage == WorkflowStage.CONFIRMATION:
                self._display_plan(session)

                # Get execution approval
                approved = await self._get_execution_approval()

                if approved:
                    print("\n🚀 Executing plan...")
                    await self.workflow.execute_plan(session.session_id)

                    print("📝 Generating documentation...")
                    await self.workflow.generate_documentation(session.session_id)

                    print(f"✅ Workflow completed! Session: {session.session_id}")
                    self._display_completion_summary(session)
                else:
                    print("❌ Execution cancelled")
            else:
                print("❌ Could not generate execution plan")

        except Exception as e:
            print(f"❌ Error: {e}")
            return

    def _display_input_analysis(self, session):
        """Display input analysis results"""
        cleaned = session.cleaned_input

        print(f"\n📊 Input Analysis")
        print(f"   Original: {cleaned.original_text}")
        print(f"   Intent: {cleaned.extracted_intent}")
        print(f"   Confidence: {cleaned.confidence:.1%}")

        if cleaned.key_entities:
            print(f"   Entities: {', '.join(cleaned.key_entities)}")

        if cleaned.ambiguities:
            print(f"   ⚠️  Ambiguities found: {len(cleaned.ambiguities)}")

    async def _handle_clarification_questions(self, session):
        """Handle clarification questions interactively"""
        print(f"\n❓ I need clarification ({len(session.questions)} questions):")
        print()

        # Offer meta-clarification option
        print("💡 Options:")
        print("  1. Answer questions manually")
        print("  2. Generate AI-assisted response prompt (copy/paste to another AI)")
        print("  3. Input AI-assisted response")

        while True:
            choice = input("Choose option (1-3): ").strip()
            if choice in ['1', '2', '3']:
                break
            print("❌ Please enter 1, 2, or 3")

        if choice == '2':
            # Generate meta-clarification prompt
            context = {
                'original_input': session.original_input,
                'intent': session.cleaned_input.extracted_intent
            }
            prompt = await self.workflow.clarification_engine.generate_meta_clarification_prompt(
                session.questions, context
            )

            print("\n📋 Copy this prompt to another AI instance:")
            print("=" * 60)
            print(prompt)
            print("=" * 60)
            print("\nAfter getting the AI response, run this command again with option 3")
            return

        elif choice == '3':
            # Handle AI-assisted response
            print("\n📥 Paste the AI response here (end with 'END' on a new line):")
            ai_response_lines = []
            while True:
                line = input()
                if line.strip() == 'END':
                    break
                ai_response_lines.append(line)

            ai_response = '\n'.join(ai_response_lines)

            # Parse AI response
            responses = self.workflow.clarification_engine.parse_meta_clarification_response(
                ai_response, session.questions
            )

            if len(responses) != len(session.questions):
                print("⚠️  AI response didn't match all questions. Falling back to manual entry.")
                choice = '1'
            else:
                print("✅ AI responses parsed successfully!")

        if choice == '1':
            # Manual entry
            responses = await self._manual_question_entry(session)

        # Submit responses and update session
        print("🔄 Processing your responses...")
        updated_session = await self.workflow.submit_responses(session.session_id, responses)
        self.current_session = updated_session

    async def _manual_question_entry(self, session):
        """Handle manual question entry"""
        responses = []

        for i, question in enumerate(session.questions, 1):
            print(f"Question {i}/{len(session.questions)}:")
            print(f"  {question.text}")

            if question.question_type == QuestionType.CHOICE and question.options:
                print("  Options:")
                for j, option in enumerate(question.options, 1):
                    print(f"    {j}. {option}")

                while True:
                    try:
                        choice = input("  Enter your choice (number): ").strip()
                        choice_idx = int(choice) - 1

                        if 0 <= choice_idx < len(question.options):
                            answer = question.options[choice_idx]
                            break
                        else:
                            print(f"  ❌ Please enter a number between 1 and {len(question.options)}")
                    except ValueError:
                        print("  ❌ Please enter a valid number")

            elif question.question_type == QuestionType.CONFIRMATION:
                while True:
                    choice = input("  (y/n): ").strip().lower()
                    if choice in ['y', 'yes', 'true', '1']:
                        answer = "Yes"
                        break
                    elif choice in ['n', 'no', 'false', '0']:
                        answer = "No"
                        break
                    else:
                        print("  ❌ Please enter y/n")

            else:
                answer = input("  Your answer: ").strip()

            # Get additional context if needed
            additional = input("  Any additional context? (optional): ").strip()

            responses.append(ClarificationResponse(
                question_id=question.id,
                answer=answer,
                confidence=1.0,
                additional_context=additional if additional else None
            ))

            print()

        return responses

    def _display_plan(self, session):
        """Display execution plan"""
        plan = session.plan

        print(f"\n📋 Execution Plan")
        print(f"   {plan.summary}")
        print(f"   Estimated duration: {plan.estimated_duration} minutes")
        print()

        print("Steps:")
        for i, step in enumerate(plan.steps, 1):
            print(f"  {i}. {step['name']} ({step['type']})")

        if plan.required_tools:
            print(f"\nRequired tools: {', '.join(plan.required_tools)}")

        if plan.prerequisites:
            print(f"Prerequisites:")
            for prereq in plan.prerequisites:
                print(f"  - {prereq}")

        if plan.success_criteria:
            print(f"\nSuccess criteria:")
            for criterion in plan.success_criteria:
                print(f"  ✓ {criterion}")

        if plan.risks:
            print(f"\n⚠️  Potential risks:")
            for risk in plan.risks:
                print(f"  - {risk}")

        if plan.fallback_options:
            print(f"\nFallback options:")
            for fallback in plan.fallback_options:
                print(f"  - {fallback}")

    async def _get_execution_approval(self):
        """Get user approval for execution"""
        print("\n🤔 Review the plan above.")

        while True:
            choice = input("Proceed with execution? (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                approved = await self.workflow.approve_execution(self.current_session.session_id, True)
                return True
            elif choice in ['n', 'no']:
                approved = await self.workflow.approve_execution(self.current_session.session_id, False)
                return False
            else:
                print("❌ Please enter y/n")

    def _display_completion_summary(self, session):
        """Display completion summary"""
        print(f"\n📊 Workflow Summary")
        print(f"   Session ID: {session.session_id}")
        print(f"   Original request: {session.original_input}")
        print(f"   Intent: {session.cleaned_input.extracted_intent}")
        print(f"   Questions asked: {len(session.questions) if session.questions else 0}")
        print(f"   Steps completed: {len(session.plan.steps) if session.plan else 0}")
        print(f"   Duration: {session.plan.estimated_duration if session.plan else 0} minutes")

        # Show generated files
        storage_path = Path.home() / ".oos" / "workflows"
        session_file = storage_path / f"{session.session_id}.json"
        doc_file = storage_path / f"{session.session_id}_documentation.md"

        print(f"\n📁 Generated files:")
        if session_file.exists():
            print(f"   Session data: {session_file}")
        if doc_file.exists():
            print(f"   Documentation: {doc_file}")

    async def resume_session(self, session_id: str):
        """Resume existing session"""
        session = await self.workflow.load_session(session_id)

        if not session:
            print(f"❌ Session {session_id} not found")
            return

        print(f"🔄 Resuming session {session_id}")
        print(f"   Stage: {session.stage.value}")
        print(f"   Original request: {session.original_input}")

        self.current_session = session

        # Continue from current stage
        if session.stage == WorkflowStage.CLARIFICATION and session.questions:
            await self._handle_clarification_questions(session)
        elif session.stage == WorkflowStage.CONFIRMATION:
            self._display_plan(session)
            approved = await self._get_execution_approval()
            if approved:
                await self.workflow.execute_plan(session.session_id)
                await self.workflow.generate_documentation(session.session_id)
                print(f"✅ Workflow completed!")
        else:
            print(f"Session is in {session.stage.value} stage")

    def list_sessions(self):
        """List available sessions"""
        storage_path = Path.home() / ".oos" / "workflows"

        if not storage_path.exists():
            print("No sessions found")
            return

        session_files = list(storage_path.glob("session_*.json"))

        if not session_files:
            print("No sessions found")
            return

        print("📋 Available sessions:")
        for session_file in sorted(session_files):
            try:
                session_data = json.loads(session_file.read_text())
                session_id = session_data['session_id']
                stage = session_data['stage']
                original = session_data['original_input'][:50] + "..." if len(session_data['original_input']) > 50 else session_data['original_input']

                print(f"  {session_id} - {stage} - {original}")
            except Exception as e:
                print(f"  ❌ Error reading {session_file.name}: {e}")


async def main():
    """Main CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="OOS Clarification Workflow CLI")
    parser.add_argument("--resume", help="Resume session by ID")
    parser.add_argument("--list", action="store_true", help="List available sessions")

    args = parser.parse_args()

    cli = ClarificationCLI()

    if args.list:
        cli.list_sessions()
    elif args.resume:
        await cli.resume_session(args.resume)
    else:
        await cli.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())