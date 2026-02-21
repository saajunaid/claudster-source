---
name: context-handoff
description: Context Handoff Skill
---

# Context Handoff Skill

## Purpose

Capture session state for **unexpected interruptions or emergency context exhaustion**, enabling continuation in a new chat.

---

## âš ï¸ IMPORTANT: Handoff vs. Phased Work

### This Skill is for EMERGENCIES, Not Routine Workflow

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    WHEN TO USE WHAT                                         â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                             â”‚
â”‚  LARGE PLANNED WORK (features, refactors)                                  â”‚
â”‚  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€                                 â”‚
â”‚  âœ… Use PHASED EXECUTION with a PLAN DOCUMENT                              â”‚
â”‚  â€¢ Break work into phases (each phase = 1 session)                         â”‚
â”‚  â€¢ Each phase has natural completion point (tests pass)                    â”‚
â”‚  â€¢ Plan doc is source of truth (e.g., plans/*.md)                 â”‚
â”‚  â€¢ New session reads plan doc, continues next phase                        â”‚
â”‚  â€¢ This is PLANNED, PREDICTABLE, EFFICIENT                                 â”‚
â”‚                                                                             â”‚
â”‚  UNEXPECTED SITUATIONS                                                      â”‚
â”‚  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€                                                  â”‚
â”‚  âœ… Use CONTEXT HANDOFF SKILL                                              â”‚
â”‚  â€¢ Interrupted mid-task (meeting, end of day)                              â”‚
â”‚  â€¢ Context filled unexpectedly (underestimated complexity)                 â”‚
â”‚  â€¢ Handing work to another person                                          â”‚
â”‚  â€¢ Emergency checkpoint before risky operation                             â”‚
â”‚  â€¢ This is REACTIVE, for UNPLANNED situations                              â”‚
â”‚                                                                             â”‚
â”‚  âŒ DON'T DO THIS                                                          â”‚
â”‚  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€                                                      â”‚
â”‚  â€¢ Handoff â†’ New Chat â†’ Handoff â†’ New Chat (repeat 20x)                   â”‚
â”‚  â€¢ This creates chat sprawl and is inefficient                             â”‚
â”‚  â€¢ If you're doing this, you need a PLAN DOCUMENT instead                  â”‚
â”‚                                                                             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Phased Work (The Right Way for Large Features)

```
1. CREATE PLAN DOCUMENT FIRST
   â””â”€â”€ plans/my-feature.md
       â”œâ”€â”€ Phase 1: Database changes (1 session)
       â”œâ”€â”€ Phase 2: Repository layer (1 session)
       â”œâ”€â”€ Phase 3: UI components (1 session)
       â””â”€â”€ Phase 4: Testing (1 session)

2. EXECUTE ONE PHASE PER SESSION
   â””â”€â”€ Session starts by reading plan doc
   â””â”€â”€ Implements ONE phase completely
   â””â”€â”€ Updates plan doc: "Phase X âœ…"
   â””â”€â”€ Tests pass for that phase
   â””â”€â”€ Natural end â†’ start new chat for next phase

3. EACH NEW SESSION
   â””â”€â”€ "Read plans/my-feature.md and implement Phase N"
   â””â”€â”€ Clean context, focused work
   â””â”€â”€ No emergency handoffs needed
```

### When Handoff IS Appropriate

- You're mid-phase and get interrupted
- Complexity was underestimated, context filling faster than expected
- Debugging took longer than planned, need to pause
- Handing off to a teammate
- Need checkpoint before attempting risky change

---

## When to Use This Skill

Load this skill when:
- **Interrupted** mid-task and need to continue later
- **Unexpected** context exhaustion (underestimated complexity)
- **Handing off** work to another developer/session
- **Checkpoint** before a risky operation

**This skill is NOT for:**
- Routine large feature development (use phased execution)
- Planned multi-session work (use plan documents)
- Every time context gets "kind of full" (plan better instead)

**Trigger phrases:**
- "I need to stop here unexpectedly"
- "Context is filling faster than expected"
- "Checkpoint this - I'll continue later"
- "Hand this off to [person/tomorrow]"

---

## Exit Timing Guidelines

### Context Budget for Handoff

The handoff process itself consumes context:

| Handoff Type | Token Cost | Safe Exit Point |
|--------------|------------|-----------------|
| **Quick** | ~2,000-3,000 tokens | â‰¤85% context full |
| **Full** | ~6,000-8,000 tokens | â‰¤75% context full |

### Recommended Exit Points

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                        CONTEXT USAGE GUIDELINES                             â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                             â”‚
â”‚  0%â”€â”€â”€â”€â”€â”€â”€â”€50%â”€â”€â”€â”€â”€â”€â”€â”€65%â”€â”€â”€â”€â”€â”€â”€â”€75%â”€â”€â”€â”€â”€â”€â”€â”€85%â”€â”€â”€â”€â”€â”€â”€â”€95%â”€â”€â”€â”€â”€â”€â”€â”€100%     â”‚
â”‚  â”‚         â”‚          â”‚          â”‚          â”‚          â”‚          â”‚        â”‚
â”‚  â”‚  WORK   â”‚   WORK   â”‚  âš ï¸ PLAN â”‚ ðŸ”¶ FULL  â”‚ ðŸ”´ QUICK â”‚ âŒ TOO   â”‚        â”‚
â”‚  â”‚  ZONE   â”‚   ZONE   â”‚   EXIT   â”‚ HANDOFF  â”‚ ONLY     â”‚ LATE     â”‚        â”‚
â”‚  â”‚         â”‚          â”‚          â”‚          â”‚          â”‚          â”‚        â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜        â”‚
â”‚                                                                             â”‚
â”‚  65-70%: Start thinking about handoff, wrap up current task                â”‚
â”‚  70-75%: IDEAL for full handoff (document + memories + prompt)             â”‚
â”‚  75-85%: Full handoff still possible, but be concise                       â”‚
â”‚  85-90%: Quick handoff only (prompt only, no document)                     â”‚
â”‚  90%+:   Emergency handoff - bare minimum, risk of truncation              â”‚
â”‚                                                                             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Session Complexity Indicators

**Simple session** (Quick handoff sufficient):
- Single task focus
- Few files modified (<5)
- No major architectural decisions
- Clear next steps

**Complex session** (Full handoff recommended):
- Multiple interrelated tasks
- Many files modified (5+)
- Important decisions made
- Discoveries about codebase
- Work spanning multiple areas
- Another person may continue the work

---

## Auto-Detect: Full vs Quick Handoff

When user doesn't specify, **automatically determine** based on:

### Decision Matrix

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    HANDOFF TYPE AUTO-DETECTION                               â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                              â”‚
â”‚  Score each factor (0-2), sum total:                                         â”‚
â”‚                                                                              â”‚
â”‚  COMPLEXITY FACTORS                                           Score          â”‚
â”‚  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€          â”‚
â”‚  Files modified:        1-3 = 0,  4-7 = 1,  8+ = 2            [__]          â”‚
â”‚  Decisions made:        0-1 = 0,  2-3 = 1,  4+ = 2            [__]          â”‚
â”‚  Tasks in progress:     0-1 = 0,  2-3 = 1,  4+ = 2            [__]          â”‚
â”‚  Codebase discoveries:  0-1 = 0,  2-3 = 1,  4+ = 2            [__]          â”‚
â”‚  Errors encountered:    0   = 0,  1-2 = 1,  3+ = 2            [__]          â”‚
â”‚  Another person continues?  No = 0,  Maybe = 1,  Yes = 2      [__]          â”‚
â”‚                                                               â”€â”€â”€â”€â”€          â”‚
â”‚  TOTAL                                                        [__]          â”‚
â”‚                                                                              â”‚
â”‚  RESULT:                                                                     â”‚
â”‚  â”€â”€â”€â”€â”€â”€â”€â”€                                                                    â”‚
â”‚  0-3:  QUICK handoff (prompt only)                                          â”‚
â”‚  4-7:  FULL handoff (document + prompt)                                     â”‚
â”‚  8+:   FULL handoff + extra detail                                          â”‚
â”‚                                                                              â”‚
â”‚  OVERRIDE CONDITIONS (always use FULL):                                      â”‚
â”‚  â€¢ Significant architectural decisions made                                  â”‚
â”‚  â€¢ Multi-session work (this is session 2+)                                  â”‚
â”‚  â€¢ Plan document was created during session                                  â”‚
â”‚  â€¢ User explicitly requests full handoff                                     â”‚
â”‚                                                                              â”‚
â”‚  OVERRIDE CONDITIONS (always use QUICK):                                     â”‚
â”‚  â€¢ Context >85% full (no room for full)                                     â”‚
â”‚  â€¢ User explicitly requests quick handoff                                    â”‚
â”‚  â€¢ Simple bug fix or minor change                                            â”‚
â”‚                                                                              â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Example Auto-Detection

**Session A: Bug fix**
```
Files modified: 2 (score: 0)
Decisions: 0 (score: 0)
Tasks in progress: 0 (score: 0)
Discoveries: 1 (score: 0)
Errors: 1 (score: 1)
Handoff to others: No (score: 0)
TOTAL: 1 â†’ QUICK HANDOFF
```

**Session B: Feature implementation**
```
Files modified: 8 (score: 2)
Decisions: 3 (score: 1)
Tasks in progress: 2 (score: 1)
Discoveries: 4 (score: 2)
Errors: 2 (score: 1)
Handoff to others: Maybe (score: 1)
TOTAL: 8 â†’ FULL HANDOFF + EXTRA DETAIL
```

### Invocation Syntax

```
# Let AI decide (auto-detect)
"Do a context handoff"
"Context is getting full, let's handoff"

# Force full handoff
"Do a FULL context handoff"
"Context handoff with documentation"

# Force quick handoff
"Quick handoff"
"Just give me a continuation prompt"
```

---

## The Handoff Protocol

### Overview

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                        CONTEXT HANDOFF PROTOCOL                             â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                             â”‚
â”‚  Phase 1: ANALYZE          Phase 2: PERSIST         Phase 3: GENERATE      â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”‚
â”‚  â”‚ â€¢ Session state â”‚  â”€â”€â–¶ â”‚ â€¢ Memory tool   â”‚  â”€â”€â–¶ â”‚ â€¢ Handoff doc   â”‚     â”‚
â”‚  â”‚ â€¢ Git status    â”‚      â”‚ â€¢ Key learnings â”‚      â”‚ â€¢ Continuation  â”‚     â”‚
â”‚  â”‚ â€¢ Decisions     â”‚      â”‚                 â”‚      â”‚   prompt        â”‚     â”‚
â”‚  â”‚ â€¢ Context score â”‚      â”‚                 â”‚      â”‚                 â”‚     â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â”‚
â”‚                                                                             â”‚
â”‚  Phase 4: SUMMARIZE        Phase 5: VERIFY                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                              â”‚
â”‚  â”‚ â€¢ Output stats  â”‚  â”€â”€â–¶ â”‚ â€¢ File created? â”‚                              â”‚
â”‚  â”‚ â€¢ Next steps    â”‚      â”‚ â€¢ Prompt ready? â”‚                              â”‚
â”‚  â”‚ â€¢ Warnings      â”‚      â”‚ â€¢ Git clean?    â”‚                              â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                              â”‚
â”‚                                                                             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Phase 1: ANALYZE

### 1.1 Session State Extraction

Extract and structure this information:

```yaml
session_metadata:
  date: <YYYY-MM-DD>
  duration: <approximate duration>
  primary_objective: <main goal>
  secondary_objectives: [<list>]
  previous_handoff: <path to prior handoff if this is a continuation>

context_priority:  # Score each item: CRITICAL / IMPORTANT / CONTEXT
  critical:  # Must be in continuation prompt
    - <item>
  important:  # Should be in handoff doc
    - <item>
  context:   # Nice to have, can be discovered from code
    - <item>

work_status:
  completed:
    - task: <task>
      files: [<files>]
      outcome: <result>
      tests: <passing/failing/not-written>
  
  in_progress:
    - task: <task>
      percent_complete: <0-100>
      current_state: <description>
      next_action: <specific next step>
      blockers: [<any blockers>]
  
  pending:
    - task: <task>
      priority: <high/medium/low>
      estimated_effort: <small/medium/large>
      dependencies: [<what must be done first>]

decisions_made:
  - decision: <what was decided>
    rationale: <why - this is CRITICAL for continuity>
    alternatives_rejected: <other options and why not>
    reversible: <yes/no>

discoveries:  # Things learned about the codebase
  patterns:
    - <pattern discovered>
  gotchas:
    - <gotcha or edge case>
  conventions:
    - <project convention learned>

errors_encountered:
  - error: <error description>
    resolution: <how it was fixed, or "unresolved">
    prevention: <how to avoid in future>
```

### 1.2 Git State Capture

Run these commands and capture output:

```powershell
# Current branch
git branch --show-current

# Uncommitted changes
git status --short

# Recent commits (last 3)
git log --oneline -3

# Stash list
git stash list
```

Structure as:
```yaml
git_state:
  branch: <branch name>
  uncommitted_files: [<list of modified files>]
  recent_commits:
    - hash: <short hash>
      message: <commit message>
  stashes: [<stash descriptions>]
  clean: <true/false>
```

### 1.3 Context Compression

For large sessions, apply compression:

| Content Type | Compression Strategy |
|--------------|---------------------|
| Long code changes | Summarize as "Modified X to add Y functionality" |
| Multiple similar errors | Group as "Resolved N instances of error type X" |
| Exploratory searches | Summarize as "Investigated X, found Y" |
| Chat tangents | Omit unless they led to decisions |

**Compression Rules:**
1. Keep ALL decisions and their rationale
2. Keep ALL blockers and error resolutions
3. Summarize repetitive work
4. Omit exploratory dead-ends unless they inform future work

---

## Phase 2: PERSIST (Memory Tool)

### 2.1 Store Key Learnings

Use the `memory` tool to persist learnings that should survive beyond just the next session:

```
For each discovery that meets these criteria:
- Actionable for future coding tasks
- Not obvious from code inspection
- Unlikely to change soon
- Not sensitive/secret

Store with memory tool:
- fact: <the learning>
- reason: "Discovered during [task] on [date]"
- citations: [<relevant file paths>]
```

**Example Memory Entries:**
```
✅ GOOD: "orders.customer_id links to customers.id via FK for order-customer correlation"
âœ… GOOD: "This project uses queries.yaml for all SQL - never inline SQL in Python"
âŒ BAD: "Fixed a typo in line 42" (too specific, not reusable)
âŒ BAD: "User prefers tabs over spaces" (preference, not fact)
```

### 2.2 What NOT to Persist

- Session-specific decisions (goes in handoff doc, not memory)
- Temporary workarounds
- User preferences
- Anything that might change soon

---

## Phase 3: GENERATE

### 3.1 Create Handoff Document

Create file at: `handoffs/YYYY-MM-DD_<task-slug>.md`

**Naming convention:**
- Use date and short task description
- Examples: `2026-02-05_interactionid-linking.md`, `2026-02-05_api-refactor.md`

**Document Template:**

```markdown
# Context Handoff: <Task Name>

**Date**: <YYYY-MM-DD>
**Status**: <In Progress | Blocked | Ready for Review>
**Previous Handoff**: <link or "None - fresh start">

## Executive Summary

<2-3 sentences: What was being done, current state, what's next>

---

## ðŸŽ¯ Objectives

### Primary Goal
<Main objective in one sentence>

### Success Criteria
- [ ] <Criterion 1>
- [ ] <Criterion 2>

### Secondary Goals
- <Goal 1>
- <Goal 2>

---

## ðŸ“Š Progress

### âœ… Completed
| Task | Files Modified | Tests | Outcome |
|------|----------------|-------|---------|
| <task> | <files> | âœ…/âŒ/â³ | <outcome> |

### ðŸ”„ In Progress
| Task | Progress | Current State | Next Action |
|------|----------|---------------|-------------|
| <task> | <X%> | <state> | <next step> |

### ðŸ“‹ Pending
| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| <task> | ðŸ”´/ðŸŸ¡/ðŸŸ¢ | S/M/L | <deps> |

---

## ðŸ§­ Key Decisions

| # | Decision | Rationale | Alternatives Rejected |
|---|----------|-----------|----------------------|
| 1 | <decision> | <why - be specific> | <what else was considered> |

**Decision Details:**

### Decision 1: <Title>
**Context**: <Why this decision was needed>
**Choice**: <What was decided>
**Rationale**: <Detailed reasoning>
**Trade-offs**: <What we gave up>
**Reversibility**: <Easy/Hard to change later>

---

## ðŸ”§ Technical Context

### Key Files
| File | Purpose | Status |
|------|---------|--------|
| `<path>` | <why it matters> | <modified/created/reference> |

### Patterns Used
```python
# <Pattern name>
<code example if helpful>
```

### Gotchas & Edge Cases
- âš ï¸ <gotcha 1>
- âš ï¸ <gotcha 2>

### Dependencies
- <External service/package>

---

## ðŸ› Issues & Blockers

| Issue | Status | Resolution/Attempt |
|-------|--------|-------------------|
| <issue> | ðŸ”´/ðŸŸ¡/ðŸŸ¢ | <what was tried> |

---

## ðŸŒ¿ Git State

- **Branch**: `<branch>`
- **Clean**: <Yes/No>
- **Uncommitted**: <list or "None">
- **Last Commit**: `<hash>` - <message>

---

## â–¶ï¸ Continuation Instructions

### Pre-Flight Checklist
Before continuing, verify:
- [ ] On correct branch: `git branch --show-current`
- [ ] No unexpected changes: `git status`
- [ ] App runs: `streamlit run src/app.py --server.port 8501`
- [ ] Tests pass: `pytest tests/ -v`

### Immediate Next Steps
1. **<Step 1>** - <specific instruction>
2. **<Step 2>** - <specific instruction>
3. **<Step 3>** - <specific instruction>

### Rollback Plan
If something goes wrong:
1. <Recovery step 1>
2. <Recovery step 2>
3. Contact/escalation: <who to ask>

---

## ðŸ“‹ Continuation Prompt

Copy this into a new chat:

\`\`\`
Read handoffs/<filename>.md and continue the implementation.

**Status**: <In Progress>
**Next Step**: <Specific next action>

Key context:
1. <Critical point 1>
2. <Critical point 2>
3. <Critical point 3>

Files to focus on:
- \`<file1>\` - <relevance>
- \`<file2>\` - <relevance>
\`\`\`
```

### 3.2 Generate Console Output

Output to console with clear visual formatting:

```
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
                         CONTEXT HANDOFF COMPLETE
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

ðŸ“„ HANDOFF DOCUMENT
   Location: handoffs/<filename>.md
   
ðŸ§  MEMORIES PERSISTED
   <N> learnings saved for future sessions
   
ðŸ“Š SESSION SUMMARY
   âœ… Completed: <N> tasks
   ðŸ”„ In Progress: <N> tasks
   ðŸ“‹ Pending: <N> tasks
   
ðŸ“ FILES MODIFIED
   Created: <N> files
   Updated: <N> files
   
ðŸŒ¿ GIT STATUS
   Branch: <branch>
   Clean: <Yes/No>

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
                      CONTINUATION PROMPT (COPY BELOW)
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

Read the handoff document at `handoffs/<filename>.md` and continue.

## Quick Context
<2-3 sentence summary>

## Current State
- **Last Completed**: <task>
- **In Progress**: <task at X%>
- **Blocked On**: <blocker or "Nothing">

## Immediate Next Step
<Specific, actionable instruction>

## Critical Files
- `<path1>` - <one-line description>
- `<path2>` - <one-line description>

## Must-Know Context
1. <Most critical thing>
2. <Second most critical>
3. <Third most critical>

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
                              âš ï¸  NEXT ACTIONS
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

1. Copy the continuation prompt above
2. Start a NEW chat (Ctrl+L or Cmd+L)
3. Paste the prompt
4. The new session will read the handoff doc and continue

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

---

## Phase 4: VERIFY

Before completing handoff, verify:

- [ ] Handoff document created successfully
- [ ] Document contains all critical decisions
- [ ] Continuation prompt is self-contained
- [ ] Git state is captured (or noted as unavailable)
- [ ] No uncommitted critical changes that could be lost

---

## Quick Handoff Mode

For simpler sessions, user can request:
```
Quick handoff - no document, just the prompt
```

In this mode:
1. Skip document creation
2. Generate detailed continuation prompt only
3. Use memory tool for key learnings
4. Output shorter summary

---

## Multi-Session Chains

For work spanning 3+ sessions:

1. **Link handoffs**: Each handoff references the previous one
2. **Maintain thread**: `previous_handoff:` field creates chain
3. **Summarize chain**: New handoff includes summary of full history
4. **Clean up**: After work completes, archive or delete old handoffs

**Chain Example:**
```
Session 1 â†’ handoff_2026-02-01_feature-start.md
Session 2 â†’ handoff_2026-02-03_feature-mid.md (links to 02-01)
Session 3 â†’ handoff_2026-02-05_feature-final.md (links to 02-03, summarizes all)
Session 4 â†’ Completes work, deletes handoff chain
```

---

## Integration with Agents

Any agent can invoke this skill. Add to agent instructions:

```markdown
### When Context Gets Full
If you notice context is 70-85% full, or user mentions context limits:
1. Load `skills/context-handoff/SKILL.md`
2. Follow the handoff protocol
3. Ensure user has continuation prompt before ending
```

---

## Best Practices

| Practice | Implementation |
|----------|----------------|
| **Proactive handoff** | Don't wait until 95% - quality degrades |
| **Decision rationale** | ALWAYS capture WHY, not just WHAT |
| **Test state** | Note if tests pass/fail before handoff |
| **Git state** | Capture branch and uncommitted changes |
| **Critical vs context** | Prioritize what goes in prompt vs doc |
| **Chain cleanup** | Delete handoffs after work completes |
| **Memory selectivity** | Only persist truly reusable learnings |
