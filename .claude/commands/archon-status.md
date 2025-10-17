---
description: "Show current Archon project status and active tasks"
allowed-tools: mcp__archon__get_project, mcp__archon__list_tasks
model: claude-3-5-sonnet-20241022
---


Show current Archon project status and active tasks

```javascript
// Get project details
const project = await mcp__archon__get_project({
    project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID"
});

// Get current tasks by status
const todoTasks = await mcp__archon__list_tasks({
    project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID",
    filter_by: "status",
    filter_value: "todo"
});

const doingTasks = await mcp__archon__list_tasks({
    project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID",
    filter_by: "status",
    filter_value: "doing"
});

const reviewTasks = await mcp__archon__list_tasks({
    project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID",
    filter_by: "status",
    filter_value: "review"
});

// Display status summary
console.log(`🎯 Project: ${project.title}`);
console.log(`📝 Description: ${project.description}`);
console.log(`\n📊 Task Status:`);
console.log(`  🟡 TODO: ${todoTasks.total_count} tasks`);
console.log(`  🔵 DOING: ${doingTasks.total_count} tasks`);
console.log(`  🟠 REVIEW: ${reviewTasks.total_count} tasks`);

// Show active (doing) tasks
if (doingTasks.tasks && doingTasks.tasks.length > 0) {
    console.log(`\n🚀 Currently Working On:`);
    doingTasks.tasks.forEach(task => {
        const shortId = task.id.substring(0, 8);
        const feature = task.feature ? `[${task.feature}] ` : '';
        console.log(`  ${shortId} ${feature}${task.title}`);
        console.log(`    👤 ${task.assignee}`);
    });
}

// Show next todo tasks
if (todoTasks.tasks && todoTasks.tasks.length > 0) {
    console.log(`\n📋 Next Tasks (TODO):`);
    todoTasks.tasks.slice(0, 3).forEach(task => {
        const shortId = task.id.substring(0, 8);
        const feature = task.feature ? `[${task.feature}] ` : '';
        console.log(`  ${shortId} ${feature}${task.title}`);
    });
    if (todoTasks.tasks.length > 3) {
        console.log(`  ... and ${todoTasks.tasks.length - 3} more`);
    }
}

console.log(`\n💡 Quick actions:`);
console.log(`  /archon-task-start - Start working on a task`);
console.log(`  /archon-research <query> - Search knowledge base`);
console.log(`  /archon-complete - Mark current work complete`);
```