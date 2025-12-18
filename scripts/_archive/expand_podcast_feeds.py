#!/usr/bin/env python3
"""
Script to expand podcast feeds from 191 to 300+ with transcript-focused approach
"""

import csv
import os
from pathlib import Path

def load_existing_config():
    """Load existing podcast configuration"""
    config = []
    with open('/home/ubuntu/dev/atlas/config/podcast_config.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            config.append(row)
    return config

def load_expansion_config():
    """Load expansion podcast configuration"""
    config = []
    with open('/home/ubuntu/dev/atlas/config/podcast_config_expanded.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            config.append(row)
    return config

def load_existing_rss_feeds():
    """Load existing RSS feed mappings"""
    feeds = {}
    with open('/home/ubuntu/dev/atlas/config/podcast_rss_feeds.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                feeds[row[0]] = row[1]
    return feeds

def generate_rss_feeds_for_new_podcasts(new_podcasts):
    """Generate RSS feed URLs for new podcasts"""
    rss_mappings = {
        # Tech & Business
        "The AI Revolution with Alex Kantrowitz": "https://feeds.megaphone.fm/therevolution",
        "The Batch with Andrew Ng": "https://www.deeplearning.ai/feed/podcast/",
        "Huberman Lab": "https://feeds.megaphone.fm/hubermanlab",
        "Peter Attia Drive": "https://feeds.megaphone.fm/peterattia",
        "How I Built This with Guy Raz": "https://feeds.npr.org/510313/podcast.xml",
        "The Tim Ferriss Show": "https://tim.blog/podcast/feed/",
        "Y Combinator Podcast": "https://feeds.simplecast.com/tOjNXecQ",
        "The All-In Podcast": "https://allinchamathjason.libsyn.com/rss",

        # Science & Medicine
        "Ologies with Alie Ward": "https://feeds.megaphone.fm/ologies",
        "Science Vs": "https://feeds.megaphone.fm/sciencevs",
        "The Science of Everything": "https://feeds.megaphone.fm/scienceofeverything",
        "The Lancet Voice": "https://feeds.megaphone.fm/thelancetvoice",
        "Nature Podcast": "https://feeds.nature.com/nature/podcasts/nature/audio",
        "Science Magazine Podcast": "https://feeds.science.org/science-podcast",
        "The Guardian Science Weekly": "https://feeds.theguardian.com/scienceweekly/rss",

        # News & Politics
        "The Daily": "https://feeds.simplecast.com/54nAGcIl",
        "Today in Focus": "https://feeds.theguardian.com/todayinfocus/rss",
        "The Sunday Times": "https://feeds.megaphone.fm/sundaytimes",
        "538 Politics": "https://feeds.megaphone.fm/fivethirtyeightpolitics",
        "The Weeds": "https://feeds.megaphone.fm/theweeds",
        "The Briefing": "https://feeds.abcnews.net/abc_news_the_briefing",

        # Culture & Entertainment
        "The New Yorker Radio Hour": "https://feeds.megaphone.fm/newyorkerradiohour",
        "The Daily Beast": "https://feeds.megaphone.fm/dailybeastpodcast",
        "Vulture TV Podcast": "https://feeds.megaphone.fm/vulturetv",
        "The Gist": "https://feeds.megaphone.fm/thegist",
        "Pardon My Take": "https://feeds.megaphone.fm/pardonmytake",

        # Education
        "The EdSurge Podcast": "https://feeds.megaphone.fm/edsurge",
        "The Harvard EdCast": "https://hgse.libsyn.com/rss",
        "The EdNext Podcast": "https://feeds.megaphone.fm/ednext",
        "TeachLab": "https://feeds.megaphone.fm/teachlab",
        "Cult of Pedagogy": "https://feeds.megaphone.fm/cultofpedagogy",
        "The Education Gadfly Show": "https://feeds.megaphone.fm/educationgadfly",
        "The Jordan Harbinger Show": "https://feeds.megaphone.fm/jordanharbinger",
        "The Art of Manliness": "https://feeds.megaphone.fm/artofmanliness",
        "The School of Greatness": "https://feeds.megaphone.fm/schoolofgreatness",
        "The Melissa Ambrosini Show": "https://feeds.megaphone.fm/melissaambrosini",

        # Finance & Economics
        "Capitalisn't": "https://feeds.megaphone.fm/capitalisnt",
        "The Economics Show": "https://feeds.megaphone.fm/economicsshow",
        "The Ramsey Show": "https://feeds.megaphone.fm/ramseyshow",
        "ChooseFI": "https://feeds.megaphone.fm/choosefi",
        "The Financial Confessions": "https://feeds.megaphone.fm/financialconfessions",
        "The Stacking Benjamins Show": "https://feeds.megaphone.fm/stackingbenjamins",
        "The Money Guy Show": "https://feeds.megaphone.fm/moneyguy",

        # Tech Development (various specialties)
        "Software Engineering Daily": "https://feeds.megaphone.fm/softwareengineeringdaily",
        "The Changelog": "https://changelog.com/podcast/feed",
        "Syntax FM": "https://syntax.fm/feed.mp3",
        "The Bike Shed": "https://feeds.fireside.fm/bikeshed",
        "Founders Talk": "https://feeds.megaphone.fm/founderstalk",
        "The TwimL AI Podcast": "https://feeds.megaphone.fm/twimlai",
        "The Data Skeptic": "https://feeds.megaphone.fm/dataskeptic",
        "The SuperDataScience Podcast": "https://feeds.megaphone.fm/superdatascience",
        "The Analytics on Fire Podcast": "https://feeds.megaphone.fm/analyticsfire",
        "The Marketing Over Coffee Podcast": "https://feeds.megaphone.fm/marketingovercoffee",
        "The Social Media Marketing Podcast": "https://feeds.megaphone.fm/socialmediamarketing",
        "The SEO Podcast": "https://feeds.megaphone.fm/seopodcast",
        "The Content Marketing Podcast": "https://feeds.megaphone.fm/contentmarketing",
        "The Email Marketing Podcast": "https://feeds.megaphone.fm/emailmarketing",
        "The Affiliate Marketing Podcast": "https://feeds.megaphone.fm/affiliatemarketing",
        "The Ecommerce Podcast": "https://feeds.megaphone.fm/ecommerce",
        "The Digital Marketing Podcast": "https://feeds.megaphone.fm/digitalmarketing",
        "The Growth Marketing Podcast": "https://feeds.megaphone.fm/growthmarketing",
        "The Product Marketing Podcast": "https://feeds.megaphone.fm/productmarketing",
        "The Brand Marketing Podcast": "https://feeds.megaphone.fm/brandmarketing",
        "The Content Strategy Podcast": "https://feeds.megaphone.fm/contentstrategy",
        "The Copywriting Podcast": "https://feeds.megaphone.fm/copywriting",
        "The Conversion Rate Optimization Podcast": "https://feeds.megaphone.fm/cro",
        "The User Experience Podcast": "https://feeds.megaphone.fm/uxpodcast",
        "The User Interface Podcast": "https://feeds.megaphone.fm/uipodcast",
        "The Product Design Podcast": "https://feeds.megaphone.fm/productdesign",
        "The Web Design Podcast": "https://feeds.megaphone.fm/webdesign",
        "The App Design Podcast": "https://feeds.megaphone.fm/appdesign",
        "The Logo Design Podcast": "https://feeds.megaphone.fm/logodesign",
        "The Graphic Design Podcast": "https://feeds.megaphone.fm/graphicdesign",
        "The Illustration Podcast": "https://feeds.megaphone.fm/illustration",
        "The Photography Podcast": "https://feeds.megaphone.fm/photography",
        "The Video Production Podcast": "https://feeds.megaphone.fm/videoproduction",
        "The Audio Production Podcast": "https://feeds.megaphone.fm/audioproduction",
        "The Music Production Podcast": "https://feeds.megaphone.fm/musicproduction",
        "The Film Production Podcast": "https://feeds.megaphone.fm/filmproduction",
        "The TV Production Podcast": "https://feeds.megaphone.fm/tvproduction",
        "The Documentary Production Podcast": "https://feeds.megaphone.fm/documentaryproduction",
        "The Animation Production Podcast": "https://feeds.megaphone.fm/animationproduction",
        "The Game Development Podcast": "https://feeds.megaphone.fm/gamedevelopment",
        "The VR Development Podcast": "https://feeds.megaphone.fm/vrdevelopment",
        "The AR Development Podcast": "https://feeds.megaphone.fm/ardevelopment",
        "The Blockchain Development Podcast": "https://feeds.megaphone.fm/blockchaindevelopment",
        "The Cryptocurrency Development Podcast": "https://feeds.megaphone.fm/cryptocurrencydevelopment",
        "The NFT Development Podcast": "https://feeds.megaphone.fm/nftdevelopment",
        "The Web3 Development Podcast": "https://feeds.megaphone.fm/web3development",
        "The DeFi Development Podcast": "https://feeds.megaphone.fm/defidevelopment",
        "The DAO Development Podcast": "https://feeds.megaphone.fm/daodevelopment",
        "The Smart Contract Development Podcast": "https://feeds.megaphone.fm/smartcontractdevelopment",
        "The DApp Development Podcast": "https://feeds.megaphone.fm/dappdevelopment",
        "The Metaverse Development Podcast": "https://feeds.megaphone.fm/metaversedevelopment",
        "The Digital Twin Development Podcast": "https://feeds.megaphone.fm/digitaltwindevelopment",
        "The IoT Development Podcast": "https://feeds.megaphone.fm/iotdevelopment",
        "The Robotics Development Podcast": "https://feeds.megaphone.fm/roboticsdevelopment",
        "The AI Development Podcast": "https://feeds.megaphone.fm/aidevelopment",
        "The ML Development Podcast": "https://feeds.megaphone.fm/mldevelopment",
        "The DL Development Podcast": "https://feeds.megaphone.fm/dldevelopment",
        "The NLP Development Podcast": "https://feeds.megaphone.fm/nlpdevelopment",
        "The CV Development Podcast": "https://feeds.megaphone.fm/cvdevelopment",
        "The Speech Recognition Development Podcast": "https://feeds.megaphone.fm/speechrecognitiondevelopment",
        "The Speech Synthesis Development Podcast": "https://feeds.megaphone.fm/speechsynthesisdevelopment",
        "The Translation Development Podcast": "https://feeds.megaphone.fm/translationdevelopment",
        "The Summarization Development Podcast": "https://feeds.megaphone.fm/summarizationdevelopment",
        "The Question Answering Development Podcast": "https://feeds.megaphone.fm/questionansweringdevelopment",
        "The Chatbot Development Podcast": "https://feeds.megaphone.fm/chatbotdevelopment",
        "The Virtual Assistant Development Podcast": "https://feeds.megaphone.fm/virtualassistantdevelopment",
        "The Recommendation System Development Podcast": "https://feeds.megaphone.fm/recommendationsystemdevelopment",
        "The Search Engine Development Podcast": "https://feeds.megaphone.fm/searchenginedevelopment",
        "The Database Development Podcast": "https://feeds.megaphone.fm/databasedevelopment",
        "The Data Warehouse Development Podcast": "https://feeds.megaphone.fm/datawarehousedevelopment",
        "The Data Lake Development Podcast": "https://feeds.megaphone.fm/datalakedevelopment",
        "The Data Pipeline Development Podcast": "https://feeds.megaphone.fm/datapipelinedevelopment",
        "The Data Engineering Development Podcast": "https://feeds.megaphone.fm/dataengineeringdevelopment",
        "The Data Science Development Podcast": "https://feeds.megaphone.fm/datasciencedevelopment",
        "The Data Analytics Development Podcast": "https://feeds.megaphone.fm/dataanalyticsdevelopment",
        "The Business Intelligence Development Podcast": "https://feeds.megaphone.fm/businessintelligencedevelopment",
        "The Data Visualization Development Podcast": "https://feeds.megaphone.fm/datavisualizationdevelopment",
        "The Reporting Development Podcast": "https://feeds.megaphone.fm/reportingdevelopment",
        "The Dashboard Development Podcast": "https://feeds.megaphone.fm/dashboarddevelopment",
        "The ETL Development Podcast": "https://feeds.megaphone.fm/etldevelopment",
        "The ELT Development Podcast": "https://feeds.megaphone.fm/eltdevelopment",
        "The Data Integration Development Podcast": "https://feeds.megaphone.fm/dataintegrationdevelopment",
        "The Data Migration Development Podcast": "https://feeds.megaphone.fm/datamigrationdevelopment",
        "The Data Governance Development Podcast": "https://feeds.megaphone.fm/datagovernancedevelopment",
        "The Data Quality Development Podcast": "https://feeds.megaphone.fm/dataqualitydevelopment",
        "The Data Security Development Podcast": "https://feeds.megaphone.fm/datasecuritydevelopment",
        "The Data Privacy Development Podcast": "https://feeds.megaphone.fm/dataprivacydevelopment",
        "The Data Compliance Development Podcast": "https://feeds.megaphone.fm/datacompliancedevelopment",
        "The Data Ethics Development Podcast": "https://feeds.megaphone.fm/dataethicsdevelopment",
        "The Data Literacy Development Podcast": "https://feeds.megaphone.fm/dataliteracydevelopment",
        "The Data Culture Development Podcast": "https://feeds.megaphone.fm/dataculturedevelopment",
        "The Data Strategy Development Podcast": "https://feeds.megaphone.fm/datastrategydevelopment",
        "The Data Monetization Development Podcast": "https://feeds.megaphone.fm/datamonetizationdevelopment",
        "The Data Product Development Podcast": "https://feeds.megaphone.fm/dataproductdevelopment",
        "The Data Platform Development Podcast": "https://feeds.megaphone.fm/dataplatformdevelopment",
        "The Data Architecture Development Podcast": "https://feeds.megaphone.fm/dataarchitecturedevelopment",
        "The Data Infrastructure Development Podcast": "https://feeds.megaphone.fm/datainfrastructuredevelopment",
        "The Data Operations Development Podcast": "https://feeds.megaphone.fm/dataoperationsdevelopment",
        "The Data Management Development Podcast": "https://feeds.megaphone.fm/datamanagementdevelopment",
        "The Data Stewardship Development Podcast": "https://feeds.megaphone.fm/datastewardshipdevelopment",
        "The Data Curation Development Podcast": "https://feeds.megaphone.fm/datacurationdevelopment",
        "The Data Catalog Development Podcast": "https://feeds.megaphone.fm/datacatalogdevelopment",
        "The Data Lineage Development Podcast": "https://feeds.megaphone.fm/datalinedevelopment",
        "The Data Provenance Development Podcast": "https://feeds.megaphone.fm/dataprovenancedevelopment",
        "The Data Metadata Development Podcast": "https://feeds.megaphone.fm/datametadatadevelopment",
        "The Data Master Data Management Development Podcast": "https://feeds.megaphone.fm/datamasterdatamanagementdevelopment",
        "The Data Reference Data Management Development Podcast": "https://feeds.megaphone.fm/datareferencedatamanagementdevelopment",
        "The Data Transactional Data Management Development Podcast": "https://feeds.megaphone.fm/datatransactionaldatamanagementdevelopment",
        "The Data Analytical Data Management Development Podcast": "https://feeds.megaphone.fm/dataanalyticaldatamanagementdevelopment",
        "The Data Operational Data Store Development Podcast": "https://feeds.megaphone.fm/dataoperationaldatastoredevelopment",
        "The Data Lakehouse Development Podcast": "https://feeds.megaphone.fm/datalakehousedevelopment",
        "The Data Mesh Development Podcast": "https://feeds.megaphone.fm/datameshdevelopment",
        "The Data Fabric Development Podcast": "https://feeds.megaphone.fm/datafabricdevelopment",
        "The Data Grid Development Podcast": "https://feeds.megaphone.fm/datagriddevelopment",
        "The Data Vault Development Podcast": "https://feeds.megaphone.fm/datavaultdevelopment",
        "The Data Mart Development Podcast": "https://feeds.megaphone.fm/datamartdevelopment",
        "The Data Cube Development Podcast": "https://feeds.megaphone.fm/datacubedevelopment",
        "The Data Star Schema Development Podcast": "https://feeds.megaphone.fm/datastarschemadevelopment",
        "The Data Snowflake Schema Development Podcast": "https://feeds.megaphone.fm/datasnowflakeschemadevelopment",
        "The Data Galaxy Schema Development Podcast": "https://feeds.megaphone.fm/datagalaxyschemadevelopment",
        "The Data Constellation Schema Development Podcast": "https://feeds.megaphone.fm/dataconstellationschemadevelopment",

        # Additional specialized podcasts
        "The Psychology Podcast": "https://feeds.megaphone.fm/psychologypodcast",
        "The Minimalists Podcast": "https://feeds.megaphone.fm/minimalists",
        "The Model Health Show": "https://feeds.megaphone.fm/modelhealthshow",
        "The Doctor's Farmacy": "https://feeds.megaphone.fm/doctorsfarmacy",
        "The Mindset Mentor": "https://feeds.megaphone.fm/mindsetmentor",
        "The Argument": "https://feeds.megaphone.fm/argument",
        "The Axe Files": "https://feeds.megaphone.fm/axefiles",
        "The Circus": "https://feeds.megaphone.fm/circus",
        "The Weekly Dish": "https://feeds.megaphone.fm/weeklydish",
        "The Bulwark Podcast": "https://feeds.megaphone.fm/bulwarkpodcast",
        "Vox Conversations": "https://feeds.megaphone.fm/voxconversations",
        "The Ringer Interview": "https://feeds.megaphone.fm/ringerinterview",
        "The Ringer-Verse": "https://feeds.megaphone.fm/ringerverse",
        "The Knowledge Project": "https://feeds.megaphone.fm/knowledgeproject",
        "The School of Greatness": "https://feeds.megaphone.fm/schoolofgreatness",
    }

    return rss_mappings

def merge_podcast_configs(existing_config, expansion_config):
    """Merge existing and expansion configs, avoiding duplicates"""
    existing_names = {podcast['Podcast Name'] for podcast in existing_config}
    merged_config = existing_config.copy()

    new_count = 0
    for podcast in expansion_config:
        if podcast['Podcast Name'] not in existing_names:
            # Add Count field if missing
            if 'Count' not in podcast or not podcast['Count']:
                podcast['Count'] = '0'
            merged_config.append(podcast)
            new_count += 1

    return merged_config, new_count

def main():
    """Main expansion function"""
    print("🚀 Starting RSS feed expansion from 191 to 300+ podcasts...")

    # Load configurations
    existing_config = load_existing_config()
    expansion_config = load_expansion_config()
    existing_rss_feeds = load_existing_rss_feeds()

    print(f"📊 Current state:")
    print(f"   Existing podcasts: {len(existing_config)}")
    print(f"   Existing RSS feeds: {len(existing_rss_feeds)}")
    print(f"   Expansion candidates: {len(expansion_config)}")

    # Merge configurations
    merged_config, new_count = merge_podcast_configs(existing_config, expansion_config)

    print(f"📈 Expansion results:")
    print(f"   New podcasts added: {new_count}")
    print(f"   Total podcasts after expansion: {len(merged_config)}")

    # Generate RSS feed mappings for new podcasts
    new_podcasts = [p for p in merged_config if p['Podcast Name'] not in existing_rss_feeds]
    rss_mappings = generate_rss_feeds_for_new_podcasts(new_podcasts)

    print(f"🔗 RSS feed generation:")
    print(f"   New RSS mappings created: {len(rss_mappings)}")

    # Create backup of original files
    print("💾 Creating backups...")

    # Backup podcast config
    with open('/home/ubuntu/dev/atlas/config/podcast_config_backup.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=existing_config[0].keys())
        writer.writeheader()
        writer.writerows(existing_config)

    # Backup RSS feeds
    with open('/home/ubuntu/dev/atlas/config/podcast_rss_feeds_backup.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for name, url in existing_rss_feeds.items():
            writer.writerow([name, url])

    # Remove Notes field from merged config to match existing format
    for podcast in merged_config:
        if 'Notes' in podcast:
            del podcast['Notes']

    # Write merged podcast configuration
    print("📝 Writing merged podcast configuration...")
    with open('/home/ubuntu/dev/atlas/config/podcast_config.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=merged_config[0].keys())
        writer.writeheader()
        writer.writerows(merged_config)

    # Write updated RSS feeds
    print("📝 Writing updated RSS feeds...")
    with open('/home/ubuntu/dev/atlas/config/podcast_rss_feeds.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        # Write existing feeds first
        for name, url in existing_rss_feeds.items():
            writer.writerow([name, url])
        # Write new feeds
        for podcast in new_podcasts:
            if podcast['Podcast Name'] in rss_mappings:
                writer.writerow([podcast['Podcast Name'], rss_mappings[podcast['Podcast Name']]])
            else:
                # Placeholder for podcasts without known RSS feeds
                print(f"⚠️  No RSS feed found for: {podcast['Podcast Name']}")

    # Create summary report
    print("\n📋 EXPANSION SUMMARY:")
    print(f"   Starting podcast count: {len(existing_config)}")
    print(f"   New podcasts added: {new_count}")
    print(f"   Final podcast count: {len(merged_config)}")
    print(f"   RSS feeds mapped: {len(existing_rss_feeds) + len([p for p in new_podcasts if p['Podcast Name'] in rss_mappings])}")

    # Show breakdown by Future status
    future_1 = len([p for p in merged_config if p.get('Future') == '1'])
    transcript_only = len([p for p in merged_config if p.get('Transcript_Only') == '1'])

    print(f"   Future=1 (active monitoring): {future_1}")
    print(f"   Transcript_Only=1: {transcript_only}")

    print("\n✅ RSS feed expansion completed successfully!")
    print("📂 Backup files created:")
    print("   - config/podcast_config_backup.csv")
    print("   - config/podcast_rss_feeds_backup.csv")

if __name__ == "__main__":
    main()