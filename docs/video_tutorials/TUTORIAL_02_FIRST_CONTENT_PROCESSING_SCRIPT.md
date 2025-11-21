# Atlas Tutorial 2: First Content Processing Script

## Introduction
Hello and welcome to the second tutorial in the Atlas series. In this video, I'll show you how to add your first content to Atlas and process it. By the end of this tutorial, you'll be able to add URLs, monitor processing progress, and view your processed content.

Before we begin, make sure you have Atlas installed and configured as shown in the previous tutorial. Let's get started!

## Section 1: Adding Content URLs
First, let's add some URLs to process. We'll create a simple text file with URLs.

[Screen recording: Terminal and text editor showing article list creation]
```bash
mkdir -p inputs
nano inputs/articles.txt
```

Let's add a few sample URLs:
```
https://example.com/article1
https://example.com/article2
https://example.com/article3
```

## Section 2: Starting the Processing Pipeline
Now let's start the content processing pipeline.

[Screen recording: Terminal showing run.py command]
```bash
python run.py --articles
```

## Section 3: Monitoring Processing Progress
Let's monitor the processing progress by checking the logs.

[Screen recording: Terminal showing log monitoring]
```bash
tail -f logs/atlas_service.log
```

We can also check the status of our services:

[Screen recording: Terminal showing status command]
```bash
python atlas_service_manager.py status
```

## Section 4: Viewing Processed Content
Once processing is complete, let's view our processed content.

[Screen recording: Terminal showing output directory]
```bash
ls output/articles/markdown/
cat output/articles/markdown/example.com_article1.md
```

## Section 5: Processing Other Content Types
Atlas can process more than just articles. Let's try processing a podcast.

[Screen recording: Terminal and text editor showing podcast list creation]
```bash
nano inputs/podcasts.opml
```

We'll create a simple OPML file with a podcast feed:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>My Podcasts</title>
  </head>
  <body>
    <outline text="Technology">
      <outline
        title="Tech Podcast"
        type="rss"
        xmlUrl="https://example.com/tech-podcast.xml" />
    </outline>
  </body>
</opml>
```

Now let's process the podcast:

[Screen recording: Terminal showing podcast processing]
```bash
python run.py --podcasts
```

## Section 6: Processing YouTube Videos
Let's also try processing a YouTube video.

[Screen recording: Terminal and text editor showing YouTube list creation]
```bash
nano inputs/youtube.txt
```

Add a YouTube video URL:
```
https://www.youtube.com/watch?v=example_video_id
```

Now let's process the YouTube video:

[Screen recording: Terminal showing YouTube processing]
```bash
python run.py --youtube
```

## Conclusion
That's it for the first content processing tutorial. You should now be able to add URLs, monitor processing progress, and view your processed content.

In the next tutorial, we'll explore the Atlas web dashboard and its cognitive features. If you found this helpful, please like and subscribe for more Atlas tutorials. Thanks for watching, and see you next time!