#!/usr/bin/env python3
"""
Atlas Automated Content Ingestion Pipeline
Unified system for automated content collection from multiple sources
"""
import os
import sys
import json
import time
import logging
import asyncio
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add Atlas root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import our custom harvesters
from automation.youtube_history_scraper import YouTubeHistoryScraper
from automation.google_data_harvester import GoogleDataHarvester

# Import Atlas components
import requests
from helpers.config import get_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('automation.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class IngestionJob:
    """Ingestion job configuration"""
    name: str
    source_type: str
    frequency: str  # cron-like: daily, weekly, hourly
    enabled: bool = True
    last_run: Optional[str] = None
    config: Dict[str, Any] = None
    success_count: int = 0
    error_count: int = 0

@dataclass
class IngestionResult:
    """Result of an ingestion operation"""
    job_name: str
    success: bool
    items_processed: int
    duration: float
    timestamp: str
    error: Optional[str] = None
    details: Optional[Dict] = None

class AutomatedContentPipeline:
    """Unified automated content ingestion pipeline"""

    def __init__(self, config_file: str = "automation_config.json", atlas_url: str = "http://localhost:8000"):
        self.config_file = config_file
        self.atlas_url = atlas_url
        self.config = get_config()
        self.jobs: List[IngestionJob] = []
        self.results_history: List[IngestionResult] = []
        self.running = False

        # Initialize harvesters
        self.youtube_scraper = None
        self.google_harvester = None

        # Load job configuration
        self.load_job_config()

    def load_job_config(self) -> None:
        """Load job configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    self.jobs = [
                        IngestionJob(**job_data)
                        for job_data in config_data.get('jobs', [])
                    ]
                logger.info(f"Loaded {len(self.jobs)} ingestion jobs")
            except Exception as e:
                logger.error(f"Failed to load job config: {e}")
                self.create_default_config()
        else:
            self.create_default_config()

    def create_default_config(self) -> None:
        """Create default job configuration"""
        default_jobs = [
            IngestionJob(
                name="YouTube History Daily",
                source_type="youtube_history",
                frequency="daily",
                config={
                    "max_videos": 100,
                    "days_back": 1,
                    "headless": True
                }
            ),
            IngestionJob(
                name="Gmail Newsletters Daily",
                source_type="gmail_newsletters",
                frequency="daily",
                config={
                    "max_emails": 200,
                    "days_back": 1
                }
            ),
            IngestionJob(
                name="Google Drive Weekly",
                source_type="google_drive",
                frequency="weekly",
                config={
                    "max_files": 50,
                    "days_back": 7
                }
            ),
            IngestionJob(
                name="RSS Feeds Hourly",
                source_type="rss_feeds",
                frequency="hourly",
                config={
                    "feeds": [
                        "https://feeds.feedburner.com/oreilly/radar",
                        "https://rss.cnn.com/rss/edition.rss",
                        "https://feeds.a16z.com/a16z.rss"
                    ]
                }
            ),
            IngestionJob(
                name="Hacker News Weekly",
                source_type="hacker_news",
                frequency="weekly",
                config={
                    "max_stories": 50,
                    "min_score": 50
                }
            )
        ]

        self.jobs = default_jobs
        self.save_job_config()
        logger.info("Created default job configuration")

    def save_job_config(self) -> None:
        """Save job configuration to file"""
        try:
            config_data = {
                "jobs": [asdict(job) for job in self.jobs],
                "last_updated": datetime.now().isoformat()
            }

            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save job config: {e}")

    def add_job(self, job: IngestionJob) -> None:
        """Add a new ingestion job"""
        self.jobs.append(job)
        self.save_job_config()
        logger.info(f"Added job: {job.name}")

    def run_job(self, job: IngestionJob) -> IngestionResult:
        """Run a single ingestion job"""
        logger.info(f"Running job: {job.name}")
        start_time = time.time()

        try:
            if job.source_type == "youtube_history":
                return self._run_youtube_job(job, start_time)
            elif job.source_type == "gmail_newsletters":
                return self._run_gmail_job(job, start_time)
            elif job.source_type == "google_drive":
                return self._run_drive_job(job, start_time)
            elif job.source_type == "rss_feeds":
                return self._run_rss_job(job, start_time)
            elif job.source_type == "hacker_news":
                return self._run_hackernews_job(job, start_time)
            else:
                raise ValueError(f"Unknown source type: {job.source_type}")

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Job {job.name} failed: {error_msg}")

            job.error_count += 1

            return IngestionResult(
                job_name=job.name,
                success=False,
                items_processed=0,
                duration=duration,
                timestamp=datetime.now().isoformat(),
                error=error_msg
            )

    def _run_youtube_job(self, job: IngestionJob, start_time: float) -> IngestionResult:
        """Run YouTube history scraping job"""
        if not self.youtube_scraper:
            self.youtube_scraper = YouTubeHistoryScraper(
                headless=job.config.get('headless', True)
            )

        try:
            self.youtube_scraper.setup_driver()

            # Login (assumes stored session)
            if not self.youtube_scraper.login_to_google(interactive=False):
                logger.warning("YouTube scraper login failed - may need interactive login")
                return IngestionResult(
                    job_name=job.name,
                    success=False,
                    items_processed=0,
                    duration=time.time() - start_time,
                    timestamp=datetime.now().isoformat(),
                    error="Login failed"
                )

            if not self.youtube_scraper.navigate_to_youtube_history():
                raise Exception("Failed to navigate to YouTube history")

            videos = self.youtube_scraper.scrape_history_videos(
                max_videos=job.config.get('max_videos', 100),
                days_back=job.config.get('days_back', 1)
            )

            if videos:
                success = self.youtube_scraper.save_to_atlas(videos, self.atlas_url)
                if success:
                    job.success_count += len(videos)

            duration = time.time() - start_time
            job.last_run = datetime.now().isoformat()

            return IngestionResult(
                job_name=job.name,
                success=len(videos) > 0,
                items_processed=len(videos),
                duration=duration,
                timestamp=datetime.now().isoformat(),
                details={"videos_scraped": len(videos)}
            )

        finally:
            if self.youtube_scraper:
                self.youtube_scraper.close()
                self.youtube_scraper = None

    def _run_gmail_job(self, job: IngestionJob, start_time: float) -> IngestionResult:
        """Run Gmail newsletter harvesting job"""
        if not self.google_harvester:
            self.google_harvester = GoogleDataHarvester()

        if not self.google_harvester.authenticate():
            raise Exception("Google authentication failed")

        emails = self.google_harvester.get_gmail_newsletters(
            days_back=job.config.get('days_back', 1),
            max_emails=job.config.get('max_emails', 200)
        )

        if emails:
            success = self.google_harvester.save_to_atlas(emails, [], self.atlas_url)
            if success:
                job.success_count += len(emails)

        duration = time.time() - start_time
        job.last_run = datetime.now().isoformat()

        return IngestionResult(
            job_name=job.name,
            success=len(emails) > 0,
            items_processed=len(emails),
            duration=duration,
            timestamp=datetime.now().isoformat(),
            details={"emails_processed": len(emails)}
        )

    def _run_drive_job(self, job: IngestionJob, start_time: float) -> IngestionResult:
        """Run Google Drive harvesting job"""
        if not self.google_harvester:
            self.google_harvester = GoogleDataHarvester()

        if not self.google_harvester.authenticate():
            raise Exception("Google authentication failed")

        drive_files = self.google_harvester.get_drive_documents(
            days_back=job.config.get('days_back', 7),
            max_files=job.config.get('max_files', 50)
        )

        if drive_files:
            success = self.google_harvester.save_to_atlas([], drive_files, self.atlas_url)
            if success:
                job.success_count += len(drive_files)

        duration = time.time() - start_time
        job.last_run = datetime.now().isoformat()

        return IngestionResult(
            job_name=job.name,
            success=len(drive_files) > 0,
            items_processed=len(drive_files),
            duration=duration,
            timestamp=datetime.now().isoformat(),
            details={"files_processed": len(drive_files)}
        )

    def _run_rss_job(self, job: IngestionJob, start_time: float) -> IngestionResult:
        """Run RSS feed ingestion job"""
        import feedparser

        feeds = job.config.get('feeds', [])
        total_items = 0

        for feed_url in feeds:
            try:
                logger.info(f"Processing RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)

                for entry in feed.entries[:10]:  # Limit to 10 per feed
                    try:
                        content_data = {
                            "title": entry.get('title', 'No Title'),
                            "url": entry.get('link', ''),
                            "content": f"RSS Feed Article: {entry.get('title')}\n\n{entry.get('summary', '')}",
                            "source": f"rss-{feed_url}",
                            "metadata": {
                                "feed_url": feed_url,
                                "published": entry.get('published', ''),
                                "author": entry.get('author', ''),
                                "platform": "rss"
                            }
                        }

                        response = requests.post(
                            f"{self.atlas_url}/api/v1/content/save",
                            json=content_data,
                            headers={"Content-Type": "application/json"}
                        )

                        if response.status_code == 200:
                            total_items += 1

                    except Exception as e:
                        logger.debug(f"Error processing RSS entry: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error processing RSS feed {feed_url}: {e}")
                continue

        duration = time.time() - start_time
        job.last_run = datetime.now().isoformat()
        job.success_count += total_items

        return IngestionResult(
            job_name=job.name,
            success=total_items > 0,
            items_processed=total_items,
            duration=duration,
            timestamp=datetime.now().isoformat(),
            details={"feeds_processed": len(feeds), "total_articles": total_items}
        )

    def _run_hackernews_job(self, job: IngestionJob, start_time: float) -> IngestionResult:
        """Run Hacker News scraping job"""
        max_stories = job.config.get('max_stories', 50)
        min_score = job.config.get('min_score', 50)

        try:
            # Get top stories
            response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            if response.status_code != 200:
                raise Exception("Failed to fetch Hacker News stories")

            story_ids = response.json()[:max_stories]
            processed_count = 0

            for story_id in story_ids:
                try:
                    story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
                    if story_response.status_code == 200:
                        story = story_response.json()

                        # Filter by score
                        if story.get('score', 0) < min_score:
                            continue

                        # Only process stories with URLs
                        if story.get('url'):
                            content_data = {
                                "title": story.get('title', 'No Title'),
                                "url": story.get('url'),
                                "content": f"Hacker News Story: {story.get('title')}\nScore: {story.get('score')}\nComments: {story.get('descendants', 0)}\n\nDiscussion: https://news.ycombinator.com/item?id={story_id}",
                                "source": "hacker-news-automation",
                                "metadata": {
                                    "hn_id": story_id,
                                    "score": story.get('score'),
                                    "comments": story.get('descendants', 0),
                                    "author": story.get('by', ''),
                                    "platform": "hackernews"
                                }
                            }

                            atlas_response = requests.post(
                                f"{self.atlas_url}/api/v1/content/save",
                                json=content_data,
                                headers={"Content-Type": "application/json"}
                            )

                            if atlas_response.status_code == 200:
                                processed_count += 1

                except Exception as e:
                    logger.debug(f"Error processing HN story {story_id}: {e}")
                    continue

            duration = time.time() - start_time
            job.last_run = datetime.now().isoformat()
            job.success_count += processed_count

            return IngestionResult(
                job_name=job.name,
                success=processed_count > 0,
                items_processed=processed_count,
                duration=duration,
                timestamp=datetime.now().isoformat(),
                details={"stories_processed": processed_count, "min_score": min_score}
            )

        except Exception as e:
            raise Exception(f"Hacker News job failed: {e}")

    def run_all_jobs(self) -> List[IngestionResult]:
        """Run all enabled jobs"""
        logger.info("Starting automated content ingestion pipeline")
        results = []

        # Run jobs in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_job = {
                executor.submit(self.run_job, job): job
                for job in self.jobs if job.enabled
            }

            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    result = future.result()
                    results.append(result)
                    self.results_history.append(result)

                    if result.success:
                        logger.info(f"✅ {job.name}: {result.items_processed} items in {result.duration:.1f}s")
                    else:
                        logger.error(f"❌ {job.name}: {result.error}")

                except Exception as e:
                    logger.error(f"Job {job.name} failed with exception: {e}")
                    results.append(IngestionResult(
                        job_name=job.name,
                        success=False,
                        items_processed=0,
                        duration=0,
                        timestamp=datetime.now().isoformat(),
                        error=str(e)
                    ))

        # Save updated job config
        self.save_job_config()

        logger.info(f"Pipeline completed: {len([r for r in results if r.success])}/{len(results)} jobs succeeded")
        return results

    def start_scheduler(self) -> None:
        """Start the automated scheduler"""
        logger.info("Starting automated content ingestion scheduler")

        # Schedule jobs based on frequency
        for job in self.jobs:
            if not job.enabled:
                continue

            if job.frequency == "hourly":
                schedule.every().hour.do(self._run_single_job_wrapper, job)
            elif job.frequency == "daily":
                schedule.every().day.at("06:00").do(self._run_single_job_wrapper, job)
            elif job.frequency == "weekly":
                schedule.every().sunday.at("06:00").do(self._run_single_job_wrapper, job)

            logger.info(f"Scheduled {job.name} to run {job.frequency}")

        self.running = True

        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        finally:
            self.running = False

    def _run_single_job_wrapper(self, job: IngestionJob) -> None:
        """Wrapper for running single job in scheduler"""
        try:
            result = self.run_job(job)
            self.results_history.append(result)

            if result.success:
                logger.info(f"Scheduled job completed: {job.name} - {result.items_processed} items")
            else:
                logger.error(f"Scheduled job failed: {job.name} - {result.error}")

        except Exception as e:
            logger.error(f"Scheduled job error: {job.name} - {e}")

    def get_status_report(self) -> Dict[str, Any]:
        """Get pipeline status report"""
        total_success_count = sum(job.success_count for job in self.jobs)
        total_error_count = sum(job.error_count for job in self.jobs)

        recent_results = [r for r in self.results_history[-24:]]  # Last 24 runs

        return {
            "pipeline_status": "running" if self.running else "stopped",
            "total_jobs": len(self.jobs),
            "enabled_jobs": len([j for j in self.jobs if j.enabled]),
            "total_items_processed": total_success_count,
            "total_errors": total_error_count,
            "recent_runs": len(recent_results),
            "recent_success_rate": len([r for r in recent_results if r.success]) / len(recent_results) * 100 if recent_results else 0,
            "jobs": [
                {
                    "name": job.name,
                    "source_type": job.source_type,
                    "frequency": job.frequency,
                    "enabled": job.enabled,
                    "last_run": job.last_run,
                    "success_count": job.success_count,
                    "error_count": job.error_count
                }
                for job in self.jobs
            ],
            "timestamp": datetime.now().isoformat()
        }

    def stop(self) -> None:
        """Stop the pipeline"""
        self.running = False
        logger.info("Pipeline stopped")

def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Automated Content Pipeline")
    parser.add_argument('--atlas-url', default='http://localhost:8000', help='Atlas server URL')
    parser.add_argument('--config', default='automation_config.json', help='Job configuration file')
    parser.add_argument('--run-once', action='store_true', help='Run all jobs once and exit')
    parser.add_argument('--scheduler', action='store_true', help='Start continuous scheduler')
    parser.add_argument('--status', action='store_true', help='Show pipeline status')
    parser.add_argument('--job', help='Run specific job by name')

    args = parser.parse_args()

    pipeline = AutomatedContentPipeline(
        config_file=args.config,
        atlas_url=args.atlas_url
    )

    try:
        if args.status:
            # Show status
            status = pipeline.get_status_report()
            print(json.dumps(status, indent=2))

        elif args.job:
            # Run specific job
            job = next((j for j in pipeline.jobs if j.name == args.job), None)
            if job:
                result = pipeline.run_job(job)
                print(f"Job result: {result}")
            else:
                logger.error(f"Job not found: {args.job}")

        elif args.run_once:
            # Run all jobs once
            results = pipeline.run_all_jobs()
            logger.info(f"Completed: {len([r for r in results if r.success])}/{len(results)} jobs succeeded")

        elif args.scheduler:
            # Start continuous scheduler
            pipeline.start_scheduler()

        else:
            # Default: run once
            results = pipeline.run_all_jobs()
            logger.info(f"Completed: {len([r for r in results if r.success])}/{len(results)} jobs succeeded")

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        pipeline.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()