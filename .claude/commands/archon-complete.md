---
description: "Mark current Archon task as complete and move to next task"
argument-hint: <arguments>
allowed-tools: mcp__archon__list_tasks, mcp__archon__update_task
model: claude-3-5-sonnet-20241022
---


Mark current Archon task as complete and move to next task

Usage: `/archon-complete [task-id]`

```javascript
const args = "$ARGUMENTS".trim();

// Get currently active (doing) tasks
const doingTasks = await mcp__archon__list_tasks({
    project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID",
    filter_by: "status",
    filter_value: "doing"
});

if (!doingTasks.tasks || doingTasks.tasks.length === 0) {
    console.log("📋 No active tasks to complete");
    console.log("💡 Start a task first with /archon-task-start");
    return;
}

let taskToComplete;

if (args) {
    // Specific task ID provided
    const taskId = args;
    let fullTaskId = taskId;

    // Handle short IDs
    if (taskId.length === 8) {
        taskToComplete = doingTasks.tasks.find(t => t.id.startsWith(taskId));
        if (!taskToComplete) {
            console.log(`❌ Active task not found: ${taskId}`);
            console.log("🔍 Active tasks:");
            doingTasks.tasks.forEach(task => {
                const shortId = task.id.substring(0, 8);
                console.log(`  ${shortId} ${task.title}`);
            });
            return;
        }
        fullTaskId = taskToComplete.id;
    } else {
        taskToComplete = doingTasks.tasks.find(t => t.id === taskId);
        if (!taskToComplete) {
            console.log(`❌ Active task not found: ${taskId}`);
            return;
        }
    }

} else if (doingTasks.tasks.length === 1) {
    // Only one active task, complete it
    taskToComplete = doingTasks.tasks[0];

} else {
    // Multiple active tasks, ask user to specify
    console.log("🎯 Multiple active tasks found. Which one to complete?");
    doingTasks.tasks.forEach(task => {
        const shortId = task.id.substring(0, 8);
        const feature = task.feature ? `[${task.feature}] ` : '';
        console.log(`  ${shortId} ${feature}${task.title}`);
    });
    console.log("\n💡 Usage:");
    console.log("  /archon-complete <task-id>");
    console.log("  Example: /archon-complete 1a2b3c4d");
    return;
}

// Mark task as complete
console.log(`✅ Completing task: ${taskToComplete.title}`);

const completedTask = await mcp__archon__update_task({
    task_id: taskToComplete.id,
    status: "done"
});

console.log(`🎉 Task completed: ${completedTask.title}`);
console.log(`📋 Status: ${completedTask.status}`);

// Show task summary
if (taskToComplete.feature) {
    console.log(`🏷️ Feature: ${taskToComplete.feature}`);
}

// Get next available tasks
const todoTasks = await mcp__archon__list_tasks({
    project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID",
    filter_by: "status",
    filter_value: "todo"
});

if (todoTasks.tasks && todoTasks.tasks.length > 0) {
    console.log(`\n📋 Next available tasks:`);
    todoTasks.tasks.slice(0, 3).forEach(task => {
        const shortId = task.id.substring(0, 8);
        const feature = task.feature ? `[${task.feature}] ` : '';
        console.log(`  ${shortId} ${feature}${task.title}`);
    });

    if (todoTasks.tasks.length > 3) {
        console.log(`  ... and ${todoTasks.tasks.length - 3} more`);
    }

    console.log(`\n💡 Start next task:`);
    console.log(`  /archon-task-start <task-id>`);
} else {
    console.log(`\n🎉 All tasks completed! Great work!`);
    console.log(`💡 Create new tasks as needed:`);
    console.log(`  /archon-task-start "New Task Title"`);
}

// Check if there are still active tasks
const remainingDoingTasks = await mcp__archon__list_tasks({
    project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID",
    filter_by: "status",
    filter_value: "doing"
});

if (remainingDoingTasks.tasks && remainingDoingTasks.tasks.length > 0) {
    console.log(`\n🚀 Still working on:`);
    remainingDoingTasks.tasks.forEach(task => {
        const shortId = task.id.substring(0, 8);
        const feature = task.feature ? `[${task.feature}] ` : '';
        console.log(`  ${shortId} ${feature}${task.title}`);
    });
}

// Show project progress
const allTasks = await mcp__archon__list_tasks({
    project_id: process.env.ARCHON_PROJECT_ID || "$ARCHON_PROJECT_ID"
});

const doneTasks = allTasks.tasks.filter(t => t.status === 'done').length;
const totalTasks = allTasks.tasks.length;

if (totalTasks > 0) {
    const progress = Math.round((doneTasks / totalTasks) * 100);
    console.log(`\n📊 Project Progress: ${progress}% (${doneTasks}/${totalTasks} tasks completed)`);
}
```