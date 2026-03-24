---
name: premium-react
description: React/Tailwind premium visual design and animation engineering. Use for premium visual design, animation engineering, Framer Motion, Bento grids, scroll reveals, magnetic buttons, parallax, cursor followers, or creative React/Tailwind UI. Prerequisite frontend-design must be loaded first.
---

# Premium React Skill

React/Tailwind specifics for premium, high-craft interfaces. Companion to `frontend-design` (which sets the taste principles). Load `frontend-design` skill before this one.

## 1. RSC Safety and `'use client'` Boundary Rules

- Default to React Server Components (RSC) — no client-side overhead unless required.
- Add `'use client'` **only when** the component uses: hooks (`useState`, `useEffect`, `useRef`), browser APIs, event listeners, or animation libraries.
- Never mark an entire route `'use client'` — push the boundary down to the smallest interactive leaf.
- Composition pattern: Server wrapper → client island.

```tsx
// ✅ GOOD: Thin client island
'use client'
export function AnimatedCard({ data }: { data: CardData }) {
  return <motion.div whileHover={{ scale: 1.02 }}>{data.title}</motion.div>
}

// Server component composes it
export default function Page() {
  const data = await fetchData()
  return <AnimatedCard data={data} />
}
```

## 2. Tailwind Version Lock and T4 Config Guard

- Always confirm Tailwind version in `package.json` before writing config.
- **Tailwind v4** uses CSS-first config (`@theme` in CSS, no `tailwind.config.ts`).
- **Tailwind v3** uses `tailwind.config.ts` with `theme.extend`.
- Never mix config patterns across versions — they are incompatible.
- Guard in config:

```ts
// tailwind.config.ts (v3 only)
import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: { display: ['var(--font-display)'] },
      animation: { 'fade-up': 'fadeUp 0.5s ease-out' },
      keyframes: { fadeUp: { from: { opacity: '0', transform: 'translateY(16px)' }, to: { opacity: '1', transform: 'none' } } },
    },
  },
}
export default config
```

## 3. Framer Motion Engineering

### Spring Physics
```tsx
// Use spring for organic feel — avoid linear/ease tweens for interactive elements
const springConfig = { type: 'spring', stiffness: 300, damping: 25 }

// Entrance animation
<motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={springConfig} />
```

### `useMotionValue` for Magnetic/Parallax Effects
```tsx
'use client'
import { useMotionValue, useSpring, useTransform } from 'framer-motion'

export function MagneticButton({ children }: { children: React.ReactNode }) {
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const springX = useSpring(x, { stiffness: 400, damping: 30 })
  const springY = useSpring(y, { stiffness: 400, damping: 30 })

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    x.set((e.clientX - cx) * 0.3)
    y.set((e.clientY - cy) * 0.3)
  }

  return (
    <motion.div style={{ x: springX, y: springY }} onMouseMove={handleMouseMove} onMouseLeave={() => { x.set(0); y.set(0) }}>
      {children}
    </motion.div>
  )
}
```

### `staggerChildren` for List Entrances
```tsx
const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }
const item = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0 } }

<motion.ul variants={container} initial="hidden" animate="show">
  {items.map(i => <motion.li key={i.id} variants={item}>{i.name}</motion.li>)}
</motion.ul>
```

### `AnimatePresence` for Conditional Renders
```tsx
import { AnimatePresence, motion } from 'framer-motion'

// MUST wrap conditional renders for exit animations to fire
<AnimatePresence mode="wait">
  {isVisible && (
    <motion.div key="panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      {content}
    </motion.div>
  )}
</AnimatePresence>
```

## 4. Bento Paradigm

Five card archetypes for Bento grid layouts:

| Archetype | Grid Span | Content Pattern |
|-----------|-----------|-----------------|
| Hero | 2×2 or 2×1 | Large stat or visual with bold typographic pairing |
| Feature | 1×2 | Icon + headline + 2-line description |
| Metric | 1×1 | Single KPI with trend indicator |
| Media | 2×1 or 3×1 | Full-bleed image / video |
| CTA | 1×1 | Action-oriented with hover state |

```tsx
// Responsive Bento grid
<div className="grid grid-cols-4 grid-rows-3 gap-3 auto-rows-[160px]">
  <BentoCard className="col-span-2 row-span-2" variant="hero" />
  <BentoCard className="col-span-1 row-span-1" variant="metric" />
  <BentoCard className="col-span-1 row-span-2" variant="feature" />
</div>
```

## 5. Performance Guardrails

- **Hardware-accelerated transforms only**: Animate `transform` (translate, scale, rotate) and `opacity`. Never animate `width`, `height`, `top`, `left`, `margin`, or any layout property.
- **DOM cost**: Keep animated subtrees shallow. Each `motion.div` wrapper adds reconciliation cost.
- **Z-index architecture**: Define in `tailwind.config.ts` as named layers. Never magic-number z-index inline.
- **`will-change` sparingly**: Only on elements that animate constantly (e.g., video overlay). Remove after animation completes.

```tsx
// ✅ GOOD: GPU-accelerated
<motion.div animate={{ x: 100, opacity: 0.5 }} />

// ❌ BAD: Layout animation — causes reflow
<motion.div animate={{ width: '200px' }} />
```

## 6. GSAP / Three.js Isolation

- Wrap GSAP and Three.js in a dedicated `'use client'` component with `dynamic(() => import(...), { ssr: false })`.
- GSAP must be version-matched to `@gsap/react` wrapper; never use raw GSAP in RSC files.
- Three.js scenes: isolate in `<Canvas>` (react-three-fiber) or a dedicated `<div ref={mountRef}>` with cleanup in `useEffect` return.

## 7. Creative Arsenal

### Scroll Reveal
```tsx
'use client'
import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'

export function ScrollReveal({ children }: { children: React.ReactNode }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })
  return (
    <motion.div ref={ref} initial={{ opacity: 0, y: 24 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.5, ease: 'easeOut' }}>
      {children}
    </motion.div>
  )
}
```

### Cursor Follower
```tsx
'use client'
export function CursorFollower() {
  const x = useMotionValue(-100)
  const y = useMotionValue(-100)
  const springX = useSpring(x, { stiffness: 200, damping: 20 })
  const springY = useSpring(y, { stiffness: 200, damping: 20 })

  useEffect(() => {
    const move = (e: MouseEvent) => { x.set(e.clientX - 8); y.set(e.clientY - 8) }
    window.addEventListener('mousemove', move)
    return () => window.removeEventListener('mousemove', move)
  }, [x, y])

  return <motion.div className="fixed top-0 left-0 size-4 rounded-full bg-accent pointer-events-none mix-blend-difference z-[9999]" style={{ x: springX, y: springY }} />
}
```

### Text Scramble / Character Animation
```tsx
// Stagger individual characters for cinematic text reveal
const chars = text.split('')
<motion.span>
  {chars.map((char, i) => (
    <motion.span key={i} initial={{ opacity: 0, y: '100%' }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03, ease: 'easeOut' }}>
      {char === ' ' ? '\u00A0' : char}
    </motion.span>
  ))}
</motion.span>
```

## 8. Accessibility Contract

All animations must respect `prefers-reduced-motion`:

```tsx
import { useReducedMotion } from 'framer-motion'

export function AnimatedSection({ children }: { children: React.ReactNode }) {
  const shouldReduce = useReducedMotion()
  return (
    <motion.div
      initial={{ opacity: 0, y: shouldReduce ? 0 : 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduce ? 0 : 0.4 }}
    >
      {children}
    </motion.div>
  )
}
```

## 9. Checklist Before Shipping

- [ ] All animations respect `prefers-reduced-motion`
- [ ] No layout properties animated (width, height, top, left)
- [ ] `AnimatePresence` wraps all conditional renders with exit animations
- [ ] GSAP/Three.js isolated behind `ssr: false` dynamic imports
- [ ] Bento grid tested on mobile (collapse to 1 or 2 columns)
- [ ] Magnetic effects have zero impact on keyboard navigation
- [ ] `'use client'` boundary at smallest possible leaf
- [ ] Z-index values from named config tokens, not inline integers
