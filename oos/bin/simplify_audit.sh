#!/bin/bash
# Audit OOS scripts to find overcomplicated ones that can be simplified

echo "🔍 OOS Script Simplification Audit"
echo "=================================="

for script in bin/*.sh; do
    if [ -f "$script" ]; then
        total_lines=$(wc -l < "$script")

        # Count actual logic vs fluff
        comment_lines=$(grep -c "^[[:space:]]*#" "$script" || echo 0)
        empty_lines=$(grep -c "^[[:space:]]*$" "$script" || echo 0)
        color_setup=$(grep -c "RED=\|GREEN=\|BLUE=\|NC=" "$script" || echo 0)
        help_text=$(grep -c "cat.*EOF\|echo.*Usage" "$script" || echo 0)

        fluff_lines=$((comment_lines + empty_lines + color_setup + (help_text * 5)))
        logic_lines=$((total_lines - fluff_lines))

        if [ $total_lines -gt 100 ]; then
            fluff_percent=$((fluff_lines * 100 / total_lines))
            echo ""
            echo "📁 $(basename "$script"): $total_lines lines"
            echo "   Logic: ~$logic_lines lines"
            echo "   Fluff: ~$fluff_lines lines ($fluff_percent%)"

            if [ $fluff_percent -gt 60 ]; then
                echo "   🚨 HIGH FLUFF RATIO - probably overcomplicated"
            elif [ $total_lines -gt 200 ] && [ $logic_lines -lt 50 ]; then
                echo "   ⚠️  CANDIDATE FOR SIMPLIFICATION"
            fi

            # Check what it actually does
            main_functions=$(grep -c "^[[:space:]]*function\|^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*(" "$script" || echo 0)
            if [ $main_functions -gt 10 ]; then
                echo "   📊 $main_functions functions - might be doing too much"
            fi
        fi
    fi
done

echo ""
echo "🎯 SIMPLIFICATION CANDIDATES:"
echo "   Scripts >200 lines with high fluff ratio"
echo "   Scripts that should be 5-line 'if this then that' logic"
echo ""
echo "💡 Look for scripts that:"
echo "   - Have more help text than actual logic"
echo "   - Do simple file operations with complex coordination"
echo "   - Could be replaced with basic bash one-liners"