# Interactive AI Textbook — Frontend Architecture

> **Role:** Principal Frontend Architect & Docusaurus Expert  
> **Stack:** Docusaurus · Next.js 15 · TypeScript · Tailwind CSS  
> **Status:** Implementation v1.0

---

## 1. Architectural Philosophy

### 1.1 Dual-Framework Strategy

The platform serves two fundamentally different user needs — **content consumption** (reading textbooks) and **interactive learning** (AI chat, quizzes, interviews, dashboards). No single framework excels at both. The architecture uses each framework for what it does best:

| Framework | Role | Strengths |
|---|---|---|
| **Docusaurus** | Textbook reader | MDX content engine, versioning, built-in i18n, Algolia DocSearch, sidebar navigation, content organization |
| **Next.js 15** | Application shell | Auth, dashboards, real-time AI features, API routes, server components, streaming |

### 1.2 Integration Model

```
┌─────────────────────────────────────────────────────┐
│                     nextjs-app                       │
│  (App Router, Auth, Dashboard, AI Features)          │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │              docusaurus-content                  │ │
│  │  (Built as standalone static export, hosted      │ │
│  │   at /textbook/* via Next.js rewrites)           │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │              shared-ui                           │ │
│  │  (Component library: Tailwind, shadcn/ui)        │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Key decisions:**
- Docusaurus builds to static HTML/JS/CSS, served under `/textbook/*` via Next.js rewrites
- Shared design system lives as a standalone package consumed by both
- Authentication state is shared via cookie/session (same domain)
- AI features live exclusively in Next.js — Docusaurus embeds them via iframes or custom React components during build time
- Search is unified: DocSearch for content, Meilisearch/Typesense for semantic search across both

### 1.3 Monorepo Structure (pnpm + TurboRepo)

```
apps/
├── nextjs-app/              # Main application shell
│   ├── app/                 # Next.js 15 App Router
│   │   ├── (auth)/          # login, register, forgot-password
│   │   ├── (dashboard)/     # reader dashboard, progress
│   │   ├── textbook/        # Docusaurus proxy route
│   │   ├── ai/              # chat, tutor, quiz, interview
│   │   └── admin/           # admin dashboard
│   ├── components/          # app-specific components
│   ├── lib/                 # utilities, API clients, hooks
│   └── middleware.ts        # auth middleware
│
├── docusaurus-content/      # Textbook content engine
│   ├── docs/                # MDX chapter files
│   ├── i18n/                # translations
│   ├── src/                 # custom theme, components
│   └── docusaurus.config.ts # Docusaurus configuration
│
└── web/                     # (existing, consumer-facing site)

packages/
├── shared-ui/               # Design system (shadcn/ui + Tailwind)
├── auth/                    # Auth helpers, types, API client
├── config/                  # Shared env, constants
├── types/                   # Shared TypeScript types
└── ai/                      # AI SDK client, prompts

┌─────────────────────────────────────────────────────┐
│                    packages/                          │
│                                                       │
│  shared-ui  auth  config  types  ai                  │
│     │        │       │       │     │                  │
│     └────────┴───────┴───────┴─────┘                  │
│                     │                                  │
│              apps/nextjs-app                          │
│              apps/docusaurus-content                 │
└─────────────────────────────────────────────────────┘
```

---

## 2. Docusaurus Content Architecture

### 2.1 Why Docusaurus

| Feature | Docusaurus | Next.js (static) |
|---|---|---|
| MDX content engine | **Built-in** with frontmatter, imports, components | Requires integration |
| Versioned docs | **Built-in** (`docs/1.0`, `docs/2.0`) | Manual implementation |
| i18n | **Built-in** (crowdin integration, per-locale builds) | Manual |
| Sidebar navigation | **Built-in** (automatic, category-based) | Manual |
| Search | **DocSearch** (Algolia) | Manual |
| Blog | **Built-in** | Needs additional setup |
| Custom themes | Swizzleable components | N/A (framework) |
| Build speed | ~2s per locale | Comparable |
| Interactive features | **Limited** — iframes or custom JS | Natural |

### 2.2 Content Organization

```
docusaurus-content/
├── docs/
│   ├── 01-introduction/
│   │   ├── 01-what-is-ai.mdx
│   │   ├── 02-history.mdx
│   │   └── 03-applications.mdx
│   ├── 02-machine-learning/
│   │   ├── 01-overview.mdx
│   │   ├── 02-supervised.mdx
│   │   ├── 03-unsupervised.mdx
│   │   └── 04-reinforcement.mdx
│   ├── 03-neural-networks/
│   └── ...
│
├── i18n/
│   ├── en/
│   │   └── docusaurus-plugin-content-docs/
│   │       └── current/              # Advanced English (source)
│   ├── en-plain/
│   │   └── docusaurus-plugin-content-docs/
│   │       └── current/              # Plain English translation
│   ├── ur/
│   │   └── docusaurus-plugin-content-docs/
│   │       └── current/              # Urdu translation
│   └── ur-rom/
│       └── docusaurus-plugin-content-docs/
│           └── current/              # Roman Urdu translation
│
├── src/
│   ├── components/                   # Custom React components
│   │   ├── AiChatButton.tsx          # Opens AI chat for this section
│   │   ├── QuizEmbed.tsx             # Inline quiz component
│   │   ├── VoiceControls.tsx         # TTS controls for section
│   │   ├── CodeExample.tsx           # Interactive code blocks
│   │   ├── Diagram.tsx              # Interactive diagrams
│   │   └── BookmarkButton.tsx        # Bookmark this section
│   ├── theme/
│   │   ├── DocItem/                  # Swizzled doc page layout
│   │   └── DocSidebar/              # Enhanced sidebar
│   └── css/
│       └── custom.css               # Tailwind + custom styles
│
├── static/
│   ├── audio/                        # Narration audio files
│   └── images/                       # Textbook images
│
├── sidebars.ts                       # Sidebar configuration
└── docusaurus.config.ts              # Main configuration
```

### 2.3 Docusaurus Configuration

```typescript
// docusaurus.config.ts — key configuration points

docusaurus.config = {
  title: "AI Enterprises Textbook",
  url: "https://app.ai-enterprises.com",
  baseUrl: "/textbook/",
  trailingSlash: false,

  // ── Internationalization ─────────────────────────
  i18n: {
    defaultLocale: "en",
    locales: ["en", "en-plain", "ur", "ur-rom"],
    localeConfigs: {
      en:        { label: "Advanced English", direction: "ltr" },
      "en-plain": { label: "Plain English",   direction: "ltr" },
      ur:        { label: "اردو",             direction: "rtl" },
      "ur-rom":  { label: "Roman Urdu",       direction: "ltr" },
    },
  },

  // ── Plugins ──────────────────────────────────────
  plugins: [
    // Custom plugin for AI features integration
    [
      "./plugins/ai-integration",
      { apiUrl: process.env.NEXT_PUBLIC_API_URL },
    ],
    // Voice narration plugin
    [
      "./plugins/voice-narration",
      { basePath: "/audio" },
    ],
  ],

  // ── Theme ────────────────────────────────────────
  themes: ["@docusaurus/theme-live-codeblock"],

  // ── Presets ──────────────────────────────────────
  presets: [
    [
      "@docusaurus/preset-classic",
      {
        docs: {
          sidebarPath: "./sidebars.ts",
          editUrl:     "https://github.com/org/repo/edit/main/",
          showLastUpdateTime: true,
          remarkPlugins:  [remarkMath, remarkMermaid],
          rehypePlugins: [rehypeKatex],
        },
        blog: false,
        theme: {
          customCss: "./src/css/custom.css",
        },
      },
    ],
  ],
};
```

### 2.4 Content Lifecycle

```
Author writes MDX in `docs/`
          │
          ▼
Sidebar auto-generated (or manual sidebars.ts)
          │
          ▼
i18n: Crowdin pulls source → translators → PR with locale files
          │
          ▼
Build: Docusaurus builds each locale as static export
          │
          ▼
Output: `build/textbook/` (per-locale directory)
          │
          ▼
Served via Next.js rewrite: `/textbook/{locale}/*`
```

### 2.5 Multi-Locale Build Strategy

```
Build command (CI):
  docusaurus build --locale en         # Advanced English
  docusaurus build --locale en-plain    # Plain English
  docusaurus build --locale ur          # Urdu
  docusaurus build --locale ur-rom      # Roman Urdu

Output structure:
  build/textbook/
    en/
      index.html
      docs/01-introduction/index.html
    en-plain/
      ...
    ur/
      ...
    ur-rom/
      ...
```

### 2.6 Versioning Strategy

```
docs/
├── current/              # Next release (unreleased)
├── 1.0/                  # v1.0 stable
└── 0.9/                  # v0.9 archive

Sidebar config:
  docs/1.0/sidebar.ts     # Each version has own sidebar
  docs/0.9/sidebar.ts

Build config:
  versions: {
    current: { label: "Next", path: "next" },
    "1.0":   { label: "v1.0", path: "", banner: "none" },
    "0.9":   { label: "v0.9", path: "0.9", banner: "unmaintained" },
  }
```

### 2.7 Docusaurus Custom Components

Each MDX page can embed interactive AI components via custom React components registered in Docusaurus' plugin system:

```tsx
// Embedded in MDX directly:
<AiChatButton section="neural-networks-intro" />

<QuizEmbed quizId="nn-quiz-1" language="en" />

<VoiceControls section="neural-networks-intro" voice="female" />

<BookmarkButton sectionId="nn-intro" />
```

These components are built in the shared-ui package and imported into Docusaurus' component registry via plugin configuration.

---

## 3. Next.js Application Architecture

### 3.1 App Router Layout

```
apps/nextjs-app/app/
├── layout.tsx                          # Root layout (fonts, providers)
├── page.tsx                            # Landing / redirect to dashboard
├── not-found.tsx                       # 404 page
├── error.tsx                           # Global error boundary
│
├── (auth)/                             # Route group (no layout nesting)
│   ├── login/
│   │   └── page.tsx                    # Login page
│   ├── register/
│   │   └── page.tsx                    # Registration page
│   ├── forgot-password/
│   │   └── page.tsx                    # Forgot password
│   └── reset-password/
│       └── page.tsx                    # Password reset
│
├── (dashboard)/                        # Route group (protected)
│   ├── layout.tsx                      # Dashboard layout (sidebar, topbar)
│   ├── page.tsx                        # Reader dashboard
│   ├── progress/
│   │   └── page.tsx                    # Progress tracking page
│   ├── bookmarks/
│   │   └── page.tsx                    # Bookmark manager
│   ├── notes/
│   │   └── page.tsx                    # Notes manager
│   └── settings/
│       └── page.tsx                    # User settings (voice, lang, theme)
│
├── textbook/                           # Docusaurus proxy
│   └── [[...slug]]/
│       └── page.tsx                    # Next.js rewrite → Docusaurus
│
├── ai/
│   ├── layout.tsx                      # AI section layout
│   ├── chat/
│   │   └── page.tsx                    # Full AI chat interface
│   ├── tutor/
│   │   └── page.tsx                    # AI tutor (Socratic)
│   ├── quiz/
│   │   ├── page.tsx                    # Quiz listing
│   │   └── [quizId]/
│   │       └── page.tsx                # Individual quiz
│   └── interview/
│       ├── page.tsx                    # Interview selection
│       └── [sessionId]/
│           └── page.tsx                # Live interview session
│
├── admin/                              # Admin dashboard
│   ├── layout.tsx                      # Admin layout (role-gated)
│   ├── page.tsx                        # Admin overview
│   ├── users/
│   │   └── page.tsx                    # User management
│   ├── content/
│   │   └── page.tsx                    # Content analytics
│   └── analytics/
│       └── page.tsx                    # Platform analytics
│
└── api/                                # Next.js API routes
    ├── auth/                           # Auth proxy to FastAPI
    ├── search/                         # Semantic search proxy
    ├── ai/                             # AI feature proxies
    │   ├── chat/
    │   ├── quiz/
    │   ├── tutor/
    │   └── interview/
    └── webhooks/                       # Webhook receivers
```

### 3.2 Route Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                     Browser Request                       │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
            Next.js Middleware (middleware.ts)
            ├── Extracts session cookie
            ├── Validates JWT (or calls FastAPI introspect)
            ├── Redirects to login if unauthenticated
            └── Sets request headers for downstream
                        │
                        ▼
              ┌─── Route Matcher ───┐
              │                     │
         textbook/*           all other routes
              │                     │
              ▼                     ▼
      Next.js Rewrite        Next.js App Router
      → Docusaurus           → Server Components
        static files           → Data fetching
                               → Client Components
                                    │
                                    ▼
                              FastAPI Backend
                              (Auth, AI, Search)
```

### 3.3 Middleware (Auth Guard)

```typescript
// middleware.ts

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public paths
  const publicPaths = ["/login", "/register", "/forgot-password",
                       "/reset-password", "/textbook", "/api", "/_next"];

  if (publicPaths.some(p => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Check session
  const sessionCookie = request.cookies.get("__Host-refresh_token");
  const accessToken = request.cookies.get("access_token");

  if (!sessionCookie && !accessToken) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Admin path gating
  if (pathname.startsWith("/admin")) {
    // Delegate to FastAPI for role check
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

### 3.4 Layout Components

```
RootLayout (app/layout.tsx)
├── ThemeProvider (dark mode)
├── AuthProvider (session context)
├── LocaleProvider (language context)
└── {children}
    │
    ├── (auth)/ → AuthLayout (centered card, no sidebar)
    │   └── page.tsx
    │
    ├── (dashboard)/ → DashboardLayout
    │   ├── DashboardSidebar
    │   ├── DashboardTopbar
    │   └── {children}
    │
    ├── ai/ → AiLayout
    │   ├── AiSidebar (session list)
    │   └── {children}
    │
    └── admin/ → AdminLayout
        ├── AdminSidebar
        ├── AdminTopbar
        └── {children}
```

### 3.5 Key Server Components (RSC)

| Component | Data Source | Cache Strategy |
|---|---|---|
| `ReaderDashboard` | FastAPI: progress, bookmarks, recent | `next/revalidate: 60` |
| `ChapterContent` | Docusaurus static (via rewrite) | Static |
| `BookmarkList` | FastAPI: user bookmarks | `revalidate: 30` |
| `NoteList` | FastAPI: user notes | `revalidate: 30` |
| `ProgressChart` | FastAPI: aggregated progress | `revalidate: 300` |
| `SearchResults` | Meilisearch/Typesense | Per-request |
| `QuizList` | FastAPI: available quizzes | `revalidate: 300` |
| `AdminStats` | FastAPI: platform metrics | `revalidate: 60` |

### 3.6 Key Client Components

| Component | State Management | Real-time |
|---|---|---|
| `AiChat` | React state + SWR | SSE streaming |
| `AiTutor` | React state + SWR | SSE streaming |
| `QuizPlayer` | React state | No |
| `InterviewSession` | React state + WebSocket | Bidirectional |
| `VoicePlayer` | React state | Audio streaming |
| `SearchInput` | React state + debounce | No |
| `ProgressBar` | SWR polling | No |
| `DarkModeToggle` | Cookie + class | Instant |
| `LanguageSwitcher` | Cookie + navigation | Page reload |
| `VoiceSelector` | Cookie | Instant |

---

## 4. Design System (shared-ui)

### 4.1 Component Architecture

```
packages/shared-ui/
├── src/
│   ├── index.ts                      # Barrel export
│   ├── globals.css                   # Tailwind base + shadcn/ui
│   │
│   ├── ui/                           # Primitive components (shadcn/ui)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── dropdown-menu.tsx
│   │   ├── input.tsx
│   │   ├── select.tsx
│   │   ├── tabs.tsx
│   │   ├── toast.tsx
│   │   ├── tooltip.tsx
│   │   ├── sheet.tsx
│   │   ├── badge.tsx
│   │   └── ... (30+ shadcn/ui components)
│   │
│   ├── textbook/                     # Textbook-specific components
│   │   ├── ChapterCard.tsx           # Chapter card for dashboard
│   │   ├── SectionContent.tsx        # Section content renderer
│   │   ├── SectionNavigation.tsx     # Prev/next section
│   │   ├── ReadingProgress.tsx       # Progress bar within section
│   │   ├── CodeBlock.tsx            # Enhanced code block
│   │   └── DiagramViewer.tsx         # Interactive diagram
│   │
│   ├── ai/                           # AI feature components
│   │   ├── ChatMessage.tsx           # Chat bubble (user/ai)
│   │   ├── ChatInput.tsx             # Message input with send
│   │   ├── ChatHistory.tsx           # Chat session list
│   │   ├── TypingIndicator.tsx       # AI thinking animation
│   │   ├── QuizQuestion.tsx          # Quiz question card
│   │   ├── QuizResult.tsx            # Quiz result display
│   │   ├── TutorSuggestion.tsx       # Tutor hint/reveal
│   │   ├── InterviewPrompt.tsx       # Interview question card
│   │   └── InterviewFeedback.tsx     # Interview feedback display
│   │
│   ├── voice/                        # Voice/TTS components
│   │   ├── VoicePlayer.tsx           # Audio player controls
│   │   ├── VoiceSelector.tsx         # Male/female toggle
│   │   ├── NarrationBar.tsx          # Floating narration bar
│   │   └── VoiceSettings.tsx         # Voice configuration
│   │
│   ├── dashboard/                    # Dashboard components
│   │   ├── StatsCard.tsx             # Metric card
│   │   ├── ProgressRing.tsx          # Circular progress
│   │   ├── ActivityTimeline.tsx      # Recent activity
│   │   ├── ContinueReading.tsx       # Resume reading card
│   │   └── StreakCounter.tsx         # Daily streak display
│   │
│   ├── search/                       # Search components
│   │   ├── SearchInput.tsx           # Search bar
│   │   ├── SearchResults.tsx         # Results list
│   │   ├── SearchResultCard.tsx      # Individual result
│   │   └── SearchFilters.tsx         # Filters panel
│   │
│   ├── admin/                        # Admin components
│   │   ├── DataTable.tsx             # Sortable/filterable table
│   │   ├── MetricCard.tsx            # Admin metric
│   │   ├── Chart.tsx                 # Chart wrapper
│   │   └── UserRow.tsx               # User management row
│   │
│   └── common/                       # Shared components
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       ├── Footer.tsx
│       ├── Loading.tsx
│       ├── EmptyState.tsx
│       ├── ErrorState.tsx
│       └── Skeleton.tsx
│
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### 4.2 Theming Architecture

```css
/* globals.css — design tokens */

@layer base {
  :root {
    /* Light theme (default) */
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --muted: 210 40% 96.1%;
    --accent: 210 40% 96.1%;
    --destructive: 0 84.2% 60.2%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;
    --radius: 0.5rem;

    /* Textbook-specific tokens */
    --text-highlight: 47 95% 85%;
    --code-bg: 210 40% 96%;
    --note-bg: 48 100% 95%;
    --tip-bg: 142 76% 90%;
    --warning-bg: 38 92% 90%;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --muted: 217.2 32.6% 17.5%;
    --accent: 217.2 32.6% 17.5%;
    --destructive: 0 62.8% 30.6%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 224.3 76.3% 48%;

    --text-highlight: 47 95% 20%;
    --code-bg: 217 33% 12%;
    --note-bg: 48 50% 15%;
    --tip-bg: 142 50% 15%;
    --warning-bg: 38 50% 15%;
  }
}
```

---

## 5. Authentication & User State

### 5.1 Auth Flow

```
1. User visits app → Next.js middleware checks cookies
2. No session → redirect to /login
3. User submits credentials
4. Next.js API route proxies to FastAPI
5. FastAPI returns access_token + sets __Host-refresh_token cookie
6. Next.js stores access_token in memory (zustand/context)
7. All subsequent API calls include Bearer token
8. On 401 → middleware triggers refresh via cookie
9. On refresh failure → redirect to /login
```

### 5.2 Auth Provider (Client Component)

```
Providers tree:
  RootLayout
    └── AuthProvider
        ├── Reads initial auth state from cookie/server
        ├── Provides: user, isAuthenticated, login, logout, refresh
        ├── Intercepts 401 responses → auto-refresh
        └── Children: entire app

AuthProvider exposes:
  - user: User | null
  - isAuthenticated: boolean
  - isLoading: boolean
  - login(email, password) → Promise<void>
  - register(email, password, name) → Promise<void>
  - logout() → Promise<void>
  - getAccessToken() → string | null
```

### 5.3 Protected Layout

```typescript
// (dashboard)/layout.tsx
// Server Component
export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Fetch user data server-side for initial state
  // Pass to client-side AuthProvider as initial state
  // This eliminates layout shift on hydration

  const user = await getServerSession(); // calls FastAPI

  return (
    <AuthProvider initialUser={user}>
      <DashboardSidebar />
      <DashboardTopbar />
      <main>{children}</main>
    </AuthProvider>
  );
}
```

---

## 6. Reader Dashboard

### 6.1 Layout & Sections

```
┌──────────────────────────────────────────────────────┐
│  DashboardTopbar                                      │
│  [Search...]                    [Lang ▼] [Voice ▼]   │
│                                     [🌙] [Avatar ▼] │
├──────────┬───────────────────────────────────────────┤
│ Sidebar  │  Main Content                              │
│          │                                            │
│ 📚 All   │  ┌─ Continue Reading ───────────────────┐ │
│ Chapters │  │  Chapter 3: Neural Networks           │ │
│          │  │  45% complete  ████████░░░░░░░░░░░░   │ │
│ Section  │  │  Last read: Section 3.2               │ │
│  1.1     │  └───────────────────────────────────────┘ │
│  1.2     │                                            │
│  2.1     │  ┌─ Your Stats ──────────────────────────┐ │
│  2.2     │  │  📖 12/40   🎯 85%   🔥 7-day streak │ │
│  2.3     │  │  Chapters  Quiz Avg   Days active     │ │
│  3.1     │  └───────────────────────────────────────┘ │
│  3.2     │                                            │
│          │  ┌─ Recent Activity ─────────────────────┐ │
│          │  │  • Completed Quiz: Neural Networks     │ │
│          │  │  • Bookmarked Section 3.2              │ │
│          │  │  • Added note to Section 2.1           │ │
│          │  └───────────────────────────────────────┘ │
│          │                                            │
│          │  ┌─ Quick Actions ───────────────────────┐ │
│          │  │  [AI Chat] [AI Tutor] [New Quiz]      │ │
│          │  └───────────────────────────────────────┘ │
└──────────┴───────────────────────────────────────────┘
```

### 6.2 Dashboard Widgets

| Widget | Data Source | Refresh |
|---|---|---|
| ContinueReading | FastAPI: last_section, progress | 60s |
| StatsCards | FastAPI: chapter_count, avg_score, streak | 300s |
| RecentActivity | FastAPI: activity_log (10 items) | 30s |
| QuickActions | Static | N/A |
| RecommendedChapters | FastAPI: ML-based recommendation | 600s |
| StreakCounter | FastAPI: daily_login | 60s |
| UpcomingQuizzes | FastAPI: quiz schedule | 300s |

### 6.3 Sidebar Navigation

```
Sidebar behavior:
  Desktop:  Always visible (240px-280px), collapsible
  Tablet:   Collapsible, slide-over overlay
  Mobile:   Hidden, hamburger toggle

Sidebar sections:
  📚 All Chapters            → full chapter tree
  ├── 1. Introduction        → expandable
  ├── 2. Machine Learning
  │   ├── 2.1 Overview
  │   ├── 2.2 Supervised
  │   └── 2.3 Unsupervised
  └── 3. Neural Networks

  🔖 Bookmarks              → flat list
  📝 Notes                  → flat list
  📊 Progress               → link to /progress
  ⚙️ Settings               → link to /settings
```

---

## 7. Multi-Language System

### 7.1 Language Matrix

| Locale | Label | Direction | Content Source | TTS Voice |
|---|---|---|---|---|
| `en` | Advanced English | LTR | Source (full technical) | US English (Male/Female) |
| `en-plain` | Plain English | LTR | Simplified translation | US English (Male/Female) |
| `ur` | Urdu | RTL | Full translation | Urdu Pakistan (Male/Female) |
| `ur-rom` | Roman Urdu | LTR | Transliteration | Urdu Pakistan (Male/Female) |

### 7.2 Language Detection & Persistence

```
On first visit:
  1. Check cookie: language_preference
  2. Check localStorage: language_preference
  3. Check Accept-Language header
  4. Check geolocation (Cloudflare CF-IPCountry)
  5. Fallback: en

Persistence:
  Cookie: language_preference={locale}; path=/; max-age=31536000
  localStorage: same

All API calls include header:
  Accept-Language: ur

All SSR pages check cookie and render appropriate content.
```

### 7.3 Docusaurus i18n Integration

```
Docusaurus builds each locale separately.
Next.js serves them via URL pattern:

  /textbook/en/docs/intro   → Docusaurus (English)
  /textbook/en-plain/docs/intro → Docusaurus (Plain English)
  /textbook/ur/docs/intro   → Docusaurus (Urdu)
  /textbook/ur-rom/docs/intro → Docusaurus (Roman Urdu)

Locale switcher (in Docusaurus component):
  - Built-in Docusaurus navbar locale dropdown
  - Customized to show labels: "Advanced English", "Plain English", etc.
  - On switch: navigates to same page in new locale

Locale switcher (in Next.js app):
  - Dropdown in DashboardTopbar
  - On switch: sets cookie + reloads
  - Updates all UI text via next-intl or custom provider
```

### 7.4 UI Translation Strategy

```
Next.js app UI strings are translated via:

  packages/config/i18n/
    en.json
    en-plain.json
    ur.json
    ur-rom.json

  Usage:
    import { t } from "@config/i18n";
    t("dashboard.welcome", { name: user.displayName });

  Key structure:
    dashboard.welcome: "Welcome back, {name}!"
    ai.chat.placeholder: "Ask anything about {chapter}..."
    quiz.start: "Start Quiz"
    voice.female: "Female Voice"
```

---

## 8. Voice System

### 8.1 Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Voice System                            │
│                                                            │
│  Text-to-Speech (TTS) options:                             │
│                                                            │
│  1. Browser Web Speech API (free, offline-capable)         │
│     - Pros: No cost, works offline, low latency            │
│     - Cons: Limited voices, platform-dependent quality     │
│     - Use: Default for short snippets                      │
│                                                            │
│  2. ElevenLabs API (premium, high quality)                 │
│     - Pros: Best quality, natural prosody                  │
│     - Cons: Cost per character, requires internet          │
│     - Use: Primary for textbook narration                  │
│                                                            │
│  3. Azure Cognitive Services (enterprise)                  │
│     - Pros: 400+ voices, 140+ languages, SSML support      │
│     - Cons: Cost, latency                                  │
│     - Use: Fallback for Urdu (better Urdu voices)          │
│                                                            │
│  Decision logic:                                            │
│    IF premium_user AND internet → ElevenLabs                │
│    ELSE IF ur/ur-rom → Azure (better Urdu)                 │
│    ELSE → Web Speech API                                   │
└──────────────────────────────────────────────────────────┘
```

### 8.2 Voice Configuration

```
Voice preferences (stored in cookie + user profile):
  - enabled: boolean
  - provider: "web-speech" | "elevenlabs" | "azure"
  - gender: "male" | "female"
  - speed: 0.5 - 2.0 (default: 1.0)
  - auto-read: boolean (auto-play on page load)
  - highlight: boolean (highlight text as it's read)

Per-locale voice mapping:
  en:       ElevenLabs [Rachel (female), Adam (male)]
  en-plain: ElevenLabs [Rachel (female), Adam (male)]
  ur:       Azure [ur-PK-Uzma (female), ur-PK-Asad (male)]
  ur-rom:   Azure [ur-PK-Uzma (female), ur-PK-Asad (male)]
```

### 8.3 Narration Bar

```
Floating bar at bottom of textbook pages:

  ┌──────────────────────────────────────────────────────────┐
  │  ◀⏪ ⏸ ⏩▶   Section 3.2: Backpropagation              │
  │  ─────●──────────────────────── 12:34 / 45:20          │
  │  [🔊 Female ▼] [1.0x ▼] [Auto] [Highlight On]          │
  └──────────────────────────────────────────────────────────┘

  Controls:
    Play/Pause, Skip Back/Forward, Progress Bar
    Voice selector (Male/Female)
    Speed selector (0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 2.0x)
    Auto-read toggle (auto-advance to next section)
    Highlight toggle (visual text tracking)
    Close/minimize button
```

### 8.4 Audio Generation Pipeline

```
Content → TTS API → Audio file → Cache → Stream to client

  For pre-generated narration:
    1. CI pipeline detects changed MDX files
    2. Extracts text content per section
    3. Calls TTS API (ElevenLabs/Azure) for each locale+voice combination
    4. Saves to docusaurus-content/static/audio/{locale}/{voice}/{section}.mp3
    5. Audio served as static files (CDN-cached)

  For real-time narration:
    1. Client requests TTS for selected text
    2. Next.js API route proxies to TTS provider
    3. Streams audio response back to client
    4. Client buffers and plays

  Cost optimization:
    - Pre-generate all content text (one-time cost)
    - Cache per section in CDN
    - Real-time only for AI-generated responses (chat, tutor)
    - User-configurable to prefer free Web Speech API
```

---

## 9. AI Features

### 9.1 AI Chat

```
Interface:
  ┌─ AiSidebar ────────────────────────────────────┐
  │  💬 New Chat                                    │
  │  ─────────────────────                          │
  │  📌 What is backpropagation? (current)          │
  │  📌 Explain neural networks                     │
  │  📌 Quiz review: chapter 3                     │
  │  + New conversation
  └─────────────────────────────────────────────────┘

  ┌─ Main Chat Area ───────────────────────────────┐
  │                                                  │
  │  ┌──────────────────────────────────────────────┐│
  │  │ System: You're studying Chapter 3 — Neural   ││
  │  │ Networks. Ask anything about this chapter.  ││
  │  └──────────────────────────────────────────────┘│
  │                                                  │
  │  ┌──────────────────────────────────────────────┐│
  │  │ User: Can you explain backpropagation with   ││
  │  │ a simple example?                            ││
  │  └──────────────────────────────────────────────┘│
  │                                                  │
  │  ┌──────────────────────────────────────────────┐│
  │  │ AI: Backpropagation is the algorithm that    ││
  │  │ trains neural networks...                    ││
  │  │                                              ││
  │  │ [Think of it like...] [Show formula]         ││
  │  │ [Practice question] [Voice ▶️]              ││
  │  │                                              ││
  │  │ [View in textbook section 3.2 ↗]            ││
  │  └──────────────────────────────────────────────┘│
  │                                                  │
  │  ┌──────────────────────────────────────────────┐│
  │  │ [Type your question...]             [Send ▶] ││
  │  │ [🎤 Voice input]                             ││
  │  └──────────────────────────────────────────────┘│
  └─────────────────────────────────────────────────┘

Capabilities:
  - Context-aware (knows current chapter/section)
  - Can reference specific sections from textbook
  - Supports voice input (browser speech recognition)
  - Supports voice output (TTS for AI responses)
  - Suggests follow-up questions
  - Can generate practice questions on demand
  - Links directly to relevant textbook sections
  - Supports language switching mid-conversation
```

### 9.2 AI Tutor (Socratic Method)

```
┌─ AiTutor ─────────────────────────────────────────┐
│                                                     │
│  📘 Chapter 3: Neural Networks                     │
│  ─────────────────────────────────────             │
│                                                     │
│  ┌────────────────────────────────────────────────┐ │
│  │ Tutor: Let's understand backpropagation.       │ │
│  │                                                 │ │
│  │ What do you think happens when a neural        │ │
│  │ network makes a wrong prediction?              │ │
│  │                                                 │ │
│  │ [Think about it...]                             │ │
│  │                                                 │ │
│  │ ┌─ Your Answer ──────────────────────────────┐ │ │
│  │ │ It adjusts its weights to reduce the error │ │ │
│  │ └────────────────────────────────────────────┘ │ │
│  │                                                 │ │
│  │ Tutor: Good! Now, how does it know which       │ │
│  │ direction to adjust each weight?               │ │
│  │                                                 │ │
│  │ [Hint: It uses calculus] [Show me] [Skip]     │ │
│  │                                                 │ │
│  │ [Progress: ████████░░ 4/5 questions correct]  │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ Controls ────────────────────────────────────┐ │
│  │  [New Topic] [Change Chapter] [End Session]  │ │
│  │  [Voice: On] [Language: English]              │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘

Socratic Teaching Flow:
  1. Tutor selects a concept from the chapter
  2. Asks guiding questions (not direct answers)
  3. User responds in free text
  4. Tutor evaluates: correct → harder question;
     partially correct → hint; wrong → simpler question
  5. After 5 correct answers → concept mastered
  6. Moves to next concept
  7. Session summary at end (strengths, weaknesses)

Session persistence:
  - Saved as tutor sessions in database
  - Can resume unfinished sessions
  - Progress tracked per concept per chapter
```

### 9.3 AI Quiz

```
┌─ QuizPlayer ──────────────────────────────────────┐
│                                                     │
│  Chapter 3 Quiz — Neural Networks                   │
│  Question 4 of 10                                   │
│  ─────────────────────────────────────             │
│                                                     │
│  ┌────────────────────────────────────────────────┐ │
│  │ What is the role of the activation function    │ │
│  │ in a neural network?                           │ │
│  │                                                 │ │
│  │ ○ To compute the loss function                 │ │
│  │ ● To introduce non-linearity                   │ │
│  │ ○ To initialize weights                        │ │
│  │ ○ To normalize input data                      │ │
│  │                                                 │ │
│  │ ┌─ Explanation ──────────────────────────────┐ │ │
│  │ │ ✅ Correct! Activation functions like ReLU │ │ │
│  │ │ introduce non-linearity, allowing networks │ │ │
│  │ │ to learn complex patterns.                 │ │ │
│  │ │ [📖 Section 3.4 ↗] [🔊 Listen]            │ │ │
│  │ └────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ◀ Previous              [3/10]               Next ▶│
│                                                     │
│  Progress: ████████░░░░░░░░ 4/10                    │
│  Score: 4/4 correct (100%)                          │
└─────────────────────────────────────────────────────┘

Quiz Types:
  Multiple Choice      — 4 options, 1 correct
  Multiple Select      — Select all that apply
  True/False           — With explanation
  Fill in the Blank    — Text input
  Code Output          — Predict the output
  Diagram Label        — Click on correct part
  Matching             — Drag to match pairs
  Ordering             — Arrange in correct order

Quiz Generation:
  - AI generates quiz questions per chapter/section
  - Reviewed by human editors (quality assurance)
  - Difficulty levels: beginner, intermediate, advanced
  - Adaptive: next question difficulty based on previous answer
  - Timed mode available (configurable per quiz)
```

### 9.4 AI Interview

```
┌─ InterviewSession ───────────────────────────────┐
│                                                     │
│  🎯 Technical Interview: Machine Learning           │
│  Level: Intermediate                                │
│  Duration: 15:23 / 30:00                           │
│  ─────────────────────────────────────             │
│                                                     │
│  ┌─ Interviewer ──────────────────────────────────┐ │
│  │ "Explain the bias-variance tradeoff. When      │ │
│  │ would you prioritize low bias over low         │ │
│  │ variance?"                                     │ │
│  │                                                 │ │
│  │ [⏱️ Timer: 02:00 to answer]                    │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ Your Response ───────────────────────────────┐ │
│  │ "The bias-variance tradeoff is...              │ │
│  │ (recording... click stop when done)            │ │
│  │                                                 │ │
│  │ [🎤 Recording...] [■ Stop] [Clear]            │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ AI Feedback ──────────────────────────────────┐ │
│  │ Strengths:                                      │ │
│  │ ✅ Correctly defined bias and variance          │ │
│  │ ✅ Good real-world example                      │ │
│  │                                                  │ │
│  │ Improvements:                                    │ │
│  │ ⚠️ Could mention regularization techniques      │ │
│  │ ⚠️ Answer was 30s over recommended time         │ │
│  │                                                  │ │
│  │ Score: 7/10                                     │ │
│  │ [Next Question ▶] [End Interview]              │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  Progress: █████░░░░░░ 2/8 questions                │
└─────────────────────────────────────────────────────┘

Interview Flow:
  1. User selects topic + difficulty level
  2. AI generates realistic interview questions
  3. User answers via voice (speech-to-text) or text
  4. AI evaluates: accuracy, completeness, clarity, conciseness
  5. Provides detailed feedback + improvement suggestions
  6. Tracks progress across multiple interview sessions
  7. Generates performance report (strengths, weaknesses, trends)

Question types:
  - Conceptual: "Explain X"
  - Applied: "How would you solve Y?"
  - Design: "Design a system for Z"
  - Coding: "Write a function to..."
  - Behavioral: "Tell me about a time when..."
```

### 9.5 AI Implementation Notes

```
All AI features use the same backend AI gateway:

  apps/api/app/ai/
    ├── gateway.py          # Multi-provider router
    ├── agents/             # OpenAI Agents SDK agents
    │   ├── chat_agent.py
    │   ├── tutor_agent.py
    │   ├── quiz_agent.py
    │   └── interview_agent.py
    ├── rag/                # RAG pipeline
    └── schemas/            # Request/response models

Frontend communicates via:
  - REST: Quiz management, session CRUD
  - SSE: Chat streaming, tutor responses
  - WebSocket: Interview (real-time voice + evaluation)

Streaming protocol:
  Client sends POST /api/v1/ai/chat/stream
  Server responds with text/event-stream:
    event: token
    data: {"token": "Back", "index": 0}

    event: token
    data: {"token": "propagation", "index": 1}

    event: source
    data: {"sources": [{"section": "3.2", "relevance": 0.95}]}

    event: done
    data: {"finish_reason": "stop"}
```

---

## 10. Bookmarks, Notes & Progress

### 10.1 Bookmarks

```
Bookmark model (FastAPI):

  bookmark:
    id: UUID (uuid7)
    user_id: UUID → FK users
    section_id: string ("03-neural-networks/02-backpropagation")
    chapter_id: string ("03-neural-networks")
    locale: string ("en")
    title: string ("Section 3.2: Backpropagation")
    snippet: string ("Backpropagation computes gradients...")
    page_url: string ("/textbook/en/docs/03-neural-networks/02-backpropagation")
    created_at: datetime

  Constraints:
    UNIQUE (user_id, section_id, locale)

Bookmark UI (in Docusaurus and Next.js):

  [🔖] button in Docusaurus DocItem header
    - Filled: bookmarked
    - Outline: not bookmarked
    - Optimistic update (instant toggle)

  /bookmarks page in Next.js dashboard:
    - List of all bookmarks grouped by chapter
    - Search within bookmarks
    - Export bookmark list
    - Clear all with confirmation
```

### 10.2 Notes

```
Note model (FastAPI):

  note:
    id: UUID (uuid7)
    user_id: UUID → FK users
    section_id: string ("03-neural-networks/02-backpropagation")
    chapter_id: string ("03-neural-networks")
    locale: string ("en")
    text: string (markdown content, max 10KB)
    selection: string (highlighted text, optional)
    color: string ("yellow" | "green" | "blue" | "pink" | "purple")
    tags: string[] (user-defined, e.g., ["important", "review"])
    created_at: datetime
    updated_at: datetime

Note UI (in Docusaurus):

  Text selection → floating toolbar:
    [🔵 Highlight] [📝 Add Note] [🔖 Bookmark]

  Note sidebar (toggleable):
    ┌─ Notes for this section ──────────────────┐
    │  🟡 Key insight: The gradient tells us    │
    │     which direction to adjust weights     │
    │  🟢 Question: Why ReLU over sigmoid?      │
    │  └────────────────────────────────────────┘

  /notes page in Next.js dashboard:
    - All notes across all chapters
    - Filter by color, tag, chapter
    - Search within notes
    - Export as markdown
```

### 10.3 Progress Tracking

```
Progress model (FastAPI):

  progress:
    user_id: UUID → FK users
    chapter_id: string ("03-neural-networks")
    sections_completed: string[] (["01-overview", "02-backpropagation"])
    quiz_scores: {quiz_id: {score, total, best_score}}
    time_spent_seconds: number
    last_accessed: datetime
    completed: boolean

  streak:
    user_id: UUID → FK users
    current_streak: number
    longest_streak: number
    last_active_date: date

Progress UI:

  Per-section:
    [□ Section 1.1]          → not started
    [◐ Section 1.2]          → in progress
    [● Section 1.3]          → completed
    [●✓ Section 2.1]         → completed + quiz passed

  Chapter progress bar:
    Chapter 3: Neural Networks
    ████████████░░░░░░░░░░ 60% complete
    6/10 sections | Quiz: 85% | 2h 15m spent

  Overall dashboard:
    ┌─ Overall Progress ─────────────────────────┐
    │                                             │
    │          ┌──────────┐                       │
    │          │    30%   │  12 of 40 chapters    │
    │          │  ██████  │                      │
    │          └──────────┘                       │
    │                                             │
    │  📊 By Chapter:                             │
    │  Ch 1: ████████████ 100% ✅                 │
    │  Ch 2: ██████████░░ 80% ✅ Quiz: 90%       │
    │  Ch 3: ██████░░░░░░ 60% 🔄 In progress     │
    │  Ch 4: ░░░░░░░░░░░░  0% ⏳ Not started     │
    │                                             │
    │  🔥 7-day streak (longest: 14 days)        │
    └─────────────────────────────────────────────┘
```

---

## 11. Semantic Search

### 11.1 Search Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Search System                           │
│                                                            │
│  Two-tier search:                                         │
│                                                            │
│  1. Content Search (Docusaurus docs)                       │
│     - Indexer: Algolia DocSearch (free for open source)   │
│                OR Meilisearch (self-hosted, recommended)   │
│     - Indexed: All MDX content, metadata, headings         │
│     - Updated on: Every content deployment                 │
│                                                            │
│  2. Semantic Search (AI-powered, across all content)       │
│     - Backend: Qdrant + pgvector (hybrid RAG)              │
│     - Embeddings: text-embedding-3-small (OpenAI)          │
│     - Reranker: Cohere rerank                             │
│     - Indexed: All textbook sections + user notes          │
│     - Updated on: Content deployment + note creation       │
│                                                            │
│  3. User-Facing Search (unified)                           │
│     - Primary: Meilisearch (fast, typo-tolerant)           │
│     - Fallback: Qdrant semantic (when no exact match)      │
│     - Reranked: Cohere for result quality                  │
└──────────────────────────────────────────────────────────┘
```

### 11.2 Search UI

```
Search bar (in DashboardTopbar, accessible anywhere):

  ┌─ Search─────────────────────────────────────────────────┐
  │  🔍 What is backpropagation?                    [Search] │
  └─────────────────────────────────────────────────────────┘

Search results overlay (or /search results page):

  ┌─ Search Results: "backpropagation" (24 results) ───────┐
  │                                                         │
  │  Filters: [All] [Chapters] [Notes] [Bookmarks]         │
  │  Language: [All] [English] [Plain English] [Urdu]      │
  │                                                         │
  │  ┌─ Result 1 ─────────────────────────────────────────┐ │
  │  │ ★★★★☆ Neural Networks > Backpropagation            │ │
  │  │ "Backpropagation computes the gradient of the      │ │
  │  │ loss function with respect to each weight..."      │ │
  │  │ 📖 Section 3.2 · English · 🔖 2.3k readers        │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                         │
  │  ┌─ Result 2 ─────────────────────────────────────────┐ │
  │  │ ★★★☆☆ Your Note (Chapter 3)                       │ │
  │  │ "Backpropagation = chain rule + gradient descent   │ │
  │  │ applied to neural networks"                        │ │
  │  │ 📝 Your note · Tagged: important · 2 days ago     │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                         │
  │  ┌─ Result 3 ─────────────────────────────────────────┐ │
  │  │ ★★★☆☆ Your Bookmark                                │ │
  │  │ "Section 3.2: Backpropagation Algorithm"           │ │
  │  │ 🔖 Bookmarked 5 days ago                           │ │
  │  └────────────────────────────────────────────────────┘ │
  │                                                         │
  │  [Show more results...]                                 │
  └─────────────────────────────────────────────────────────┘
```

### 11.3 Docusaurus Search Integration

```
Docusaurus uses Algolia DocSearch (or local search plugin):

  docusaurus.config.ts:
    algolia: {
      appId: process.env.ALGOLIA_APP_ID,
      apiKey: process.env.ALGOLIA_API_KEY,
      indexName: "ai-enterprises-textbook",
      contextualSearch: true,
      searchParameters: {
        facetFilters: ["language:${currentLocale}"],
      },
    }

  This powers the Docusaurus-native search bar on textbook pages.

  The Next.js app uses a different (more powerful) search
  implementation that queries both Meilisearch and Qdrant,
  and includes notes, bookmarks, and user-specific results.
```

---

## 12. Dark Mode

### 12.1 Implementation

```
Storage:
  - Cookie: color_scheme={light|dark|system}
  - Server-side: middleware reads cookie, sets class on <html>
  - Client-side: ThemeProvider reads cookie, applies class
  - System preference: listens to matchMedia("(prefers-color-scheme: dark)")

Tailwind classes:
  - All shadcn/ui components use CSS variables (auto-switch)
  - Custom components use dark: prefix
  - No manual class management needed

Theme toggle:
  - Sun/moon icon button in DashboardTopbar
  - Three-state: Light / Dark / System
  - Persisted to cookie + user profile preference
  - Smooth transition via CSS transition on background/color
```

### 12.2 Docusaurus Dark Mode

```
Docusaurus handles dark mode natively via `config.themeConfig.colorMode`.
The Docusaurus theme inherits the same CSS variables as the Next.js app
(via shared Tailwind config), ensuring visual consistency between the
two frameworks.

  docusaurus.config.ts:
    themeConfig: {
      colorMode: {
        defaultMode: "light",
        disableSwitch: false,
        respectPrefersColorScheme: true,
      },
    }
```

---

## 13. Performance & Bundling

### 13.1 Bundle Strategy

```
Next.js bundle optimization:

  - App Router: Automatic code splitting per route
  - React Server Components: Zero client JS for data-fetching components
  - Dynamic imports: AI components (chat, tutor) loaded lazily
  - next/image: Textbook images served via image optimization pipeline
  - next/font: Inter font subset, preloaded

  Target bundle sizes:
    Dashboard page:      < 80 KB JS (first load)
    Textbook (Docusaurus): Static HTML (no JS needed for reading)
    AI Chat page:        < 120 KB JS (incl. streaming client)
    Quiz page:           < 100 KB JS (incl. interactive quiz)
    Interview page:      < 150 KB JS (incl. WebSocket + audio)

Docusaurus bundle optimization:

  - Tree-shake unused components
  - Preload next chapter on idle (intersection observer + <link rel=prefetch>)
  - Lazy-load interactive components (QuizEmbed, AiChatButton)
  - Audio files: Streaming via <audio> element, preload="none"
```

### 13.2 Caching Strategy

```
| Asset | Cache | Strategy |
|---|---|---|
| Docusaurus HTML | CDN (1h), SWR 1d | Static export, per-locale |
| Docusaurus JS/CSS | CDN (1y), immutable | Content-hashed filenames |
| Next.js pages | CDN (1m), SWR 10m | Incremental Static Regeneration |
| API responses | Redis (30s-5m) | Per-endpoint TTL |
| AI responses | Redis (1h) | Keyed on query hash |
| Audio files | CDN (1y) | Pre-generated, content-hashed |
| Images | CDN (1y) | next/image optimization |
| User data | No cache | Private, per-request |
```

### 13.3 Streaming & Loading

```
Loading patterns:

  Pages:            Suspense boundary with Skeleton component
  AI chat:          Streaming tokens via SSE, displayed as received
  Quiz results:     Optimistic UI (show results immediately)
  Bookmarks/Notes:  Optimistic updates (toggle instantly, sync in bg)
  Search results:   Debounced input (300ms), show skeleton on query
  Voice narration:  Stream audio, show buffering indicator

  Error handling:
    - Each feature wrapped in ErrorBoundary
    - Failed AI response → retry button + "AI is having trouble" message
    - Failed auth → silent refresh, then redirect
    - Offline → show cached content + "You're offline" banner
    - Generic error → toast notification, not full page failure
```

---

## 14. Docusaurus Deep Integration

### 14.1 Custom Plugin: AI Integration

```typescript
// docusaurus-content/plugins/ai-integration/index.ts

// This plugin enables Docusaurus pages to communicate with
// the Next.js AI backend by injecting:
//   1. A global script that exposes an AI bridge API
//   2. Custom MDX components for AI features
//   3. Authentication state from shared cookie

module.exports = function aiIntegrationPlugin(context, options) {
  return {
    name: "ai-integration",

    // Inject custom components into MDX scope
    getClientModules() {
      return ["./src/theme/AiComponents"];
    },

    // Inject global script
    injectHtmlTags() {
      return {
        head: [
          {
            tagName: "script",
            attributes: {
              src: `${options.apiUrl}/sdk/ai-bridge.js`,
              async: true,
            },
          },
        ],
        preBodyTags: [
          {
            tagName: "script",
            innerHTML: `
              window.__AI_CONFIG = {
                apiUrl: "${options.apiUrl}",
                locale: "${context.i18n.currentLocale}",
              };
            `,
          },
        ],
      };
    },
  };
};
```

### 14.2 Custom Theme Swizzles

```
Swizzled Docusaurus components:

  DocItem/Layout        → Add bookmark button, voice controls, AI chat trigger
  DocSidebar/Desktop    → Add progress indicators per section
  DocSidebar/Mobile     → Add language switcher quick-access
  Navbar/Search         → Custom search that bridges to Meilisearch
  Navbar/LocaleDropdown → Enhanced with locale labels + icons
  DocItem/Content       → Wrap content for highlight-tracking during voice narration

Each swizzle:
  - Uses Tailwind classes (not Docusaurus CSS modules)
  - References shared-ui components via alias
  - Communicates with Next.js app via postMessage or shared cookie
```

### 14.3 Cross-Framework Communication

```
Docusaurus → Next.js:
  - Click AI Chat button in textbook section
  - Opens Next.js route: /ai/chat?section=neural-networks-3.2
  - Context: chapter, section, locale passed via URL params

Next.js → Docusaurus:
  - "View in textbook" link in AI responses
  - Navigates to /textbook/{locale}/docs/{chapter}/{section}
  - Auto-scrolls to specific anchor

Shared state (via cookie):
  - auth_token
  - language_preference
  - color_scheme
  - voice_preference
```

---

## 15. Admin Dashboard

### 15.1 Admin Layout

```
/admin/
├── page.tsx                    → Overview (metrics, alerts)
├── users/
│   ├── page.tsx                → User list (search, filter, paginate)
│   └── [userId]/
│       └── page.tsx            → User detail (activity, progress)
├── content/
│   ├── page.tsx                → Content analytics (popular, completion)
│   └── chapters/
│       └── page.tsx            → Per-chapter analytics
├── analytics/
│   ├── page.tsx                → Platform metrics
│   ├── engagement/
│   │   └── page.tsx            → User engagement
│   ├── ai/
│   │   └── page.tsx            → AI usage, costs, quality
│   └── voice/
│       └── page.tsx            → TTS usage, costs
├── quizzes/
│   ├── page.tsx                → Quiz performance
│   └── [quizId]/
│       └── page.tsx            → Quiz detail
└── settings/
    └── page.tsx                → Platform settings
```

### 15.2 Admin Metrics

```
Dashboard widgets:

  User Metrics:
    Total users, DAU, MAU, Growth rate
    Users by language, Users by completion
    Active vs inactive ratio

  Content Metrics:
    Most popular chapters
    Chapter completion rates
    Average time per chapter
    Drop-off points (which section users stop)

  AI Metrics:
    Total AI interactions (chat, tutor, quiz, interview)
    Average session duration
    Cost per interaction
    User satisfaction ratings
    Most common questions

  Quiz Metrics:
    Total quizzes taken
    Average score by chapter
    Question difficulty analysis
    Most missed questions

  Voice Metrics:
    Total narration minutes
    Characters synthesized
    Cost per user
    Popularity by gender (male vs female voice)
```

---

## 16. Accessibility

### 16.1 Requirements

```
WCAG 2.2 AA compliance (minimum):

  - Perceivable:
    - All images have alt text
    - Audio transcripts available
    - Color not sole means of conveying information
    - Text contrast ratio ≥ 4.5:1

  - Operable:
    - Full keyboard navigation
    - Focus indicators visible
    - Skip to content link
    - No keyboard traps
    - Voice controls accessible via keyboard

  - Understandable:
    - Clear labels on all form controls
    - Error messages in plain language
    - Consistent navigation
    - Language attribute set on <html>

  - Robust:
    - Semantic HTML (headings, landmarks)
    - ARIA labels where needed
    - Screen reader compatible
```

### 16.2 Specific Features

```
Screen reader support:
  - Reading progress announced: "You are 60% through Chapter 3"
  - Quiz results read automatically
  - AI responses marked as aria-live="polite"
  - Streamed tokens debounced for screen reader (don't read partial words)

Keyboard shortcuts:
  ? → Show shortcut menu
  n → Next section
  p → Previous section
  s → Focus search
  . → Play/pause voice
  b → Toggle bookmarks sidebar
  m → Toggle notes sidebar
  / → Focus chat input
  Esc → Close overlay/sidebar
```

---

## 17. Development & Deployment

### 17.1 Development Workflow

```
pnpm dev                    # Runs both Next.js and Docusaurus in dev mode
pnpm dev:next               # Next.js only (port 3000)
pnpm dev:docusaurus         # Docusaurus only (port 3001)
pnpm lint                   # ESLint across both apps
pnpm typecheck              # TypeScript strict checking
pnpm test                   # Vitest + Playwright
pnpm build                  # Production build of both

Docusaurus dev:
  - Hot reload on MDX changes
  - Locale preview: pnpm dev:docusaurus --locale ur
  - Build all locales: pnpm build:docusaurus:all

Next.js dev:
  - Standard Next.js dev server
  - Rewrites /textbook/* to Docusaurus build output
  - API route proxying to FastAPI
```

### 17.2 Build Pipeline

```
# CI/CD (GitHub Actions)

jobs:
  build-docusaurus:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        locale: [en, en-plain, ur, ur-rom]
    steps:
      - pnpm install
      - pnpm build:docusaurus --locale ${{ matrix.locale }}
      - Upload artifact: docusaurus-${{ matrix.locale }}

  build-nextjs:
    runs-on: ubuntu-latest
    needs: build-docusaurus
    steps:
      - Download all docusaurus locale artifacts
      - Copy to apps/nextjs-app/public/textbook/
      - pnpm build:next
      - Upload artifact: nextjs-build

  deploy:
    runs-on: ubuntu-latest
    needs: build-nextjs
    steps:
      - Download nextjs-build
      - Deploy to Vercel / Docker / Kubernetes
```

### 17.3 Production Configuration

```
Next.js rewrites (next.config.js):

  async rewrites() {
    return [
      {
        source: "/textbook/:locale(en|en-plain|ur|ur-rom)/:path*",
        destination: "/textbook/:locale/:path*",
      },
    ];
  }

  async headers() {
    return [
      {
        source: "/textbook/:path*",
        headers: [
          { key: "Cache-Control", value: "public, max-age=3600, stale-while-revalidate=86400" },
        ],
      },
    ];
  }

Environment variables:
  NEXT_PUBLIC_API_URL:        https://api.ai-enterprises.com
  NEXT_PUBLIC_TEXTBOOK_URL:   /textbook
  ALGOLIA_APP_ID:             ...
  ALGOLIA_SEARCH_KEY:         ...
  MEILISEARCH_URL:            https://search.ai-enterprises.com
  ELEVENLABS_API_KEY:         ...
  AZURE_TTS_KEY:              ...
  AZURE_TTS_REGION:           eastus
```

---

## 18. File & Route Summary

### 18.1 File Count

```
apps/nextjs-app/
  app/                        42 pages (layouts + pages)
  components/                 25 app-specific components
  lib/                        15 utilities, hooks, API clients

  Total: ~82 files

apps/docusaurus-content/
  docs/                       120+ MDX chapter files
  i18n/                       4 locales × 120+ files
  src/components/             15 custom components
  src/theme/                  6 swizzled theme components

  Total: ~600 files

packages/shared-ui/
  src/ui/                     30 shadcn/ui components
  src/textbook/               6 textbook components
  src/ai/                     8 AI feature components
  src/voice/                  4 voice components
  src/dashboard/              5 dashboard components
  src/search/                 4 search components
  src/admin/                  4 admin components
  src/common/                 8 common components

  Total: ~69 files

Grand total: ~750 files
```

### 18.2 Route Map

```
/                           → Landing (redirect to /dashboard or /login)
/login                      → Auth: Login page
/register                   → Auth: Registration
/forgot-password            → Auth: Forgot password
/reset-password             → Auth: Reset password

/dashboard                  → Reader dashboard
/dashboard/progress         → Progress tracking
/dashboard/bookmarks        → Bookmark manager
/dashboard/notes            → Notes manager
/dashboard/settings         → User settings

/textbook/{locale}/docs/*   → Docusaurus textbook content

/ai/chat                    → AI chat (full page)
/ai/tutor                   → AI tutor (Socratic)
/ai/quiz                    → Quiz listing
/ai/quiz/{quizId}           → Quiz player
/ai/interview               → Interview selection
/ai/interview/{sessionId}   → Interview session

/admin                      → Admin dashboard
/admin/users                → User management
/admin/users/{userId}       → User detail
/admin/content              → Content analytics
/admin/analytics            → Platform metrics
/admin/quizzes              → Quiz analytics
/admin/settings             → Platform settings

/.well-known/jwks.json      → JWKS endpoint (via Next.js rewrite)
/health                     → Health check
```

---

## 19. Implementation Phases

```
Phase 1 — Foundation (Week 1-2):
  [x] Monorepo scaffolding (pnpm, TurboRepo, shared configs)
  [x] shared-ui package (Tailwind, shadcn/ui components)
  [x] Next.js 15 App Router setup with layouts
  [x] Docusaurus setup with i18n (4 locales)
  [x] Authentication UI (login, register)
  [x] Dark mode implementation
  [x] Build pipeline (CI/CD)

Phase 2 — Content & Reading (Week 3-4):
  [ ] MDX content authoring (first 5 chapters)
  [ ] Docusaurus custom components (bookmark, voice, embed)
  [ ] Reader dashboard
  [ ] Progress tracking
  [ ] Bookmarks + Notes
  [ ] Docusaurus ↔ Next.js routing integration

Phase 3 — AI Features (Week 5-6):
  [ ] AI Chat UI
  [ ] AI Tutor (Socratic) UI
  [ ] AI Quiz UI + integration
  [ ] Semantic Search UI
  [ ] SSE streaming integration
  [ ] Source citations in AI responses

Phase 4 — Voice & Interview (Week 7-8):
  [ ] Voice player (Web Speech API)
  [ ] ElevenLabs integration
  [ ] Azure TTS for Urdu
  [ ] AI Interview UI
  [ ] Voice input (speech-to-text)
  [ ] Audio pre-generation pipeline

Phase 5 — Admin & Polish (Week 9-10):
  [ ] Admin dashboard
  [ ] Platform analytics
  [ ] AI cost tracking
  [ ] Accessibility audit + fixes
  [ ] Performance optimization
  [ ] E2E tests (Playwright)
  [ ] Load testing
```

---

> **Document Status:** v1.0 — Complete architecture specification  
> **Next Steps:** Phase 1 implementation (shared-ui components setup)