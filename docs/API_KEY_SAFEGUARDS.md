# 🔐 CRITICAL: API KEY PROTECTION SAFEGUARDS

## ⚠️  NEVER DO THESE THINGS:
1. **NEVER** add API keys to ~/.bashrc or ~/.bash_profile
2. **NEVER** export OPENROUTER_API_KEY in terminal sessions
3. **NEVER** commit .env files to git
4. **NEVER** put API keys in shell scripts
5. **NEVER** copy API keys to multiple files

## ✅ ONLY STORE API KEY HERE:
- **ONLY LOCATION**: `/home/ubuntu/dev/atlas/.env`
- **SINGLE SOURCE**: All services read from this file only

## 🛡️ PROTECTION MEASURES IN PLACE:
- **.gitignore**: Blocks all API keys from git commits
- **.env.template**: Safe template without real keys
- **Cleaned ~/.bashrc**: All OPENROUTER exports removed
- **Environment cleared**: No system env variables

## 🚨 IF API KEY GETS BURNED AGAIN:
1. Stop all services: `sudo systemctl stop atlas`
2. Clear .env: `echo "OPENROUTER_API_KEY=" > /home/ubuntu/dev/atlas/.env`
3. Check ~/.bashrc: `grep OPENROUTER ~/.bashrc` (should be empty)
4. Check environment: `env | grep OPENROUTER` (should be empty)
5. Add new key ONLY to .env file
6. Restart services

## 💡 CURRENT STATUS:
✅ API Key safely stored in .env only
✅ All other locations cleaned
✅ Git protections in place
✅ Ready for production use
