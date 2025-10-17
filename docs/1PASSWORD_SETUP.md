# 🔐 1Password Setup Guide for OOS

**How to set up your 1Password vault so OOS can securely manage your API keys.**

## 🎯 What You Need

OOS expects a 1Password item called `bootstrap-env` in your `Private` vault with a field called `env` containing your environment variables.

## 📋 Step-by-Step Setup

### 1. Install 1Password CLI
```bash
# macOS
brew install --cask 1password-cli

# Ubuntu/Debian
curl -sS https://downloads.1password.com/linux/keys/1password.asc | sudo gpg --dearmor --output /usr/share/keyrings/1password-archive-keyring.gpg
echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/amd64 stable main' | sudo tee /etc/apt/sources.list.d/1password.list
sudo apt update && sudo apt install 1password-cli

# Or download from: https://developer.1password.com/docs/cli/get-started/
```

### 2. Sign In to 1Password CLI
```bash
eval $(op signin)
# Enter your 1Password password when prompted
```

### 3. Create the Environment Item

#### Option A: Using 1Password CLI (Recommended)
```bash
# Create the item with your API keys
op item create --category="Secure Note" --title="bootstrap-env" --vault="Private" \
  env="$(cat << 'EOF'
# ==== OOS bootstrap env ====
# This file contains secure environment variables for development
# Add your API keys here - they will be pulled into projects automatically

# OpenRouter (recommended - gives access to multiple AI models)
OPENROUTER_API_KEY=your_openrouter_key_here_sk-or-v1-...
OPENROUTER_API_BASE_URL=https://openrouter.ai/api/v1

# Individual AI Provider Keys (optional if using OpenRouter)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Other common API keys
GITHUB_TOKEN=your_github_token_here
GOOGLE_API_KEY=your_google_key_here

# Database URLs
DATABASE_URL=postgresql://user:pass@localhost/db

# Custom environment variables
MY_CUSTOM_VAR=some_value
EOF
)"
```

#### Option B: Using 1Password App (GUI)
1. Open 1Password app
2. Go to your "Private" vault
3. Click "+" → "Secure Note"
4. **Title**: `bootstrap-env`
5. Add a field:
   - **Label**: `env`
   - **Type**: Large text
   - **Value**: Paste your environment variables (see example below)
6. Save

### 4. Environment Variables Example

Here's what to put in the `env` field:

```bash
# ==== OOS bootstrap env ====
# This file contains secure environment variables for development

# OpenRouter (recommended - access to multiple AI models with one key)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_API_BASE_URL=https://openrouter.ai/api/v1

# You can also add multiple OpenRouter keys for failover:
# OPENROUTER_KEYS=sk-or-v1-key1,sk-or-v1-key2,sk-or-v1-key3

# Individual AI Provider Keys (if not using OpenRouter)
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Development Tools
GITHUB_TOKEN=ghp_your-github-token-here
GOOGLE_API_KEY=your-google-api-key

# Database Connections
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
REDIS_URL=redis://localhost:6379

# Custom Project Variables
APP_NAME=my-awesome-project
DEBUG_LEVEL=info
API_VERSION=v1
```

## 🔑 Getting API Keys

### OpenRouter (Recommended)
1. Go to [https://openrouter.ai/](https://openrouter.ai/)
2. Sign up/Login
3. Go to "API Keys" section
4. Create a new key
5. Copy the key (starts with `sk-or-v1-`)

**Why OpenRouter?** One key gives you access to Claude, GPT-4, Gemini, and many other models.

### Individual Providers

#### OpenAI
1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create a new secret key
3. Copy the key (starts with `sk-`)

#### Anthropic (Claude)
1. Go to [https://console.anthropic.com/](https://console.anthropic.com/)
2. Go to "API Keys" section
3. Create a new key
4. Copy the key (starts with `sk-ant-`)

#### GitHub Token
1. Go to [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`, `read:org`
4. Copy the token (starts with `ghp_`)

## 🧪 Testing Your Setup

```bash
# 1. Sign in to 1Password
eval $(op signin)

# 2. Test that OOS can read your environment
op item get bootstrap-env --vault Private --field env

# 3. Test OOS with a new project
mkdir test-oos-setup && cd test-oos-setup
oos
# Choose option 1, should work without errors!
```

## 🔄 Updating Your Environment

```bash
# Update the environment item
op item edit bootstrap-env --vault Private env="$(cat << 'EOF'
# Your updated environment variables here
OPENROUTER_API_KEY=sk-or-v1-new-key-here
# ... rest of your variables
EOF
)"
```

## 🚨 Troubleshooting

### "item bootstrap-env not found"
```bash
# Check if the item exists
op item list --vault Private | grep bootstrap

# If not found, create it (see Step 3 above)
```

### "vault Private not found"
```bash
# List your vaults
op vault list

# If you don't have a Private vault, use your existing vault:
# Update OOS to use your vault:
export OP_VAULT=Personal  # or whatever your vault is called
oos
```

### "field env not found"
The item exists but doesn't have an `env` field. Edit the item in 1Password app and add an `env` field with your environment variables.

### "no active session found"
```bash
# Sign in again
eval $(op signin)
```

## 🔒 Security Best Practices

- ✅ **Never commit API keys to git** - OOS automatically adds `.env` to `.gitignore`
- ✅ **Use different keys for different environments** - Have separate dev/staging/prod keys
- ✅ **Rotate keys regularly** - Update them in 1Password, OOS will pick up changes
- ✅ **Use minimal permissions** - Only grant API keys the permissions they need
- ✅ **Monitor usage** - Check your API provider dashboards for unusual activity

## 📝 Custom Vault/Item Names

If you want to use different names:

```bash
# Set environment variables before running OOS
export OP_VAULT=MyVault
export OP_ITEM=my-env-item
export OP_FIELD=environment

oos
```

Or edit your project's `.env` file after creation to update the defaults.

---

## ❓ Need Help?

- 📖 **1Password CLI Docs**: [https://developer.1password.com/docs/cli/](https://developer.1password.com/docs/cli/)
- 🔑 **OpenRouter**: [https://openrouter.ai/docs](https://openrouter.ai/docs)
- 🤖 **OpenAI**: [https://platform.openai.com/docs](https://platform.openai.com/docs)
- 🎯 **Anthropic**: [https://docs.anthropic.com/](https://docs.anthropic.com/)

---

**Once set up, you'll never have to worry about API keys in your code again! 🎉**