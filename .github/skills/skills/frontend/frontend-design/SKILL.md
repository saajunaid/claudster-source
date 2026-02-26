---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications. Generates creative, polished code that avoids generic AI aesthetics while strictly adhering to the user's technical standards.
---

# Frontend Design Skill

This skill guides the creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

## 1. Core Principle: Avoid "AI Slop"
- **Typography:** Avoid system fonts (Inter, Arial, Roboto). Pair a distinctive display font (e.g., *Cormorant Garamond*, *Playfair Display*, *Space Mono*) with a refined, readable body font. Use dramatic scale jumps ($h1 > 5rem$ vs metadata $< 0.75rem$).
- **Color & Theme:** Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Visuals:** Create atmosphere and depth using textures (grain, noise), glassmorphism, or complex gradients rather than defaulting to solid flat colors.

## 2. Technical Implementation Standards
**CRITICAL:** You must ignore generic React patterns. Instead, you represent the specific technical architecture defined in the user's stack.

**Mandatory Reference:**
Before writing any component logic, state management, or hooks, you must cross-reference and apply the patterns found in:
`./references/my-tech-stack.md`

Specifically, you must:
1.  **Use Composition:** Build flexible UIs using the *Composition Over Inheritance* and *Compound Component* patterns defined in the reference file.
2.  **Use Custom Hooks:** Do not write ad-hoc logic for debouncing or toggling; use `useDebounce` and `useToggle` from the reference.
3.  **Optimize Performance:** Apply `useMemo` and `useCallback` strictly according to the "Memoization Rules" in the reference.
4.  **Ensure Stability:** Wrap complex or risky components in the `ErrorBoundary` pattern provided.
5.  **Enforce Accessibility:** Follow the keyboard navigation and focus management patterns exactly as specified.

## 3. Design Thinking Process
Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Tone:** Pick an extreme (Brutalist, Luxury, Retro-futuristic, Editorial, Industrial).
- **Motion:** Use animations for effects and micro-interactions. Focus on high-impact moments (staggered page loads) rather than scattered micro-interactions.
- **Differentiation:** What makes this UNFORGETTABLE? What's the one thing someone will remember?

## 4. Output Requirements
Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- **Production-grade:** Functional, responsive, and accessible.
- **Visually striking:** Memorable and cohesive with a clear point-of-view.
- **Technically compliant:** Strictly follows the architecture in `my-tech-stack.md`.

## 5. Transition Integrity (No Stale UI)

For data-heavy views that switch entities (profile A → profile B), enforce deterministic transitions:

- Use a **single render region** (e.g., Streamlit's `st.empty()`) that replaces its entire content on each render pass.
- **NEVER use dynamic keys** (nonce, entity ID) on containers inside `st.empty()` — dynamic keys cause the framework to create *new* DOM nodes instead of replacing existing ones, leaving ghost/shadow copies visible for 1-2 seconds until frontend reconciliation catches up.
- Use **stable keys** on inner containers. The render region handles content replacement; inner containers just need stable identity for in-place DOM updates.
- Temporarily hide high-salience identity panels/tabs during loading to avoid ghosted prior-state flashes.
- Execute state transitions outside container context managers to avoid interrupted cleanup.

Acceptance rule: users must only perceive `old state → loader → new state`, with no stale intermediate artifacts.