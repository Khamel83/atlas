# Paywall Authentication Fix - Quick Reference

**Priority**: Medium | **Effort**: 8-12 hours | **Status**: Planned

## Problem
- NYTimes/WSJ authentication currently broken (getting ~1,400 char paywalled responses)
- 301+ premium articles failing that users have legitimate access to
- Enhanced Wayback Machine working great (40% recovery), but auth should work too

## Solution
1. **Debug current login forms** - capture real HTML, fix selectors
2. **Fix authentication flows** - dynamic selectors, proper waits, session management
3. **Graceful fallback** - if auth fails, use Enhanced Wayback Machine

## Success Criteria
- >80% auth success for NYTimes/WSJ
- Full article content (>15,000 chars) when auth works
- No crashes, graceful fallback to Enhanced Wayback
- Rate limiting maintained (3-17 sec delays)

## Implementation Tasks
1. **Debug**: Create form inspector, test selectors (2-3 hrs)
2. **Fix**: Update PaywallAuthenticatedStrategy, add session management (4-5 hrs)
3. **Test**: Comprehensive testing, production integration (2-3 hrs)

## Files
- `helpers/article_strategies.py` (fix authentication)
- `helpers/auth_debugger.py` (new debugging tool)
- `helpers/session_manager.py` (new session persistence)

## Risk Mitigation
- **Graceful fallback**: Enhanced Wayback as backup (already working)
- **Rate limiting**: Prevent account bans (already implemented)
- **Dynamic selectors**: Handle form changes automatically

*Enhances Atlas's "never lose data" principle by adding authenticated access to premium content while maintaining robust fallback strategies.*