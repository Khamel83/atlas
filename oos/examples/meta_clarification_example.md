# Meta-Clarification Feature Example

This demonstrates the meta-clarification feature where you can use a separate AI instance to help formulate better responses to clarification questions.

## How It Works

1. **Start Clarification Workflow**: Input your request (e.g., "optimize the code")
2. **Choose AI-Assisted Mode**: When questions appear, select option 2
3. **Copy Generated Prompt**: The system generates a structured prompt for another AI
4. **Paste to External AI**: Use ChatGPT, Claude, or any other AI to get optimal answers
5. **Input AI Response**: Return to OOS and paste the AI's response

## Example Workflow

### Step 1: User Input
```
What would you like me to help you with?
> optimize the authentication system
```

### Step 2: System Analysis
```
📊 Input Analysis
   Original: optimize the authentication system
   Intent: optimization
   Confidence: 60%
   ⚠️ Ambiguities found: 2
```

### Step 3: Clarification Options
```
❓ I need clarification (3 questions):

💡 Options:
  1. Answer questions manually
  2. Generate AI-assisted response prompt (copy/paste to another AI)
  3. Input AI-assisted response

Choose option (1-3): 2
```

### Step 4: Generated Prompt for External AI
```
📋 Copy this prompt to another AI instance:
============================================================
I'm working with a clarification system and need help formulating optimal responses to these questions.

**Context**: optimize the authentication system

**Questions to Answer**:

1. What's your primary goal?
   Options:
   1. Analyze and understand existing code
   2. Implement new functionality
   3. Fix or optimize existing code
   4. Create documentation
   5. Test or validate something

2. What type of project or technology stack are you working with?

3. What level of solution are you looking for?
   Options:
   1. Quick and simple approach
   2. Comprehensive and robust solution
   3. Balanced approach with good practices

**Please provide**:
1. Your recommended answers to each question
2. Brief reasoning for each choice
3. Any additional context that would be helpful

**Format your response as**:
Question 1: [Your answer] - [Brief reasoning]
Question 2: [Your answer] - [Brief reasoning]
Additional context: [Any relevant context or suggestions]

Focus on being clear, specific, and technically accurate. Consider what would lead to the most successful outcome.
============================================================
```

### Step 5: External AI Response Example
```
Question 1: Fix or optimize existing code - The request specifically mentions "optimize" which indicates improvement of existing functionality rather than new implementation.

Question 2: Web application with token-based authentication (likely JWT), possibly Node.js/Express or similar stack - Authentication systems are commonly found in web applications, and optimization typically involves token management, session handling, or security improvements.

Question 3: Comprehensive and robust solution - Authentication is security-critical, so any optimization should prioritize security and reliability over quick fixes.

Additional context: Consider focusing on security vulnerabilities, token refresh mechanisms, rate limiting, and secure storage. Performance optimizations should not compromise security.
```

### Step 6: Input AI Response Back to System
```
Choose option (1-3): 3

📥 Paste the AI response here (end with 'END' on a new line):
Question 1: Fix or optimize existing code - The request specifically mentions "optimize" which indicates improvement of existing functionality rather than new implementation.

Question 2: Web application with token-based authentication (likely JWT), possibly Node.js/Express or similar stack - Authentication systems are commonly found in web applications, and optimization typically involves token management, session handling, or security improvements.

Question 3: Comprehensive and robust solution - Authentication is security-critical, so any optimization should prioritize security and reliability over quick fixes.

Additional context: Consider focusing on security vulnerabilities, token refresh mechanisms, rate limiting, and secure storage. Performance optimizations should not compromise security.
END

✅ AI responses parsed successfully!
```

### Step 7: Generated Plan
```
📋 Execution Plan
   Comprehensive optimization plan with systematic approach and validation
   Estimated duration: 65 minutes

Steps:
  1. Profile current performance (analysis)
  2. Identify bottlenecks (investigation)
  3. Implement optimizations (coding)
  4. Validate improvements (testing)
  5. Comprehensive testing (testing)
  6. Performance validation (validation)
  7. Documentation review (review)

Required tools: profiler, analyzer, code_editor, benchmarker, test_suite, performance_tester, doc_reviewer

Prerequisites:
  - Access to codebase
  - Appropriate permissions
  - Development environment setup
  - Test framework availability

Success criteria:
  ✓ Measurable performance improvement
  ✓ No regression in functionality
  ✓ Optimizations are maintainable
  ✓ Comprehensive documentation provided
  ✓ Full test coverage achieved

⚠️ Potential risks:
  - Code changes may introduce bugs
  - Breaking changes to existing functionality
  - Test environment may not match production

Fallback options:
  - Break down into smaller incremental changes
  - Implement minimal viable solution first
  - Use existing solutions/libraries where possible
  - Implement feature flags for safe rollback
```

## Benefits of Meta-Clarification

1. **Better Context Understanding**: External AI can provide broader perspective
2. **More Structured Responses**: AI formulates clearer, more complete answers
3. **Technical Accuracy**: AI can suggest technically sound approaches
4. **Time Efficiency**: Faster than manually thinking through each question
5. **Consistency**: AI responses tend to be more structured and comprehensive

## Integration Points

- **Automatic Mode**: Could integrate with API calls to external AI services
- **Template Library**: Build library of successful meta-clarification patterns
- **Learning Integration**: Feed successful AI responses back into learning system
- **Multi-AI Support**: Support different AI services for different types of questions

## Usage Tips

1. **Context Quality**: Provide good context about your project/situation
2. **Copy Full Prompt**: Include all questions and formatting for best results
3. **Review AI Answers**: Verify the AI's suggestions make sense for your situation
4. **Add Specifics**: Enhance AI responses with project-specific details
5. **Iterate**: If first AI response isn't clear, refine and try again