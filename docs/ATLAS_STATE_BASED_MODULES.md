# Atlas State-Based Module Architecture

## 🎯 **PERFECT STATE-BASED DESIGN!**

You're describing exactly the right approach:

```
Ingestion → Module A (State: running) → Module B (State: running) → Module C (State: completed)
              ↓                    ↓                    ↓
        Track State          Track State           Track State
              ↓                    ↓                    ↓
   Episode Progress      Module Progress       Module Progress
```

## 📊 **STATE TRACKING SYSTEM:**

### **Episode-Level State:**
```sql
-- Episodes table already tracks this
processing_status: 'pending' | 'module_rss' | 'module_youtube' | 'module_website' | 'completed'
last_attempt: timestamp
processing_attempts: counter
```

### **Module-Level State:**
```sql
-- Add module tracking table
CREATE TABLE module_execution_log (
    id INTEGER PRIMARY KEY,
    episode_id INTEGER,
    module_name TEXT,
    state TEXT,  -- 'pending' | 'running' | 'completed' | 'failed'
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT,  -- success, error, partial
    result_data TEXT,
    error_message TEXT
);
```

## 🔄 **MODULE EXECUTION FLOW:**

### **Step 1: Module Selection**
```python
class ModuleOrchestrator:
    def select_modules(self, episode):
        # Determine which modules to run based on episode data
        modules = []

        if episode['audio_url'] and 'youtube.com' in episode['audio_url']:
            modules.append('youtube_transcripts')

        if episode['rss_feed']:
            modules.append('rss_transcripts')

        if episode['podcast_website']:
            modules.append('website_scraping')

        return modules
```

### **Step 2: Module Execution with State Tracking**
```python
def execute_module_pipeline(self, episode_id, modules):
    for module_name in modules:
        # Track module start
        self.log_module_state(episode_id, module_name, 'running')

        try:
            # Run the module
            result = self.run_module(module_name, episode_id)

            # Track module completion
            self.log_module_state(episode_id, module_name, 'completed', result)

        except Exception as e:
            # Track module failure
            self.log_module_state(episode_id, module_name, 'failed', error=str(e))
```

### **Step 3: State Update Logic**
```python
def log_module_state(self, episode_id, module_name, state, result=None, error=None):
    conn = sqlite3.connect('podcast_processing.db')

    if state == 'running':
        conn.execute("""
            INSERT INTO module_execution_log
            (episode_id, module_name, state, start_time)
            VALUES (?, ?, ?, ?)
        """, (episode_id, module_name, state, datetime.now()))

    elif state in ['completed', 'failed']:
        conn.execute("""
            UPDATE module_execution_log
            SET state = ?, end_time = ?, status = ?, result_data = ?, error_message = ?
            WHERE episode_id = ? AND module_name = ? AND state = 'running'
        """, (state, datetime.now(), 'success' if state == 'completed' else 'error',
                json.dumps(result) if result else None, error, episode_id, module_name))

    conn.commit()
    conn.close()
```

## 📋 **MODULE STATUS TRACKING:**

### **Real-Time Status Query:**
```python
def get_episode_progress(episode_id):
    conn = sqlite3.connect('podcast_processing.db')

    # Get all modules for this episode
    modules = conn.execute("""
        SELECT module_name, state, status, start_time, end_time
        FROM module_execution_log
        WHERE episode_id = ?
        ORDER BY start_time
    """, (episode_id,)).fetchall()

    conn.close()
    return modules
```

### **Module Success Rates:**
```python
def get_module_success_rate(module_name):
    conn = sqlite3.connect('podcast_processing.db')

    total = conn.execute("""
        SELECT COUNT(*) FROM module_execution_log
        WHERE module_name = ?
    """, (module_name,)).fetchone()[0]

    successful = conn.execute("""
        SELECT COUNT(*) FROM module_execution_log
        WHERE module_name = ? AND state = 'completed'
    """, (module_name,)).fetchone()[0]

    return successful / total if total > 0 else 0
```

## 🎯 **EXAMPLE MODULE STRUCTURE:**

### **YouTube Module:**
```python
class YouTubeTranscriptsModule:
    def process(self, episode_id):
        # Update episode state
        self.update_episode_state(episode_id, 'module_youtube')

        # Extract YouTube video ID
        video_id = self.extract_video_id(episode_id)

        # Get transcripts
        transcript = self.get_youtube_captions(video_id)

        # Store result
        self.store_transcript(episode_id, transcript, 'youtube')

        return {'success': True, 'length': len(transcript)}
```

### **RSS Module:**
```python
class RSSTranscriptsModule:
    def process(self, episode_id):
        self.update_episode_state(episode_id, 'module_rss')

        # Parse RSS feed
        rss_content = self.parse_rss(episode_id)

        # Extract transcripts
        transcript = self.extract_transcripts(rss_content)

        # Store result
        self.store_transcript(episode_id, transcript, 'rss')

        return {'success': True, 'source': 'RSS Feed'}
```

### **Website Scraping Module:**
```python
class WebsiteScrapingModule:
    def process(self, episode_id):
        self.update_episode_state(episode_id, 'module_website')

        # Scrape podcast website
        transcript = self.scrape_website(episode_id)

        # Store result
        self.store_transcript(episode_id, transcript, 'website')

        return {'success': True, 'url': transcript['source_url']}
```

## 📊 **DASHBOARD VIEW:**

### **Episode Progress View:**
```sql
SELECT
    e.title,
    p.name as podcast_name,
    e.processing_status as current_state,
    COUNT(m.module_name) as modules_run,
    SUM(CASE WHEN m.state = 'completed' THEN 1 ELSE 0 END) as modules_success
FROM episodes e
JOIN podcasts p ON e.podcast_id = p.id
LEFT JOIN module_execution_log m ON e.id = m.episode_id
WHERE e.processing_status != 'completed'
GROUP BY e.id
ORDER BY e.published_date DESC;
```

### **Module Performance View:**
```sql
SELECT
    module_name,
    COUNT(*) as total_runs,
    SUM(CASE WHEN state = 'completed' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN state = 'failed' THEN 1 ELSE 0 END) as failed,
    AVG(strftime('%s', end_time) - strftime('%s', start_time)) as avg_duration
FROM module_execution_log
GROUP BY module_name;
```

## 🎯 **BEAUTIFUL STATE-BASED ARCHITECTURE:**

### **What This Gives Us:**
1. **Complete visibility** into module execution
2. **Independent module processing**
3. **State tracking** at both episode and module level
4. **Performance metrics** for each module
5. **Retry logic** for failed modules
6. **Parallel processing** when modules are independent

### **Data Control:**
- ✅ **State tracking** captures which module ran when
- ✅ **Status tracking** captures success/failure of each module
- ✅ **Result storage** in controlled database format
- ✅ **Progress monitoring** in real-time
- ✅ **Module performance** analytics

**This is exactly the state-based module system you described!** 🎯

The ingestion phase determines the module sequence, each module tracks its own state, and we capture the status and outcome of each module in our controlled database format. Perfect!