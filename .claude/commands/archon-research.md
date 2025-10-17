---
description: "Search Archon knowledge base and code examples"
argument-hint: <arguments>
allowed-tools: mcp__archon__perform_rag_query, mcp__archon__search_code_examples, mcp__archon__list_tasks
model: claude-3-5-sonnet-20241022
---


Search Archon knowledge base and code examples

Usage: `/archon-research <search query>`

```javascript
const query = "$ARGUMENTS".trim();

if (!query) {
    console.log("🔍 Archon Research Tool");
    console.log("Search the knowledge base for relevant information and code examples.");
    console.log("\n💡 Usage:");
    console.log("  /archon-research JWT authentication");
    console.log("  /archon-research React component patterns");
    console.log("  /archon-research database optimization");
    console.log("  /archon-research API security best practices");
    return;
}

console.log(`🔍 Researching: "${query}"`);

try {
    // Search knowledge base
    console.log("\n📚 Searching knowledge base...");
    const ragResults = await mcp__archon__perform_rag_query({
        query: query,
        match_count: 5
    });

    if (ragResults.results && ragResults.results.length > 0) {
        console.log(`\n📖 Knowledge Base Results (${ragResults.results.length}):`);
        ragResults.results.forEach((result, index) => {
            console.log(`\n${index + 1}. ${result.title || 'Document'}`);
            if (result.url) {
                console.log(`   🔗 ${result.url}`);
            }
            if (result.content) {
                // Truncate content for display
                const content = result.content.length > 200
                    ? result.content.substring(0, 200) + "..."
                    : result.content;
                console.log(`   📄 ${content}`);
            }
            if (result.metadata && result.metadata.source) {
                console.log(`   📊 Source: ${result.metadata.source}`);
            }
        });
    } else {
        console.log("📖 No knowledge base results found");
    }

    // Search code examples
    console.log("\n💻 Searching code examples...");
    const codeResults = await mcp__archon__search_code_examples({
        query: query,
        match_count: 3
    });

    if (codeResults.results && codeResults.results.length > 0) {
        console.log(`\n💻 Code Examples (${codeResults.results.length}):`);
        codeResults.results.forEach((result, index) => {
            console.log(`\n${index + 1}. ${result.title || 'Code Example'}`);
            if (result.file_path) {
                console.log(`   📁 ${result.file_path}`);
            }
            if (result.function_name) {
                console.log(`   ⚡ ${result.function_name}`);
            }
            if (result.summary) {
                console.log(`   📝 ${result.summary}`);
            }
            if (result.content) {
                // Show first few lines of code
                const lines = result.content.split('\n').slice(0, 3);
                console.log(`   💻 Preview:`);
                lines.forEach(line => {
                    if (line.trim()) {
                        console.log(`      ${line}`);
                    }
                });
                if (result.content.split('\n').length > 3) {
                    console.log(`      ... (${result.content.split('\n').length - 3} more lines)`);
                }
            }
        });
    } else {
        console.log("💻 No code examples found");
    }

    // Show currently active tasks for context
    const doingTasks = await mcp__archon__list_tasks({
        project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID",
        filter_by: "status",
        filter_value: "doing"
    });

    if (doingTasks.tasks && doingTasks.tasks.length > 0) {
        console.log(`\n🎯 Active Tasks (for context):`);
        doingTasks.tasks.forEach(task => {
            const shortId = task.id.substring(0, 8);
            const feature = task.feature ? `[${task.feature}] ` : '';
            console.log(`  ${shortId} ${feature}${task.title}`);
        });
    }

    console.log(`\n💡 Next steps:`);
    console.log(`  • Review the results above`);
    console.log(`  • Apply insights to your current task`);
    console.log(`  • Use /archon-complete when task is finished`);

} catch (error) {
    console.log(`❌ Research failed: ${error.message}`);
    console.log("💡 Make sure your Archon server is running and accessible");
}
```