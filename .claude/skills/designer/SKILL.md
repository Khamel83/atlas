---
name: designer
description: "Create beautiful, modern web designs with clean HTML/CSS. Builds responsive layouts, landing pages, and UI components. Use when user says 'design', 'website', 'landing page', 'UI', 'make it look good', or 'CSS'."
allowed-tools: Read, Write
---

# Designer

You are an expert at creating beautiful, modern web designs.

## When To Use

- User asks to design a website, landing page, or UI
- User wants to create a portfolio, blog, or marketing page
- User mentions "make it look good" or "professional design"
- User needs a quick static site

## Design Philosophy

### Core Principles

1. **Clean, minimal aesthetics** - Whitespace is your friend
2. **Mobile-first responsive** - Works on all devices
3. **Fast loading** - No heavy frameworks unless needed
4. **Accessibility** - Semantic HTML, proper contrast, keyboard navigation
5. **Modern CSS** - Flexbox, Grid, custom properties

## Design System Defaults

```css
:root {
  /* Colors */
  --primary: #2563eb;
  --primary-dark: #1d4ed8;
  --text: #1f2937;
  --text-muted: #6b7280;
  --bg: #ffffff;
  --bg-alt: #f9fafb;
  --border: #e5e7eb;

  /* Typography */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* Spacing */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 2rem;
  --space-xl: 4rem;

  /* Sizing */
  --max-width: 1200px;
  --content-width: 720px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);

  /* Transitions */
  --transition: 150ms ease;
}
```

## Color Palette Presets

| Palette | Primary | Accent |
|---------|---------|--------|
| Professional Blue | `#2563eb` | `#3b82f6` |
| Warm Orange | `#ea580c` | `#f97316` |
| Forest Green | `#059669` | `#10b981` |
| Royal Purple | `#7c3aed` | `#8b5cf6` |
| Dark Mode | `--bg: #0f172a` | `--text: #f1f5f9` |

## Common Components

### Hero Section

```html
<section class="hero">
  <div class="container">
    <h1 class="hero-title">Your Headline Here</h1>
    <p class="hero-subtitle">A compelling subtitle</p>
    <div class="hero-cta">
      <a href="#" class="btn btn-primary">Get Started</a>
      <a href="#" class="btn btn-secondary">Learn More</a>
    </div>
  </div>
</section>
```

### Feature Grid

```html
<section class="features">
  <div class="container">
    <h2 class="section-title">Features</h2>
    <div class="feature-grid">
      <div class="feature-card">
        <div class="feature-icon">🚀</div>
        <h3>Feature One</h3>
        <p>Description of this amazing feature.</p>
      </div>
    </div>
  </div>
</section>
```

### Button Styles

```css
.btn {
  padding: var(--space-sm) var(--space-md);
  border-radius: 0.5rem;
  font-weight: 500;
  transition: var(--transition);
  cursor: pointer;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-dark);
}

.btn-secondary {
  background: transparent;
  border: 1px solid var(--border);
}
```

## Output Format

When creating designs, output:
1. **Single HTML file** with embedded CSS (for simple pages)
2. **Or separate files**: `index.html`, `styles.css`, `script.js`

Always include:
- Responsive meta tags
- Semantic HTML5
- CSS custom properties
- Smooth scroll behavior

## Responsive Breakpoints

```css
/* Mobile first */
/* Default styles are mobile */

/* Tablet */
@media (min-width: 768px) { }

/* Desktop */
@media (min-width: 1024px) { }

/* Large screens */
@media (min-width: 1280px) { }
```

## Anti-Patterns

- Heavy frameworks for simple pages
- Inline styles instead of CSS variables
- Fixed pixel widths (use rem, %, vw)
- Missing mobile viewport meta tag
- Low contrast text
- No focus states for accessibility

## Keywords

design, website, landing page, UI, CSS, HTML, make it look good, professional, responsive
