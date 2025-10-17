
### Update subdirectory without integration
**Date**: 2025-09-28
**Why Bad**: Updated OOS in subdirectory but slash commands aren't available in parent project
**Better Approach**: Include post-update integration script to copy capabilities to parent


### Generate JSON without validation
**Date**: 2025-09-28
**Why Bad**: Creates invalid JSON that silently breaks integration
**Better Approach**: Always validate JSON before writing, add error checking, include testing

