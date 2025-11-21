#!/usr/bin/env python3
"""
Atlas Module Configuration System
High-level module orchestration where Atlas defines domains and RelayQ executes them
"""

import sqlite3
import json
from datetime import datetime
from archive.disabled_integrations.relayq_integration import AtlasRelayQIntegration

class AtlasModuleConfiguration:
    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.relayq = AtlasRelayQIntegration()

        # High-level module domains as defined in architecture
        self.module_domains = {
            "ingestion": {
                "description": "Data acquisition and standardization",
                "modules": ["rss_parser", "metadata_extractor", "episode_normalizer"],
                "priority": 1,
                "required": True
            },
            "transcript_discovery": {
                "description": "Finding and locating transcripts",
                "modules": [
                    "official_source_checker",
                    "youtube_transcript_finder",
                    "rss_transcript_extractor",
                    "website_scraper",
                    "aggregator_searcher",
                    "platform_checker"
                ],
                "priority": 2,
                "required": False
            },
            "content_extraction": {
                "description": "Extracting transcript content",
                "modules": [
                    "content_scraper",
                    "text_cleaner",
                    "format_normalizer",
                    "quality_validator"
                ],
                "priority": 3,
                "required": False
            },
            "quality_assurance": {
                "description": "Transcript quality assessment",
                "modules": [
                    "completeness_checker",
                    "coherence_scorer",
                    "source_validator",
                    "quality_classifier"
                ],
                "priority": 4,
                "required": False
            },
            "database_integration": {
                "description": "Data storage and retrieval",
                "modules": [
                    "schema_manager",
                    "index_optimizer",
                    "integrity_validator",
                    "performance_monitor"
                ],
                "priority": 5,
                "required": True
            },
            "analysis": {
                "description": "Content analysis and insights",
                "modules": [
                    "text_analyzer",
                    "topic_extractor",
                    "content_summarizer",
                    "trend_analyzer"
                ],
                "priority": 6,
                "required": False
            },
            "distribution": {
                "description": "Content delivery and export",
                "modules": [
                    "format_converter",
                    "api_manager",
                    "search_interface",
                    "backup_manager"
                ],
                "priority": 7,
                "required": False
            }
        }

        # Module execution strategies based on episode characteristics
        self.execution_strategies = {
            "standard_podcast": {
                "domains": ["ingestion", "transcript_discovery", "content_extraction", "quality_assurance", "database_integration"],
                "transcript_discovery_priority": ["official_source_checker", "rss_transcript_extractor", "website_scraper", "aggregator_searcher"]
            },
            "youtube_podcast": {
                "domains": ["ingestion", "transcript_discovery", "content_extraction", "quality_assurance", "database_integration"],
                "transcript_discovery_priority": ["youtube_transcript_finder", "official_source_checker", "aggregator_searcher"]
            },
            "premium_podcast": {
                "domains": ["ingestion", "transcript_discovery", "content_extraction", "quality_assurance", "database_integration"],
                "transcript_discovery_priority": ["official_source_checker", "website_scraper", "platform_checker", "aggregator_searcher"]
            },
            "news_podcast": {
                "domains": ["ingestion", "transcript_discovery", "content_extraction", "quality_assurance", "database_integration", "analysis"],
                "transcript_discovery_priority": ["official_source_checker", "rss_transcript_extractor", "aggregator_searcher", "website_scraper"]
            }
        }

    def determine_episode_strategy(self, episode):
        """Determine the best processing strategy for an episode"""
        podcast_name = str(episode.get('podcast_name', '')).lower()
        title = str(episode.get('title', '')).lower()
        audio_url = str(episode.get('audio_url', ''))

        # Check for YouTube content
        if 'youtube.com' in audio_url or 'youtu.be' in audio_url:
            return "youtube_podcast"

        # Check for premium content indicators
        premium_indicators = ['plus', 'premium', 'subscriber', 'exclusive', 'members only']
        if any(indicator in podcast_name or indicator in title for indicator in premium_indicators):
            return "premium_podcast"

        # Check for news content
        news_indicators = ['news', 'today', 'daily', 'briefing', 'update', 'morning', 'evening']
        if any(indicator in podcast_name for indicator in news_indicators):
            return "news_podcast"

        # Default to standard strategy
        return "standard_podcast"

    def create_module_configuration(self, episode):
        """Create module configuration for RelayQ to execute"""
        strategy = self.determine_episode_strategy(episode)
        strategy_config = self.execution_strategies[strategy]

        configuration = {
            "episode_id": episode['id'],
            "podcast_name": episode.get('podcast_name', 'Unknown'),
            "episode_title": episode.get('title', 'Unknown'),
            "strategy": strategy,
            "domains_to_execute": strategy_config["domains"],
            "module_priorities": {},
            "execution_parameters": {
                "max_processing_time": 1800,  # 30 minutes
                "retry_failed_modules": True,
                "parallel_execution": True,
                "quality_threshold": 0.6
            }
        }

        # Add module priorities for transcript discovery
        if "transcript_discovery" in strategy_config["domains"]:
            configuration["module_priorities"]["transcript_discovery"] = strategy_config["transcript_discovery_priority"]

        return configuration

    def submit_configured_episode(self, episode):
        """Submit episode to RelayQ with full module configuration"""
        # Create the configuration
        config = self.create_module_configuration(episode)

        # Prepare RelayQ job data
        job_data = {
            "episode": episode,
            "atlas_module_configuration": config,
            "execution_request": "Execute Atlas module pipeline with configuration",
            "expected_domains": config["domains_to_execute"],
            "processing_strategy": config["strategy"]
        }

        print(f"🎯 {episode.get('podcast_name', 'Unknown')}: {episode['title'][:50]}...")
        print(f"   Strategy: {config['strategy']}")
        print(f"   Domains: {', '.join(config['domains_to_execute'])}")

        # Check if already submitted
        if self.episode_already_configured(episode['id']):
            print(f"    ⏭️ Already configured and submitted")
            return {"status": "skipped", "reason": "already_configured"}

        try:
            # Submit to RelayQ with configuration
            job_result = self.relayq.create_relayq_job(job_data)

            if job_result['success']:
                self.mark_episode_configured(episode['id'], config)
                print(f"    ✅ Configured and submitted: {job_result['job_file']}")
                return {
                    "status": "submitted",
                    "job_file": job_result['job_file'],
                    "configuration": config
                }
            else:
                print(f"    ❌ Failed: {job_result['error']}")
                return {
                    "status": "failed",
                    "error": job_result['error']
                }

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    def episode_already_configured(self, episode_id):
        """Check if episode has already been configured and submitted"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT processing_status FROM episodes
            WHERE id = ? AND processing_status != 'pending'
        """, (episode_id,))
        result = cursor.fetchone()
        conn.close()

        return result is not None

    def mark_episode_configured(self, episode_id, config):
        """Mark episode as configured in database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE episodes SET
                processing_status = 'module_configured',
                last_attempt = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), episode_id))
        conn.commit()
        conn.close()

    def get_pending_episodes_for_configuration(self, limit=10):
        """Get episodes that need module configuration"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("""
            SELECT e.*, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.processing_status = 'pending'
            ORDER BY p.priority DESC, e.published_date DESC
            LIMIT ?
        """, (limit,))

        episodes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return episodes

    def run_module_configuration_batch(self, batch_size=10):
        """Run a batch of episode configurations"""
        print("🎯 ATLAS MODULE CONFIGURATION SYSTEM")
        print("=" * 50)
        print(f"📦 Configuring {batch_size} episodes for RelayQ execution")
        print(f"🧠 High-level module domains: {len(self.module_domains)}")
        print(f"📋 Execution strategies: {len(self.execution_strategies)}")
        print()

        episodes = self.get_pending_episodes_for_configuration(batch_size)

        if not episodes:
            print("✅ No episodes pending configuration")
            return

        print(f"🚀 CONFIGURING {len(episodes)} EPISODES")
        print()

        results = []
        successful = 0
        failed = 0
        skipped = 0

        for i, episode in enumerate(episodes, 1):
            print(f"[{i}/{len(episodes)}] ", end="")
            result = self.submit_configured_episode(episode)
            results.append(result)

            if result['status'] == 'submitted':
                successful += 1
            elif result['status'] in ['failed', 'error']:
                failed += 1
            elif result['status'] == 'skipped':
                skipped += 1

        print()
        print(f"📊 Configuration Results:")
        print(f"   ✅ Configured: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏭️ Skipped: {skipped}")

        # Show strategy distribution
        strategies_used = {}
        for result in results:
            if result['status'] == 'submitted':
                strategy = result['configuration']['strategy']
                strategies_used[strategy] = strategies_used.get(strategy, 0) + 1

        if strategies_used:
            print(f"📈 Strategies Used:")
            for strategy, count in strategies_used.items():
                print(f"   {strategy}: {count}")

    def export_module_configuration_schema(self):
        """Export the module configuration schema for documentation"""
        schema = {
            "module_domains": self.module_domains,
            "execution_strategies": self.execution_strategies,
            "created_at": datetime.now().isoformat(),
            "atlas_version": "1.0.0",
            "relayq_integration": "configured"
        }

        schema_file = f"atlas_module_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(schema_file, 'w') as f:
            json.dump(schema, f, indent=2)

        print(f"📄 Module schema exported: {schema_file}")
        return schema_file

if __name__ == "__main__":
    configurator = AtlasModuleConfiguration()

    # Export schema first
    configurator.export_module_configuration_schema()
    print()

    # Run configuration batch
    configurator.run_module_configuration_batch(10)