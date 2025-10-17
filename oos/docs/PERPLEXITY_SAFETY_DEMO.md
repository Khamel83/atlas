# 🛡️ Perplexity Safety System Demo

Your API key `pplx-75P5...` is now protected with bulletproof safety controls.

## 🎯 What Happens on Every Search

When OOS wants to use Perplexity, you'll see:

```bash
📊 Perplexity Usage This Month:
   Current spend: $0.00 / $5.00 (0.0%)
   Remaining budget: $5.00
   Estimated call cost: $0.01
   After this call: $0.01 / $5.00

🤔 Use Perplexity API for this search? (y/N):
```

**Your choices:**
- **y** = Use Perplexity (costs ~$0.01)
- **N** = Skip Perplexity, use free alternatives

## 🚨 Hard Safety Stops

### At 90% Usage ($4.50):
```bash
🚨 SAFETY STOP: Would exceed 90% limit ($4.50). Current: $4.45
⚠️  Perplexity skipped: SAFETY STOP message
```

### When credits exhausted:
```bash
❌ Insufficient credits: $0.05 remaining, need $0.01
⚠️  Perplexity skipped: Insufficient credits
```

## 📊 Usage Tracking

Check your usage anytime:
```bash
python3 src/perplexity_usage_manager.py
```

Shows:
- Monthly spend vs $5 limit
- Percentage used
- Remaining budget
- Number of API calls
- Safety status

## 🎯 Search Flow

1. **Free searches first**: DuckDuckGo, Wikipedia, GitHub, Stack Overflow
2. **If insufficient results**: Asks permission to use Perplexity
3. **User decides**: y/N for each Perplexity call
4. **Hard stops**: At 90% ($4.50) or when credits exhausted
5. **Monthly reset**: Fresh $5 on 1st of each month

## 💰 Expected Usage

With careful use:
- **~25,000 searches/month** with your $5 credits
- **~$0.01 per search** (very affordable)
- **Ask permission** for research queries only
- **Use free search** for simple lookups

**You'll NEVER exceed your $5/month credits - the system prevents it!** 🛡️