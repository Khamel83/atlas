# Enhanced Model Selector System Guide

## 🎯 Overview

The Enhanced Model Selector is a smart, cost-optimized system that automatically selects the best available model for each task, prioritizing free models while maintaining quality and performance.

## 🏗️ Architecture

### **Free-First Strategy**
- Always tries free models before paid ones
- Intelligent fallback from free → paid within each tier
- Maximizes cost savings while maintaining reliability

### **Tiered Model Selection**
- **Premium Tier**: High-quality models for complex tasks (classification, diarization)
- **Budget Tier**: Fast, cost-effective models for bulk operations (summaries, entities)
- **Fallback Tier**: Balanced models for general use

### **Smart Constraints**
- **Fast Models**: Optimized for speed-sensitive tasks
- **Quality Models**: Optimized for accuracy-critical tasks
- **Balanced Models**: Good all-around performance

## 🔧 Configuration

### **Add to your `config/.env` file:**

```bash
# Paid Model Tiers
MODEL_PREMIUM=google/gemini-2.0-flash-lite-001
MODEL_FALLBACK=google/gemini-2.0-flash-lite-001
MODEL_BUDGET=mistralai/mistral-7b-instruct

# Free Premium Models (for important/complex tasks)
MODEL_FREE_PREMIUM_1=deepseek/deepseek-r1:free
MODEL_FREE_PREMIUM_2=deepseek/deepseek-v3:free
MODEL_FREE_PREMIUM_3=meta-llama/llama-3.1-8b-instruct:free

# Free Fallback Models (balanced performance)
MODEL_FREE_FALLBACK_1=google/gemma-2-9b-it:free
MODEL_FREE_FALLBACK_2=mistralai/mistral-7b-instruct:free
MODEL_FREE_FALLBACK_3=qwen/qwen-2.5-7b-instruct:free

# Free Budget Models (for bulk/cheap tasks)
MODEL_FREE_BUDGET_1=mistralai/mistral-7b-instruct:free
MODEL_FREE_BUDGET_2=qwen/qwen-2.5-7b-instruct:free
MODEL_FREE_BUDGET_3=google/gemma-2-9b-it:free
```

## 🚀 Usage

### **Basic Usage**
```python
from helpers.model_selector import select_model

# Select best model for tier
model = select_model(tier="premium")
model = select_model(tier="budget")
model = select_model(tier="fallback")
```

### **With Constraints**
```python
# Fast model for time-sensitive tasks
model = select_model(tier="budget", require_fast=True)

# Quality model for accuracy-critical tasks
model = select_model(tier="premium", require_quality=True)
```

### **Usage Tracking**
```python
from helpers.model_selector import record_model_usage

# Record successful usage
record_model_usage("deepseek/deepseek-r1:free", tokens_used=150, success=True)

# Record failed usage
record_model_usage("some-model:free", success=False)
```

## 📊 Task Assignments

The system automatically assigns optimal models for different tasks:

| **Task Type** | **Model Tier** | **Constraints** | **Reasoning** |
|---------------|----------------|-----------------|---------------|
| **Classification** | Premium | Quality | Accuracy is crucial for categorization |
| **Speaker Diarization** | Premium | Quality | Complex task requiring high accuracy |
| **Summarization** | Budget | Fast | Bulk operation, cost-effective |
| **Entity Extraction** | Budget | Fast | Bulk operation, cost-effective |
| **General/Default** | Fallback | None | Balanced performance |

## 🔍 Features

### **1. Usage Tracking**
- Tracks requests, tokens, costs per model
- Daily and monthly usage summaries
- Success rate monitoring
- Cost analysis and savings calculations

### **2. Rate Limiting**
- Prevents API abuse
- Configurable limits per model
- Automatic rate limit detection
- Intelligent fallback when limits hit

### **3. Model Discovery**
- Automatic discovery of new free models
- Availability testing and validation
- Performance classification
- Regular cache updates

### **4. Intelligent Fallbacks**
- Free models tried first
- Graceful degradation to paid models
- Rate limit awareness
- Success rate consideration

## 📈 Monitoring & Analytics

### **Get Usage Summary**
```python
from helpers.model_selector import get_usage_summary

summary = get_usage_summary()
print(f"Today's usage: {summary['today']}")
print(f"This month: {summary['this_month']}")
print(f"Total models: {summary['total_models']}")
```

### **Model Recommendations**
```python
from helpers.model_selector import model_selector

recommendations = model_selector.get_model_recommendations()
print(f"Free usage: {recommendations['free_usage_percentage']:.1f}%")
print(f"Most used: {recommendations['most_used_models']}")
```

## 🔄 Automated Updates

### **Monthly Model Discovery**
Run this script monthly to discover new models and optimize configuration:

```bash
python3 scripts/model_discovery_updater.py
```

This will:
- Discover new free models
- Test model availability
- Generate usage reports
- Suggest configuration optimizations
- Create update scripts

### **Manual Model Discovery**
```python
from helpers.model_selector import model_selector

# Force update discovery cache
model_selector.update_model_discovery(force=True)

# Check if cache needs update
needs_update = model_selector.discovery.should_update_cache()
```

## 🎛️ Advanced Configuration

### **Custom Performance Classifications**
Edit `helpers/model_selector.py` to customize model classifications:

```python
# Fast models for time-sensitive tasks
self.fast_models = {
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free"
}

# High-quality models for accuracy-critical tasks
self.high_quality_models = {
    "deepseek/deepseek-r1:free",
    "deepseek/deepseek-v3:free",
    "meta-llama/llama-3.1-8b-instruct:free"
}
```

### **Custom Rate Limits**
```python
# Check if model is rate limited with custom limit
is_limited = model_selector.usage_tracker.is_rate_limited("model-name", limit=50)
```

## 📁 File Structure

```
helpers/
├── model_selector.py          # Main enhanced model selector
├── config.py                  # Configuration with free model support
└── ...

scripts/
├── model_discovery_updater.py # Automated model discovery
└── ...

docs/
├── ENHANCED_MODEL_SELECTOR_GUIDE.md  # This guide
└── ...

# Generated files
model_usage_tracking.json      # Usage tracking data
model_discovery_cache.json     # Model discovery cache
model_discovery_report_*.json  # Monthly reports
update_model_config_*.sh       # Auto-generated update scripts
```

## 🔧 Troubleshooting

### **Models Not Available**
- Check your OpenRouter API key
- Verify model names are correct
- Some free models may have limited availability
- Use the model discovery script to find available models

### **Rate Limiting Issues**
- Check current usage with `get_usage_summary()`
- Adjust rate limits in configuration
- The system will automatically fallback to other models

### **Poor Model Selection**
- Review model classifications in `model_selector.py`
- Update model performance categories
- Run model discovery to find better alternatives

## 🎯 Best Practices

1. **Run Monthly Updates**: Use the discovery script to find new models
2. **Monitor Usage**: Check usage summaries regularly
3. **Optimize Configuration**: Use recommendations to improve cost efficiency
4. **Test New Models**: Validate new models before adding to production
5. **Track Performance**: Monitor success rates and adjust classifications

## 🚀 Future Enhancements

The system is designed to be extensible:
- **Cost Optimization**: Automatic cost-based model selection
- **Performance Monitoring**: Real-time latency and quality metrics
- **A/B Testing**: Automated model performance comparison
- **Custom Strategies**: User-defined model selection strategies

## 📊 Expected Benefits

With proper configuration, you should see:
- **70-90% free model usage** for most workloads
- **Significant cost savings** on API calls
- **Improved reliability** through intelligent fallbacks
- **Better performance** through optimized model selection
- **Automatic adaptation** to new models and availability changes

---

*For questions or issues, check the troubleshooting section or review the implementation in `helpers/model_selector.py`*