# 🔧 Perplexity API Setup Guide

## 🎯 Get Your Free $5/Month API Credits

Since you have **Perplexity Pro**, you automatically get **$5/month in API credits**!

### Step 1: Get Your API Key

1. **Go to Perplexity API Settings**:
   ```bash
   # Open in browser:
   https://www.perplexity.ai/settings/api
   ```

2. **Generate API Key**:
   - Click "**+ Create Key**"
   - Name it: `OOS-Search-API`
   - Copy the key (starts with `pplx-`)

3. **Check Your Credits**:
   - You should see **$5.00** in credits (refreshes monthly)
   - If not there, wait 10-20 minutes after Pro subscription

### Step 2: Add to OOS Environment

```bash
# Add to your environment (1Password or .env):
export PERPLEXITY_API_KEY="pplx-your-key-here"

# Or add to .env file:
echo "PERPLEXITY_API_KEY=pplx-your-key-here" >> .env
```

### Step 3: Test Your API Access

```bash
# Test your API key works:
curl -X POST https://api.perplexity.ai/chat/completions \
  -H "Authorization: Bearer pplx-your-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sonar-small-online",
    "messages": [{"role": "user", "content": "What is Python?"}],
    "max_tokens": 100
  }'
```

## 💰 Perplexity API Pricing

### Free Credits (Your Pro Subscription):
- **$5/month** automatically added
- **Refreshes** on 1st of each month
- **No manual action needed**

### Token Costs:
```bash
Model                  Input      Output
sonar-small-online    $0.20/1M   $0.20/1M   ← Cheapest, web search
sonar-medium-online   $0.60/1M   $0.60/1M   ← Better quality
sonar-large-online    $1.00/1M   $1.00/1M   ← Highest quality
```

### Usage Estimates:
```bash
# With your $5/month credits:
sonar-small:  ~25,000 searches (very generous!)
sonar-medium: ~8,300 searches
sonar-large:  ~5,000 searches
```

## 🚀 OOS Integration

Once you add the API key, OOS will automatically:

1. **Use Perplexity for complex searches** when free alternatives don't work
2. **Track costs** against your $5/month budget
3. **Show remaining credits** in status reports
4. **Fall back to free search** if credits are low

### Search Priority (Updated):
1. **DuckDuckGo** (free, unlimited)
2. **Wikipedia** (free, unlimited)
3. **GitHub** (free, 5K/hour)
4. **Stack Overflow** (free, 10K/day)
5. **Perplexity Sonar** (your $5/month credits) ← NEW!
6. **Local knowledge** (built-in docs)

## 🛡️ Safety Features

- **Daily limit**: Max $1/day from your $5/month budget
- **Smart routing**: Only uses Perplexity for searches that need web access
- **Credit monitoring**: Shows remaining balance
- **Auto-fallback**: Switches to free search if credits run low

## 🎯 Best Practices

1. **Save for complex research**: Don't waste on simple queries
2. **Use sonar-small-online**: Cheapest option with web search
3. **Monitor credits**: Check balance weekly
4. **Combine with free search**: Let OOS decide when to use Perplexity

**Bottom line: You get ~25,000 high-quality web searches per month for FREE with your Pro subscription!** 🎉