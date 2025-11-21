#!/usr/bin/env python3
"""
Velja Integration Script
Monitors Velja data and ingests URLs into Atlas
"""

import os
import json
import logging
import time
from pathlib import Path
from datetime import datetime
from url_ingestion_service import AtlasIngestionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/velja_integration.log'),
        logging.StreamHandler()
    ]
)

class VeljaIntegration:
    """Integration service for Velja URL monitoring"""

    def __init__(self):
        self.ingestion_service = AtlasIngestionService()

        # Velja typically stores data in:
        # ~/Library/Application Support/Velja/
        # ~/Library/Containers/com.sindresorhus.Velja/
        self.velja_paths = [
            Path.home() / "Library" / "Application Support" / "Velja",
            Path.home() / "Library" / "Containers" / "com.sindresorhus.Velja" / "Data" / "Library" / "Application Support" / "Velja",
        ]

        # Known Velja data files
        self.data_files = [
            "urls.json", "history.json", "bookmarks.json",
            "links.json", "capture.json"
        ]

        self.processed_urls = set()
        self.load_processed_urls()

    def load_processed_urls(self):
        """Load already processed URLs to avoid duplicates"""
        try:
            processed_file = Path("config/velja_processed_urls.txt")
            if processed_file.exists():
                with open(processed_file, 'r') as f:
                    self.processed_urls = set(line.strip() for line in f if line.strip())
                logging.info(f"Loaded {len(self.processed_urls)} processed URLs")
        except Exception as e:
            logging.error(f"Error loading processed URLs: {e}")

    def save_processed_url(self, url):
        """Save a processed URL to avoid duplicates"""
        try:
            os.makedirs("config", exist_ok=True)
            with open("config/velja_processed_urls.txt", 'a') as f:
                f.write(f"{url}\n")
            self.processed_urls.add(url)
        except Exception as e:
            logging.error(f"Error saving processed URL: {e}")

    def find_velja_data(self):
        """Find Velja data directory and files"""
        for path in self.velja_paths:
            if path.exists():
                logging.info(f"Found Velja directory: {path}")
                return path

        logging.warning("Velja directory not found. Common locations:")
        for path in self.velja_paths:
            logging.warning(f"  - {path}")

        return None

    def extract_urls_from_velja(self, velja_dir):
        """Extract URLs from Velja data files"""
        urls_found = []

        for data_file in self.data_files:
            file_path = velja_dir / data_file
            if file_path.exists():
                try:
                    urls = self._parse_velja_file(file_path)
                    urls_found.extend(urls)
                    logging.info(f"Found {len(urls)} URLs in {data_file}")
                except Exception as e:
                    logging.error(f"Error parsing {data_file}: {e}")

        return urls_found

    def _parse_velja_file(self, file_path):
        """Parse a Velja data file and extract URLs"""
        urls = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different Velja data formats
            if isinstance(data, list):
                for item in data:
                    url = self._extract_url_from_item(item)
                    if url and url not in self.processed_urls:
                        urls.append({
                            'url': url,
                            'source': 'velja',
                            'timestamp': datetime.now().isoformat(),
                            'file': file_path.name
                        })

            elif isinstance(data, dict):
                if 'urls' in data:
                    for item in data['urls']:
                        url = self._extract_url_from_item(item)
                        if url and url not in self.processed_urls:
                            urls.append({
                                'url': url,
                                'source': 'velja',
                                'timestamp': datetime.now().isoformat(),
                                'file': file_path.name
                            })
                elif 'links' in data:
                    for item in data['links']:
                        url = self._extract_url_from_item(item)
                        if url and url not in self.processed_urls:
                            urls.append({
                                'url': url,
                                'source': 'velja',
                                'timestamp': datetime.now().isoformat(),
                                'file': file_path.name
                            })
                elif 'bookmarks' in data:
                    for item in data['bookmarks']:
                        url = self._extract_url_from_item(item)
                        if url and url not in self.processed_urls:
                            urls.append({
                                'url': url,
                                'source': 'velja',
                                'timestamp': datetime.now().isoformat(),
                                'file': file_path.name
                            })
                else:
                    # Try to find URL keys in the dict
                    url = self._extract_url_from_item(data)
                    if url and url not in self.processed_urls:
                        urls.append({
                            'url': url,
                            'source': 'velja',
                            'timestamp': datetime.now().isoformat(),
                            'file': file_path.name
                        })

        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error in {file_path}: {e}")
        except Exception as e:
            logging.error(f"Error reading {file_path}: {e}")

        return urls

    def _extract_url_from_item(self, item):
        """Extract URL from a Velja data item"""
        if isinstance(item, str):
            # Item is already a URL string
            if item.startswith(('http://', 'https://')):
                return item
        elif isinstance(item, dict):
            # Item is a dictionary, look for URL keys
            for key in ['url', 'link', 'href', 'location', 'address']:
                if key in item and isinstance(item[key], str):
                    if item[key].startswith(('http://', 'https://')):
                        return item[key]

            # Check for nested URL objects
            for value in item.values():
                if isinstance(value, dict):
                    nested_url = self._extract_url_from_item(value)
                    if nested_url:
                        return nested_url

        return None

    def process_new_urls(self, urls):
        """Process new URLs found in Velja data"""
        if not urls:
            logging.info("No new URLs to process")
            return 0

        logging.info(f"Processing {len(urls)} new URLs from Velja")

        success_count = 0
        for url_data in urls:
            try:
                result = self.ingestion_service.ingest_url(
                    url_data['url'],
                    source='velja',
                    priority='normal'
                )

                if result['success']:
                    success_count += 1
                    self.save_processed_url(url_data['url'])
                    logging.info(f"✓ Ingested: {url_data['url']}")
                else:
                    logging.error(f"✗ Failed to ingest: {url_data['url']} - {result.get('error')}")

            except Exception as e:
                logging.error(f"Error processing URL {url_data['url']}: {e}")

        logging.info(f"Successfully ingested {success_count}/{len(urls)} URLs")
        return success_count

    def monitor_and_process(self, check_interval=60):
        """Continuously monitor Velja for new URLs"""
        logging.info("Starting Velja monitoring...")

        velja_dir = self.find_velja_data()
        if not velja_dir:
            logging.error("Velja directory not found. Please ensure Velja is installed.")
            return

        logging.info(f"Monitoring Velja directory: {velja_dir}")
        logging.info(f"Check interval: {check_interval} seconds")

        while True:
            try:
                # Extract URLs from Velja data
                urls = self.extract_urls_from_velja(velja_dir)

                # Process new URLs
                if urls:
                    success_count = self.process_new_urls(urls)
                    if success_count > 0:
                        logging.info(f"Processed {success_count} new URLs from Velja")

                # Wait for next check
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logging.info("Monitoring stopped by user")
                break
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(check_interval)

    def manual_import(self, velja_dir_path=None):
        """Manually import URLs from Velja directory"""
        if velja_dir_path:
            velja_dir = Path(velja_dir_path)
        else:
            velja_dir = self.find_velja_data()

        if not velja_dir:
            logging.error("Velja directory not found")
            return 0

        logging.info(f"Importing URLs from: {velja_dir}")
        urls = self.extract_urls_from_velja(velja_dir)
        success_count = self.process_new_urls(urls)

        logging.info(f"Manual import complete: {success_count}/{len(urls)} URLs processed")
        return success_count

def main():
    """CLI interface for Velja integration"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 velja_integration.py <command> [args]")
        print("Commands:")
        print("  monitor [interval] - Start monitoring Velja for new URLs")
        print("  import [path] - Manually import URLs from Velja directory")
        print("  find - Find Velja data directory")
        sys.exit(1)

    integration = VeljaIntegration()
    command = sys.argv[1]

    if command == 'monitor':
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        integration.monitor_and_process(interval)

    elif command == 'import':
        path = sys.argv[2] if len(sys.argv) > 2 else None
        integration.manual_import(path)

    elif command == 'find':
        velja_dir = integration.find_velja_data()
        if velja_dir:
            print(f"Found Velja directory: {velja_dir}")
        else:
            print("Velja directory not found")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()