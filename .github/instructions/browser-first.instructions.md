---
description: "Direct integrated-browser actions must use native browser tools first"
applyTo: "**"
priority: 200
---

# Browser-First Rule for Direct Integrated-Browser Requests

When the user explicitly asks to use the **integrated browser** or asks for a simple action on an **already-open browser page**, treat it as a direct browser task.

## Trigger examples
- "click this button in the integrated browser"
- "use the already-open browser page"
- "type into this field and tell me what happens"
- "report the visible status text"
- "check what changed on screen"

## Mandatory behavior
1. Use the native browser tools immediately on the existing page.
2. Perform the requested action directly in the browser.
3. Report the visible result briefly.
4. Stop unless the user asked for more.

## Do NOT do these first
- Read source files or inspect HTML
- Run `get_errors`
- Run terminal commands
- Search the workspace
- Load or use Playwright
- Produce a checklist, diagnostic wrapper, or long progress narrative

## Fallback rule
Only inspect code, use Playwright, or run diagnostics **if the native browser tools fail or are unavailable**.

## Example
If the user says:

> Use the already-open integrated browser page. Click "Run smoke action" and report the visible status text.

Then the correct behavior is:
- click the button in the open browser page
- report the on-screen status text
- do nothing else
