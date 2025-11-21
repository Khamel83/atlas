#!/usr/bin/env python3
"""
Auto-organization Script
Moves files to their proper locations according to Atlas organization rules
"""

import os
import shutil
import sys
from pathlib import Path

# File mappings for auto-organization
FILE_MAPPINGS = {
    # Core files → src/
    'atlas_unified.py': 'src/atlas_unified.py',
    'atlas_data_provider.py': 'src/atlas_data_provider.py',
    'atlas_orchestrator.py': 'src/atlas_orchestrator.py',

    # Module files → modules/
    'simple_email_ingester.py': 'modules/ingestion/simple_email_ingester.py',
    'simple_email_ingestion.py': 'modules/ingestion/simple_email_ingestion.py',
    'newsletter_processor.py': 'modules/ingestion/newsletter_processor.py',
    'transcript_scrapers.py': 'modules/transcript_discovery/transcript_scrapers.py',
    'transcript_fetchers.py': 'modules/transcript_discovery/transcript_fetchers.py',
    'transcript_extraction_engine.py': 'modules/content_extraction/transcript_extraction_engine.py',
    'transcript_quality.py': 'modules/content_extraction/transcript_quality.py',
    'atlas_analytics.py': 'modules/analysis/atlas_analytics.py',
    'content_insights.py': 'modules/analysis/content_insights.py',

    # Processor files → processors/
    'podcast_processor.py': 'processors/podcast_processor.py',
    'url_processor.py': 'processors/url_processor.py',
    'batch_processor.py': 'processors/batch_processor.py',
    'episode_processor.py': 'processors/episode_processor.py',
    'continuous_processor.py': 'processors/continuous_processor.py',

    # Integration files → integrations/
    'telegram_manager.py': 'integrations/telegram/telegram_manager.py',
    'telegram_alerts.py': 'integrations/telegram/telegram_alerts.py',
    'velja_integration.py': 'integrations/velja/velja_integration.py',
    'email_atlas_bridge.py': 'integrations/email/email_bridge.py',
    'webhook_email_bridge.py': 'integrations/email/webhook_bridge.py',

    # RelayQ → archive/disabled_integrations/ (DISABLED)
    'relayq_integration.py': 'archive/disabled_integrations/relayq_integration.py',
    'submit_atlas_jobs.py': 'archive/disabled_integrations/submit_atlas_jobs.py',
    'submit_batch_gh.py': 'archive/disabled_integrations/submit_batch_gh.py',
    'atlas_orchestrator.py': 'archive/disabled_integrations/atlas_orchestrator.py',

    # Scripts → scripts/
    'atlas_autostart.sh': 'scripts/start/atlas_autostart.sh',
    'start_atlas.sh': 'scripts/start/start_atlas.sh',
    'start_monitoring.sh': 'scripts/monitoring/start_monitoring.sh',
    'diagnostic_analysis.py': 'scripts/maintenance/diagnostic_analysis.py',
    'fix_system.py': 'scripts/maintenance/fix_system.py',
    'install_service.sh': 'scripts/setup/install_service.sh',
    'setup_velja_integration.command': 'scripts/setup/setup_velja_integration.command',

    # Tools → tools/
    'migrate_to_toml.py': 'tools/migration/migrate_to_toml.py',
    'universal_migration.py': 'tools/migration/universal_migration.py',
    'system_validator.py': 'tools/validation/system_validator.py',
    'simple_universal_migration.py': 'tools/migration/simple_universal_migration.py',
    'add_missing_documents.py': 'tools/maintenance/add_missing_documents.py',
    'add_missing_documents_fixed.py': 'tools/maintenance/add_missing_documents_fixed.py',
    'copy_atlas_data.py': 'tools/maintenance/copy_atlas_data.py',
    'fix_gmail_auth.py': 'tools/maintenance/fix_gmail_auth.py',
    'build_correct_queue.py': 'tools/maintenance/build_correct_queue.py',
    'build_episode_queue.py': 'tools/maintenance/build_episode_queue.py',
    'build_targeted_queue.py': 'tools/maintenance/build_targeted_queue.py',
    'build_exact_queue.py': 'tools/maintenance/build_exact_queue.py',
    'comprehensive_queue_builder.py': 'tools/maintenance/comprehensive_queue_builder.py',
    'comprehensive_test.py': 'tools/maintenance/comprehensive_test.py',
    'rebuild_proper_queue.py': 'tools/maintenance/rebuild_proper_queue.py',
    'finish_queue_rebuild.py': 'tools/maintenance/finish_queue_rebuild.py',
    'simple_backlog_migration.py': 'tools/migration/simple_backlog_migration.py',
    'backlog_migration.py': 'tools/migration/backlog_migration.py',
    'batch_csv_processor.py': 'tools/processing/batch_csv_processor.py',
    'batch_database_sync.py': 'tools/processing/batch_database_sync.py',

    # Processors → processors/
    'always_on_processor.py': 'processors/always_on_processor.py',
    'atlas_bulk_importer.py': 'processors/atlas_bulk_importer.py',
    'atlas_complete_processor.py': 'processors/atlas_complete_processor.py',
    'atlas_comprehensive_service.py': 'processors/atlas_comprehensive_service.py',
    'atlas_continuous_processor.py': 'processors/atlas_continuous_processor.py',
    'atlas_email_processor.py': 'processors/atlas_email_processor.py',
    'atlas_file_based_system.py': 'processors/atlas_file_based_system.py',
    'atlas_fresh_system.py': 'processors/atlas_fresh_system.py',
    'atlas_manager.py': 'processors/atlas_manager.py',
    'atlas_manager_fixed.py': 'processors/atlas_manager_fixed.py',
    'atlas_processor.py': 'processors/atlas_processor.py',
    'atlas_quality_rescue.py': 'processors/atlas_quality_rescue.py',
    'atlas_service_manager.py': 'processors/atlas_service_manager.py',
    'atlas_service_wrapper.py': 'processors/atlas_service_wrapper.py',
    'atlas_telegram_manager.py': 'processors/atlas_telegram_manager.py',
    'atlas_transcript_processor.py': 'processors/atlas_transcript_processor.py',
    'atlas_v2_actual_migration.py': 'processors/atlas_v2_actual_migration.py',
    'atlas_v2_migration.py': 'processors/atlas_v2_migration.py',
    'atlas_v3.py': 'processors/atlas_v3.py',
    'atlas_v3_dual_ingestion.py': 'processors/atlas_v3_dual_ingestion.py',
    'atlas_v3_gmail.py': 'processors/atlas_v3_gmail.py',
    'continuous_processor.py': 'processors/continuous_processor.py',
    'continuous_processor.sh': 'processors/continuous_processor.sh',
    'continuous_runner.py': 'processors/continuous_runner.py',
    'continuous_transcript_processor.py': 'processors/continuous_transcript_processor.py',
    'daily_processor.py': 'processors/daily_processor.py',
    'debug_tyler_cowen.py': 'processors/debug_tyler_cowen.py',
    'dedup_processor.py': 'processors/dedup_processor.py',
    'demo_atp_transcript_fix.py': 'processors/demo_atp_transcript_fix.py',
    'demo_scheduled_processing.py': 'processors/demo_scheduled_processing.py',
    'demonstrate_system.py': 'processors/demonstrate_system.py',
    'direct_transcript_processor.py': 'processors/direct_transcript_processor.py',
    'enhanced_continuous_processor.py': 'processors/enhanced_continuous_processor.py',
    'enhanced_free_processor.py': 'processors/enhanced_free_processor.py',
    'enhanced_retry_handler.py': 'processors/enhanced_retry_handler.py',
    'exhaustive_transcript_search.py': 'processors/exhaustive_transcript_search.py',
    'failed_episode_retry.py': 'processors/failed_episode_retry.py',
    'fast_counts.py': 'processors/fast_counts.py',
    'fast_transcript_processor.py': 'processors/fast_transcript_processor.py',
    'final_processor.py': 'processors/final_processor.py',
    'final_transcript_processor.py': 'processors/final_transcript_processor.py',
    'find_more_transcripts.py': 'processors/find_more_transcripts.py',
    'focused_mass_extraction.py': 'processors/focused_mass_extraction.py',
    'focused_transcript_processor.py': 'processors/focused_transcript_processor.py',
    'focused_transcript_search.py': 'processors/focused_transcript_search.py',
    'free_transcript_finder.py': 'processors/free_transcript_finder.py',
    'free_transcript_processor.py': 'processors/free_transcript_processor.py',
    'get_real_counts.py': 'processors/get_real_counts.py',
    'github_processor.py': 'processors/github_processor.py',
    'google_powered_transcript_finder.py': 'processors/google_powered_transcript_finder.py',
    'google_transcript_finder.py': 'processors/google_transcript_finder.py',
    'hard_podcast_processor.py': 'processors/hard_podcast_processor.py',
    'high_speed_ingester.py': 'processors/high_speed_ingester.py',
    'high_speed_processor.py': 'processors/high_speed_processor.py',
    'improved_extraction_patterns.py': 'processors/improved_extraction_patterns.py',
    'improved_transcript_finder.py': 'processors/improved_transcript_finder.py',
    'instant_processor.py': 'processors/instant_processor.py',
    'internet_content_processor.py': 'processors/internet_content_processor.py',
    'lazy': 'processors/lazy',
    'mass_rss_transcript_extractor.py': 'processors/mass_rss_transcript_extractor.py',
    'newsletter_processor.py': 'processors/newsletter_processor.py',
    'no_api_processor.py': 'processors/no_api_processor.py',
    'optimized_transcript_discovery.py': 'processors/optimized_transcript_discovery.py',
    'process_all_newsletters.py': 'processors/process_all_newsletters.py',
    'process_all_podcasts_comprehensive.py': 'processors/process_all_podcasts_comprehensive.py',
    'process_atp_queue.py': 'processors/process_atp_queue.py',
    'process_backlog.py': 'processors/process_backlog.py',
    'process_balanced_queue.py': 'processors/process_balanced_queue.py',
    'process_bloomberg_url.py': 'processors/process_bloomberg_url.py',
    'process_entire_queue.py': 'processors/process_entire_queue.py',
    'quality_assured_transcript_hunter.py': 'processors/quality_assured_transcript_hunter.py',
    'quick_transcript_validator.py': 'processors/quick_transcript_validator.py',
    'real_content_processor.py': 'processors/real_content_processor.py',
    'reliability_test_report.json': 'processors/reliability_test_report.json',
    'run.py': 'processors/run.py',
    'run_all_tests.py': 'processors/run_all_tests.py',
    'run_existing_transcript_system.py': 'processors/run_existing_transcript_system.py',
    'run_transcript_test.py': 'processors/run_transcript_test.py',
    'scheduler.py': 'processors/scheduler.py',
    'scheduler_youtube_integration.py': 'processors/scheduler_youtube_integration.py',
    'simple_atlas_ingest.py': 'processors/simple_atlas_ingest.py',
    'simple_email_ingester.py': 'processors/simple_email_ingester.py',
    'simple_extraction_improvements.py': 'processors/simple_extraction_improvements.py',
    'simple_free_processor.py': 'processors/simple_free_processor.py',
    'simple_gmail_test.py': 'processors/simple_gmail_test.py',
    'simple_log_processor.py': 'processors/simple_log_processor.py',
    'simple_overnight_processor.py': 'processors/simple_overnight_processor.py',
    'simple_queue_builder.py': 'processors/simple_queue_builder.py',
    'simple_retry_handler.py': 'processors/simple_retry_handler.py',
    'simple_transcript_copy.py': 'processors/simple_transcript_copy.py',
    'simple_universal_migration.py': 'processors/simple_universal_migration.py',
    'simple_url_worker.py': 'processors/simple_url_worker.py',
    'simple_working_processor.py': 'processors/simple_working_processor.py',
    'simple_youtube_integration.py': 'processors/simple_youtube_integration.py',
    'single_episode_processor.py': 'processors/single_episode_processor.py',
    'smart_processor.py': 'processors/smart_processor.py',
    'standalone_monitoring_service.py': 'processors/standalone_monitoring_service.py',
    'start_monitoring.sh': 'processors/start_monitoring.sh',
    'start_url_worker.py': 'processors/start_url_worker.py',
    'status.sh': 'processors/status.sh',
    'submit_atlas_jobs.py': 'processors/submit_atlas_jobs.py',
    'submit_batch_gh.py': 'processors/submit_batch_gh.py',
    'targeted_transcript_processor.py': 'processors/targeted_transcript_processor.py',
    'test_20_episodes.py': 'processors/test_20_episodes.py',
    'test_api.py': 'processors/test_api.py',
    'test_api_direct.py': 'processors/test_api_direct.py',
    'test_api_disabled.py': 'processors/test_api_disabled.py',
    'test_article_google_fallback.py': 'processors/test_article_google_fallback.py',
    'test_atlas_processing.py': 'processors/test_atlas_processing.py',
    'test_atlas_system.py': 'processors/test_atlas_system.py',
    'test_atp_integration.py': 'processors/test_atp_integration.py',
    'test_clean_feed.xml': 'processors/test_clean_feed.xml',
    'test_comprehensive_system.py': 'processors/test_comprehensive_system.py',
    'test_config_simple.py': 'processors/test_config_simple.py',
    'test_configuration_management.py': 'processors/test_configuration_management.py',
    'test_content_pipeline.py': 'processors/test_content_pipeline.py',
    'test_database.py': 'processors/test_database.py',
    'test_end_to_end.py': 'processors/test_end_to_end.py',
    'test_enhanced_processor.py': 'processors/test_enhanced_processor.py',
    'test_exports': 'processors/test_exports',
    'test_extensive_api.py': 'processors/test_extensive_api.py',
    'test_extensive_database.py': 'processors/test_extensive_database.py',
    'test_extensive_processor.py': 'processors/test_extensive_processor.py',
    'test_gmail_auth_vm.py': 'processors/test_gmail_auth_vm.py',
    'test_gmail_imap.py': 'processors/test_gmail_imap.py',
    'test_gmail_integration.py': 'processors/test_gmail_integration.py',
    'test_lex_fridman_extraction.py': 'processors/test_lex_fridman_extraction.py',
    'test_newsletter_processing.py': 'processors/test_newsletter_processing.py',
    'test_obscure_podcast.py': 'processors/test_obscure_podcast.py',
    'test_observability.py': 'processors/test_observability.py',
    'test_operational_tools.py': 'processors/test_operational_tools.py',
    'test_operational_tools_simple.py': 'processors/test_operational_tools_simple.py',
    'test_processor.py': 'processors/test_processor.py',
    'test_queue_builder.py': 'processors/test_queue_builder.py',
    'test_reliability.py': 'processors/test_reliability.py',
    'test_reliability_basic.py': 'processors/test_reliability_basic.py',
    'test_reliability_simple.py': 'processors/test_reliability_simple.py',
    'test_reliability_summary.py': 'processors/test_reliability_summary.py',
    'test_reliability_working.py': 'processors/test_reliability_working.py',
    'test_results_20_episodes.json': 'processors/test_results_20_episodes.json',
    'test_results_20251108_182923.json': 'processors/test_results_20251108_182923.json',
    'test_results_20251108_184513.json': 'processors/test_results_20251108_184513.json',
    'test_runner.py': 'processors/test_runner.py',
    'test_specific_url.py': 'processors/test_specific_url.py',
    'test_stress_load.py': 'processors/test_stress_load.py',
    'test_system_integration.py': 'processors/test_system_integration.py',
    'test_temp_data': 'processors/test_temp_data',
    'test_toml_migration.py': 'processors/test_toml_migration.py',
    'test_transcript_extraction.py': 'processors/test_transcript_extraction.py',
    'test_upload.csv': 'processors/test_upload.csv',
    'test_vacuum_fix.py': 'processors/test_vacuum_fix.py',
    'test_web_interface.py': 'processors/test_web_interface.py',
    'test_workflow.py': 'processors/test_workflow.py',
    'test_workflow_engine.py': 'processors/test_workflow_engine.py',
    'test_youtube_integration.py': 'processors/test_youtube_integration.py',
    'test_youtube_simple.py': 'processors/test_youtube_simple.py',
    'testing_results': 'processors/testing_results',
    'transcript_fix_summary.md': 'processors/transcript_fix_summary.md',
    'trusted_queue_processor.py': 'processors/trusted_queue_processor.py',
    'turbo_processor.py': 'processors/turbo_processor.py',
    'universal_content_demo.py': 'processors/universal_content_demo.py',
    'universal_content_discovery.py': 'processors/universal_content_discovery.py',
    'universal_url_processor.py': 'processors/universal_url_processor.py',
    'universal_url_registry.py': 'processors/universal_url_registry.py',
    'url_ingestion_summary.json': 'processors/url_ingestion_summary.json',
    'wayback_processor.py': 'processors/wayback_processor.py',
    'working_transcript_test.py': 'processors/working_transcript_test.py',
    'worker.py': 'processors/worker.py',
    'wsj_transcript_processor.py': 'processors/wsj_transcript_processor.py',
    'your_podcast_discovery.py': 'processors/your_podcast_discovery.py',
    'your_podcast_processor.py': 'processors/your_podcast_processor.py',

    # Web interface → web/
    'web_interface.py': 'web/web_interface.py',
    'api.py': 'web/api.py',
    'start_api.py': 'web/start_api.py',
    'start_web.py': 'web/start_web.py',

    # Config → config/
    'atlas_config.toml': 'config/atlas_config.toml',
    'podcast_sources.json': 'config/podcast_sources.json',
    'comprehensive_source_mapping.json': 'config/comprehensive_source_mapping.json',
    'transcript_sources_flat.csv': 'data/inputs/transcript_sources_flat.csv',
    'transcript_sources_wide.csv': 'data/inputs/transcript_sources_wide.csv',
    'locator_links_v3.csv': 'data/inputs/locator_links_v3.csv',
    'locator_links_v3.json': 'data/inputs/locator_links_v3.json',
}

# Directory-based mappings
DIRECTORY_MAPPINGS = {
    # Test files
    'test_': 'tests/',

    # Documentation (non-markdown)
    'readme': 'docs/',

    # Data files
    'podcast_results': 'data/exports/',
    'comprehensive_results': 'data/exports/',
    'production_results': 'data/exports/',
    'test_exports': 'tests/test_data/',
    'test_data': 'tests/test_data/',
    'testing_results': 'tests/test_data/',
    'validation_results': 'data/exports/',
    'transcripts': 'data/exports/',

    # System files
    'systemd': 'systemd/',
}

def move_file(source_path, target_path, dry_run=False):
    """Move a file from source to target, creating directories as needed"""
    try:
        source = Path(source_path)
        target = Path(target_path)

        if not source.exists():
            return False, f"Source file not found: {source_path}"

        # Create target directory if it doesn't exist
        target.parent.mkdir(parents=True, exist_ok=True)

        if dry_run:
            return True, f"Would move: {source_path} → {target_path}"

        # Move the file
        shutil.move(str(source), str(target))
        return True, f"Moved: {source_path} → {target_path}"

    except Exception as e:
        return False, f"Error moving {source_path}: {e}"

def auto_organize_files(dry_run=False):
    """Auto-organize files according to mappings"""
    root = Path('.')
    moved_files = []
    failed_moves = []

    for source_name, target_path in FILE_MAPPINGS.items():
        source_path = root / source_name
        if source_path.exists():
            success, message = move_file(source_path, target_path, dry_run)
            if success:
                moved_files.append(message)
            else:
                failed_moves.append(message)

    # Handle directory-based mappings
    for item in root.iterdir():
        if item.is_dir():
            dir_name = item.name.lower()
            for pattern, target_dir in DIRECTORY_MAPPINGS.items():
                if pattern in dir_name:
                    target_path = root / target_dir / item.name
                    success, message = move_file(item, target_path, dry_run)
                    if success:
                        moved_files.append(message)
                    else:
                        failed_moves.append(message)
                    break

    return moved_files, failed_moves

def move_log_files():
    """Move all log files to logs/ directory"""
    root = Path('.')
    log_files = list(root.glob('*.log'))
    moved_logs = []

    for log_file in log_files:
        target_path = root / 'logs' / log_file.name
        success, message = move_file(log_file, target_path)
        if success:
            moved_logs.append(message)

    return moved_logs

if __name__ == "__main__":
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("🔍 DRY RUN - Showing what would be moved:\n")

    # Create directories first
    os.system('python3 scripts/enforcement/check_file_organization.py create-dirs')

    # Auto-organize files
    moved, failed = auto_organize_files(dry_run)

    # Move log files
    if not dry_run:
        log_moves = move_log_files()
        moved.extend(log_moves)

    # Report results
    if moved:
        print("✅ Successfully moved:")
        for move in moved:
            print(f"  {move}")

    if failed:
        print("\n❌ Failed to move:")
        for fail in failed:
            print(f"  {fail}")

    if dry_run:
        print(f"\n📋 DRY RUN: Would move {len(moved)} files")
        print("Run without --dry-run to actually move files")
    else:
        print(f"\n📋 Moved {len(moved)} files")
        if failed:
            print(f"❌ {len(failed)} moves failed")