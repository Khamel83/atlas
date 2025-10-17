---
description: "Start working on an Archon task or create a new one"
argument-hint: <arguments>
allowed-tools: mcp__archon__list_tasks, mcp__archon__update_task, mcp__archon__create_task
model: claude-3-5-sonnet-20241022
---


Start working on an Archon task or create a new one

Usage: `/archon-task-start [task-id]` or `/archon-task-start "New Task Title"`

```javascript
const args = "$ARGUMENTS".trim();

if (!args) {
    // Show available tasks to start
    const todoTasks = await mcp__archon__list_tasks({
        project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID",
        filter_by: "status",
        filter_value: "todo"
    });

    if (todoTasks.tasks && todoTasks.tasks.length > 0) {
        console.log("📋 Available tasks to start:");
        todoTasks.tasks.slice(0, 5).forEach(task => {
            const shortId = task.id.substring(0, 8);
            const feature = task.feature ? `[${task.feature}] ` : '';
            console.log(`  ${shortId} ${feature}${task.title}`);
        });
        console.log("\n💡 Usage:");
        console.log("  /archon-task-start <task-id>  - Start existing task");
        console.log('  /archon-task-start "New Task" - Create and start new task');
    } else {
        console.log("No TODO tasks found. Create a new task:");
        console.log('Usage: /archon-task-start "Task Title"');
    }
    return;
}

// Check if it's a task ID (8 or more characters, could be UUID)
if (args.length >= 8 && !args.includes(' ') && !args.startsWith('"')) {
    // Starting existing task
    const taskId = args;

    // Get full task ID if short ID provided
    let fullTaskId = taskId;
    if (taskId.length === 8) {
        const allTasks = await mcp__archon__list_tasks({
            project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID"
        });

        const foundTask = allTasks.tasks.find(t => t.id.startsWith(taskId));
        if (!foundTask) {
            console.log(`❌ Task not found: ${taskId}`);
            return;
        }
        fullTaskId = foundTask.id;
    }

    // Update task status to doing
    const updatedTask = await mcp__archon__update_task({
        task_id: fullTaskId,
        status: "doing"
    });

    console.log(`🚀 Started task: ${updatedTask.title}`);
    console.log(`📋 Status: ${updatedTask.status}`);
    console.log(`👤 Assignee: ${updatedTask.assignee}`);

    if (updatedTask.description) {
        console.log(`\n📄 Description:`);
        console.log(updatedTask.description);
    }

    // Show related sources if available
    if (updatedTask.sources && updatedTask.sources.length > 0) {
        console.log(`\n📚 Related sources:`);
        updatedTask.sources.forEach(source => {
            console.log(`  • ${source.url} (${source.type})`);
        });
    }

} else {
    // Creating new task
    const title = args.replace(/^["']|["']$/g, ''); // Remove quotes

    const newTask = await mcp__archon__create_task({
        project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID",
        title: title,
        description: "Task created from Claude Code slash command",
        status: "doing",
        assignee: "AI IDE Agent"
    });

    console.log(`✅ Created and started new task: ${newTask.title}`);
    console.log(`🆔 Task ID: ${newTask.id.substring(0, 8)}`);
    console.log(`📋 Status: ${newTask.status}`);
    console.log(`\n💡 You can add more details to this task using:`);
    console.log(`  /archon-research <topic> - Find relevant information`);
}

console.log(`\n🎯 Next steps:`);
console.log(`  • Work on your task`);
console.log(`  • Use /archon-research to find relevant information`);
console.log(`  • Use /archon-complete when finished`);
```