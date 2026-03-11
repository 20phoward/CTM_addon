# UI Redesign — Clean Corporate

## Goal
Restyle the frontend from basic Tailwind defaults to a clean, corporate look with a slate blue palette.

## Color Palette
- **Primary:** Slate (`slate-600`/`slate-700`/`slate-800`) replacing indigo
- **Page background:** `bg-slate-50` instead of white
- **Cards:** `bg-white border border-slate-200 rounded-lg` (flat, no shadows)
- **Text:** `slate-900` headings, `slate-500` secondary
- **Borders:** `slate-200` throughout
- **Buttons:** `bg-slate-700 hover:bg-slate-800 text-white`
- **Status colors:** Keep green/yellow/red but use muted variants
- **Score colors:** Keep existing semantic scale (green/yellow/orange/red)

## Component Changes

### Navbar (App.jsx)
- `bg-slate-800` background
- `hover:text-slate-200` links
- Role badge: muted slate tones

### Login (Login.jsx)
- Card with `border border-slate-200` instead of shadow
- `bg-slate-700` submit button
- Subtle, centered layout

### Dashboard (Dashboard.jsx)
- `bg-slate-50` page background
- Stat cards: border instead of shadow, remove uppercase labels
- Remove colored left-border nav widgets — use clean flat cards
- Tighter typography

### CallList (CallList.jsx)
- Table: `divide-y divide-slate-100`, tighter padding
- Refined badges
- Slate-toned filter controls

### CallDetail (CallDetail.jsx)
- Bordered cards instead of shadows
- Slate color scheme for metadata

### Reports (Reports.jsx)
- Chart colors: slate blue + muted emerald (replacing indigo + green)
- Bordered cards

### ScoreDisplay (ScoreDisplay.jsx)
- Slate-toned rings/bars replacing indigo/emerald
- Keep score color semantics

### Other Components
- AudioUpload, UserManagement, TeamManagement, AuditLog: same border/button treatment
- InactivityTimer, ProtectedRoute: no visual changes needed

## What Stays the Same
- All functionality, routing, data flow
- Score color coding logic
- Status badge semantics
- Responsive breakpoints
- API calls
