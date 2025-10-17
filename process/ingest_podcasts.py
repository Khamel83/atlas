import csv
import feedparser
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../config/podcasts_prioritized_cleaned.csv')
PROCESSED_EPISODES_LOG = os.path.join(os.path.dirname(__file__), '../logs/processed_episodes.log')

def load_podcast_config(config_file):
    podcasts = []
    with open(config_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            podcasts.append(row)
    return podcasts

def get_processed_episodes(log_file):
    processed = set()
    if os.path.exists(log_file):
        with open(log_file, mode='r', encoding='utf-8') as f:
            for line in f:
                processed.add(line.strip())
    return processed

def log_processed_episode(log_file, episode_id):
    with open(log_file, mode='a', encoding='utf-8') as f:
        f.write(f"{episode_id}\n")

def fetch_and_parse_feed(rss_url):
    try:
        feed = feedparser.parse(rss_url)
        if feed.bozo:
            logging.warning(f"Malformed feed detected for {rss_url}: {feed.bozo_exception}")
        return feed.entries
    except Exception as e:
        logging.error(f"Error fetching or parsing feed {rss_url}: {e}")
        return []

def process_episode(episode, podcast_name, transcript_only, processed_episodes_log):
    episode_id = episode.link # Using episode link as a unique ID for simplicity
    if episode_id in processed_episodes_log:
        logging.info(f"Episode '{episode.title}' from '{podcast_name}' already processed. Skipping.")
        return

    logging.info(f"Processing episode: '{episode.title}' from '{podcast_name}'")

    # Placeholder for actual processing logic (transcription, download, etc.)
    if transcript_only == '1':
        logging.info(f"  -> Initiating transcript-only processing for '{episode.title}'")
        # Call transcription service/module here
    else:
        logging.info(f"  -> Initiating full processing (download + transcript) for '{episode.title}'")
        # Call download and transcription service/module here

    log_processed_episode(PROCESSED_EPISODES_LOG, episode_id)
    logging.info(f"  -> Finished processing '{episode.title}' from '{podcast_name}'.")

def main():
    logging.info("Starting podcast ingestion process...")
    podcasts = load_podcast_config(CONFIG_FILE)
    processed_episodes = get_processed_episodes(PROCESSED_EPISODES_LOG)

    for podcast in podcasts:
        podcast_name = podcast.get('Podcast Name')
        rss_url = podcast.get('RSS_URL')
        exclude = podcast.get('Exclude')
        future = podcast.get('Future')
        transcript_only = podcast.get('Transcript_Only')
        count = podcast.get('Count') # This will be a string, convert to int if needed

        if exclude == '1':
            logging.info(f"Podcast '{podcast_name}' is marked for exclusion. Skipping.")
            continue

        if not rss_url:
            logging.warning(f"Podcast '{podcast_name}' has no RSS_URL. Skipping.")
            continue

        logging.info(f"Processing podcast: '{podcast_name}' (RSS: {rss_url})")
        entries = fetch_and_parse_feed(rss_url)

        if future == '1':
            # Process new episodes only
            # For simplicity, this example processes all new entries.
            # A more robust solution would compare pub dates with last processed date.
            for entry in entries:
                process_episode(entry, podcast_name, transcript_only, processed_episodes)
        else:
            # Process historical episodes up to 'count'
            # This logic needs refinement to handle actual historical processing
            # and avoid re-processing if 'count' changes.
            num_to_process = int(count) if count and count.isdigit() else 0
            processed_count = 0
            for entry in entries:
                if processed_count < num_to_process:
                    process_episode(entry, podcast_name, transcript_only, processed_episodes)
                    processed_count += 1
                else:
                    break
            logging.info(f"  -> Processed {processed_count} historical episodes for '{podcast_name}'.")

    logging.info("Podcast ingestion process finished.")

if __name__ == '__main__':
    main()
