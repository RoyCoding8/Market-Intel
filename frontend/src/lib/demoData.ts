/**
 * Demo / pre-populated data for first-load display.
 * Shows a Bright Data-backed Notion vs Obsidian comparison immediately.
 */

import type {
  IntelligenceReport,
  AgentEvent,
  JobStatusResponse,
} from "@/types";

export const DEMO_REPORT: IntelligenceReport = {
  id: "demo-report-001",
  title: "Notion vs Obsidian — Competitive Intelligence Report",
  created_at: new Date().toISOString(),
  total_sources: 32,
  verification_passes: 3,
  executive_summary:
    "This Bright Data-backed report compares Notion and Obsidian across pricing, features, team structure, and market positioning. " +
    "Notion dominates the team collaboration space with a robust API and enterprise features, while Obsidian " +
    "excels in local-first privacy, plugin extensibility, and offline access. Both products have passionate " +
    "communities, but target fundamentally different user personas. Web Unlocker collected pricing, feature, about, and blog pages despite common bot defenses.",
  trend_analysis:
    "The note-taking and knowledge management market is consolidating around two paradigms: cloud-first collaboration " +
    "tools (Notion, Coda, Craft) and local-first privacy-oriented tools (Obsidian, Logseq, Bear). " +
    "AI integration is becoming a key differentiator, with Notion investing heavily in Notion AI while " +
    "Obsidian relies on community plugins for LLM integration.",
  recommendations: [
    "If targeting enterprise teams, adopt Notion-style collaboration features and API-first architecture",
    "If targeting power users and developers, prioritize local-first storage and plugin extensibility like Obsidian",
    "Invest in AI-powered features — this is the fastest-growing differentiator in the space",
    "Consider hybrid storage: local-first with optional cloud sync to capture both market segments",
    "Build an open plugin ecosystem — Obsidian's community plugins are a major competitive moat",
    "Keep Bright Data debug headers in demo logs so procurement and technical buyers can verify live data access",
  ],
  competitors: [
    {
      id: "comp-notion",
      name: "Notion",
      url: "https://notion.so",
      scraped_pages: [],
      pricing: {
        plans: [
          {
            name: "Free",
            price: "$0",
            billing_period: "forever",
            features: ["Unlimited pages for individuals", "10 guest collaborators", "7-day page history"],
            highlighted: false,
          },
          {
            name: "Plus",
            price: "$10",
            billing_period: "per user/month",
            features: ["Unlimited blocks for teams", "Unlimited file uploads", "30-day page history"],
            highlighted: false,
          },
          {
            name: "Business",
            price: "$18",
            billing_period: "per user/month",
            features: ["SAML SSO", "Advanced page analytics", "90-day page history", "Private teamspaces"],
            highlighted: true,
          },
          {
            name: "Enterprise",
            price: "Custom",
            billing_period: "per year",
            features: ["Advanced security", "Audit log", "SCIM provisioning", "Dedicated success manager"],
            highlighted: false,
          },
        ],
        currency: "USD",
        has_free_tier: true,
        enterprise_tier: true,
        source_url: "https://notion.so/pricing",
        scraped_at: new Date().toISOString(),
      },
      features: [
        { name: "Real-time collaboration", description: "Multiple users editing simultaneously", category: "Collaboration", source_url: "https://notion.so" },
        { name: "API & integrations", description: "REST API with official SDKs", category: "Developer", source_url: "https://notion.so/developers" },
        { name: "Notion AI", description: "Built-in AI writing and analysis", category: "AI", source_url: "https://notion.so/ai" },
        { name: "Databases", description: "Relational databases with views", category: "Core", source_url: "https://notion.so" },
        { name: "Templates gallery", description: "Thousands of community templates", category: "Community", source_url: "https://notion.so/templates" },
      ],
      team_info: {
        team_size: "700+",
        key_members: [
          { name: "Ivan Zhao", role: "Co-founder & CEO" },
          { name: "Simon Last", role: "Co-founder" },
        ],
        recent_hires: [],
        source_url: "https://notion.so/about",
      },
      recent_news: [
        {
          title: "Notion launches AI-powered Q&A across all workspace content",
          url: "https://notion.so/blog",
          date: "2025-10-15",
          summary: "Notion AI can now search and answer questions across all workspace pages.",
          source: "Notion Blog",
        },
      ],
      last_updated: new Date().toISOString(),
    },
    {
      id: "comp-obsidian",
      name: "Obsidian",
      url: "https://obsidian.md",
      scraped_pages: [],
      pricing: {
        plans: [
          {
            name: "Personal",
            price: "$0",
            billing_period: "forever",
            features: ["Full app access", "All core plugins", "Community plugins", "Local storage"],
            highlighted: false,
          },
          {
            name: "Commercial",
            price: "$50",
            billing_period: "per user/year",
            features: ["Commercial license", "Priority support", "Sync included"],
            highlighted: false,
          },
          {
            name: "Sync",
            price: "$5",
            billing_period: "per month",
            features: ["End-to-end encrypted sync", "Version history", "5 vaults"],
            highlighted: true,
          },
          {
            name: "Publish",
            price: "$10",
            billing_period: "per month",
            features: ["Publish notes as website", "Custom domain", "Graph view"],
            highlighted: false,
          },
        ],
        currency: "USD",
        has_free_tier: true,
        enterprise_tier: true,
        source_url: "https://obsidian.md/pricing",
        scraped_at: new Date().toISOString(),
      },
      features: [
        { name: "Local-first storage", description: "All data stored as local Markdown files", category: "Core", source_url: "https://obsidian.md" },
        { name: "Plugin ecosystem", description: "1000+ community plugins", category: "Community", source_url: "https://obsidian.md/plugins" },
        { name: "Graph view", description: "Visual knowledge graph of linked notes", category: "Core", source_url: "https://obsidian.md" },
        { name: "Canvas", description: "Visual thinking and spatial note-taking", category: "Core", source_url: "https://obsidian.md" },
        { name: "End-to-end encrypted sync", description: "Privacy-first sync across devices", category: "Sync", source_url: "https://obsidian.md/sync" },
      ],
      team_info: {
        team_size: "20-30",
        key_members: [
          { name: "Shida Li", role: "Co-founder & CEO" },
          { name: "Erica Xu", role: "Co-founder" },
        ],
        recent_hires: [],
        source_url: "https://obsidian.md/about",
      },
      recent_news: [
        {
          title: "Obsidian 1.5 introduces improved performance and new theming engine",
          url: "https://obsidian.md/blog",
          date: "2025-09-20",
          summary: "Major performance improvements and a new CSS-based theming system.",
          source: "Obsidian Blog",
        },
      ],
      last_updated: new Date().toISOString(),
    },
  ],
  findings: [
    {
      id: "finding-001",
      title: "Notion's Pricing Favors Large Teams",
      summary:
        "Notion's per-user pricing model becomes expensive at scale. A 100-person team on the Business plan " +
        "costs $21,600/year. Obsidian's flat $50/user/year commercial license is significantly cheaper for " +
        "organizations that don't need cloud collaboration.",
      category: "pricing",
      confidence: "high",
      confidence_score: 0.92,
      citations: [
        {
          url: "https://notion.so/pricing",
          title: "Notion Pricing Page",
          quote: "Business plan: $18 per user per month, billed annually",
          accessed_at: new Date().toISOString(),
          confidence: "high",
        },
        {
          url: "https://obsidian.md/pricing",
          title: "Obsidian Pricing Page",
          quote: "Commercial license: $50 per user per year",
          accessed_at: new Date().toISOString(),
          confidence: "high",
        },
      ],
      competitor_ids: ["comp-notion", "comp-obsidian"],
      impact: "High impact for enterprise procurement decisions — Notion costs 4.3x more per user annually",
      recommendation: "Evaluate total cost of ownership including sync, API access, and admin features",
    },
    {
      id: "finding-002",
      title: "Obsidian's Plugin Ecosystem Creates Deep Lock-in",
      summary:
        "With 1000+ community plugins, Obsidian users build highly customized workflows that are difficult to " +
        "migrate away from. This creates organic retention that Notion's more controlled extension model cannot match.",
      category: "ecosystem",
      confidence: "high",
      confidence_score: 0.88,
      citations: [
        {
          url: "https://obsidian.md/plugins",
          title: "Obsidian Community Plugins",
          quote: "Browse and install community plugins for Obsidian",
          accessed_at: new Date().toISOString(),
          confidence: "high",
        },
      ],
      competitor_ids: ["comp-obsidian"],
      impact: "High — plugin ecosystem is a major competitive moat",
      recommendation: "If competing with Obsidian, invest early in an open plugin architecture",
    },
    {
      id: "finding-003",
      title: "Notion AI is a Major Differentiator in Enterprise",
      summary:
        "Notion's integrated AI features (summarization, writing assistance, Q&A) are a key selling point for " +
        "enterprise buyers. Obsidian relies on third-party plugins for AI, creating a fragmented experience.",
      category: "features",
      confidence: "medium",
      confidence_score: 0.78,
      citations: [
        {
          url: "https://notion.so/ai",
          title: "Notion AI",
          quote: "AI-powered writing, analysis, and Q&A across your workspace",
          accessed_at: new Date().toISOString(),
          confidence: "high",
        },
      ],
      competitor_ids: ["comp-notion", "comp-obsidian"],
      impact: "Medium — AI is table stakes for enterprise tools in 2025+",
      recommendation: "Build native AI features rather than relying on plugin ecosystem",
    },
    {
      id: "finding-004",
      title: "Local-First Privacy Resonates with Technical Users",
      summary:
        "Obsidian's local-first, Markdown-based approach appeals strongly to developers and privacy-conscious " +
        "users. This segment values data ownership and portability over cloud convenience.",
      category: "market_positioning",
      confidence: "high",
      confidence_score: 0.91,
      citations: [
        {
          url: "https://obsidian.md",
          title: "Obsidian Homepage",
          quote: "Obsidian is the private and flexible writing app that adapts to the way you think",
          accessed_at: new Date().toISOString(),
          confidence: "high",
        },
      ],
      competitor_ids: ["comp-obsidian"],
      impact: "Medium — addresses a specific but passionate market segment",
      recommendation: "Consider offering local-first as an option alongside cloud sync",
    },
    {
      id: "finding-005",
      title: "Notion's API Enables Workflow Automation at Scale",
      summary:
        "Notion's REST API allows deep integration with external tools (Zapier, Make, custom scripts). This " +
        "is critical for enterprise teams that need to automate knowledge management workflows.",
      category: "developer_experience",
      confidence: "high",
      confidence_score: 0.85,
      citations: [
        {
          url: "https://notion.so/developers",
          title: "Notion Developers",
          quote: "Connect Notion to your tools with our REST API",
          accessed_at: new Date().toISOString(),
          confidence: "high",
        },
      ],
      competitor_ids: ["comp-notion"],
      impact: "High for enterprise — API access enables custom integrations",
      recommendation: "API-first architecture is essential for enterprise knowledge management tools",
    },
  ],
  comparison_tables: [
    {
      title: "Pricing Comparison",
      dimensions: ["Free tier", "Individual plan", "Team plan (per user/yr)", "Enterprise", "Sync cost"],
      rows: [
        { dimension: "Free tier", values: { "comp-notion": "Yes (limited)", "comp-obsidian": "Yes (full app)" }, winner: "comp-obsidian" },
        { dimension: "Individual plan", values: { "comp-notion": "$10/mo", "comp-obsidian": "$0" }, winner: "comp-obsidian" },
        { dimension: "Team plan (per user/yr)", values: { "comp-notion": "$216", "comp-obsidian": "$50" }, winner: "comp-obsidian" },
        { dimension: "Enterprise", values: { "comp-notion": "Custom pricing", "comp-obsidian": "$50/user/yr" }, winner: "comp-obsidian" },
        { dimension: "Sync cost", values: { "comp-notion": "Included", "comp-obsidian": "$5/mo additional" }, winner: "comp-notion" },
      ],
      competitor_ids: ["comp-notion", "comp-obsidian"],
    },
    {
      title: "Feature Comparison",
      dimensions: ["Real-time collab", "API access", "AI features", "Offline mode", "Plugin ecosystem", "Data format"],
      rows: [
        { dimension: "Real-time collab", values: { "comp-notion": "Yes", "comp-obsidian": "No (limited via plugins)" }, winner: "comp-notion" },
        { dimension: "API access", values: { "comp-notion": "REST API + SDKs", "comp-obsidian": "Plugin-based" }, winner: "comp-notion" },
        { dimension: "AI features", values: { "comp-notion": "Built-in (Notion AI)", "comp-obsidian": "Community plugins" }, winner: "comp-notion" },
        { dimension: "Offline mode", values: { "comp-notion": "Limited", "comp-obsidian": "Full offline" }, winner: "comp-obsidian" },
        { dimension: "Plugin ecosystem", values: { "comp-notion": "Limited (integrations)", "comp-obsidian": "1000+ plugins" }, winner: "comp-obsidian" },
        { dimension: "Data format", values: { "comp-notion": "Proprietary", "comp-obsidian": "Markdown files" }, winner: "comp-obsidian" },
      ],
      competitor_ids: ["comp-notion", "comp-obsidian"],
    },
  ],
};

export const DEMO_EVENTS: AgentEvent[] = [
  {
    event_id: "evt-001",
    event_type: "job.started",
    job_id: "demo-job-001",
    agent_name: "orchestrator",
    timestamp: new Date(Date.now() - 120000).toISOString(),
    message: "Starting Bright Data-backed intelligence analysis for Notion vs Obsidian",
  },
  {
    event_id: "evt-002",
    event_type: "step.started",
    job_id: "demo-job-001",
    agent_name: "scraper",
    timestamp: new Date(Date.now() - 110000).toISOString(),
    message: "Routing scraper through Bright Data Web Unlocker...",
    data: { scrape_provider: "bright_data_web_unlocker", bright_data_enabled: "true" },
  },
  {
    event_id: "evt-003",
    event_type: "page.scraped",
    job_id: "demo-job-001",
    agent_name: "scraper",
    timestamp: new Date(Date.now() - 100000).toISOString(),
    message: "Bright Data unlocked and scraped: notion.so/pricing",
    data: {
      url: "https://notion.so/pricing",
      page_type: "pricing",
      scrape_provider: "bright_data_web_unlocker",
      bright_data_enabled: "true",
    },
  },
  {
    event_id: "evt-004",
    event_type: "page.scraped",
    job_id: "demo-job-001",
    agent_name: "scraper",
    timestamp: new Date(Date.now() - 95000).toISOString(),
    message: "Bright Data unlocked and scraped: obsidian.md/pricing",
    data: {
      url: "https://obsidian.md/pricing",
      page_type: "pricing",
      scrape_provider: "bright_data_web_unlocker",
      bright_data_enabled: "true",
    },
  },
  {
    event_id: "evt-004a",
    event_type: "page.scraped",
    job_id: "demo-job-001",
    agent_name: "scraper",
    timestamp: new Date(Date.now() - 92000).toISOString(),
    message: "Bright Data crawled: notion.so/product",
    data: {
      url: "https://notion.so/product",
      page_type: "features",
      scrape_provider: "bright_data_web_unlocker",
      bright_data_enabled: "true",
    },
  },
  {
    event_id: "evt-004b",
    event_type: "page.scraped",
    job_id: "demo-job-001",
    agent_name: "scraper",
    timestamp: new Date(Date.now() - 90000).toISOString(),
    message: "Bright Data crawled: notion.so/about",
    data: {
      url: "https://notion.so/about",
      page_type: "about",
      scrape_provider: "bright_data_web_unlocker",
      bright_data_enabled: "true",
    },
  },
  {
    event_id: "evt-004c",
    event_type: "page.scraped",
    job_id: "demo-job-001",
    agent_name: "scraper",
    timestamp: new Date(Date.now() - 88000).toISOString(),
    message: "Bright Data crawled: obsidian.md/sync",
    data: {
      url: "https://obsidian.md/sync",
      page_type: "features",
      scrape_provider: "bright_data_web_unlocker",
      bright_data_enabled: "true",
    },
  },
  {
    event_id: "evt-004d",
    event_type: "page.scraped",
    job_id: "demo-job-001",
    agent_name: "scraper",
    timestamp: new Date(Date.now() - 86000).toISOString(),
    message: "Bright Data crawled: obsidian.md/blog",
    data: {
      url: "https://obsidian.md/blog",
      page_type: "blog",
      scrape_provider: "bright_data_web_unlocker",
      bright_data_enabled: "true",
    },
  },
  {
    event_id: "evt-005",
    event_type: "step.completed",
    job_id: "demo-job-001",
    agent_name: "scraper",
    timestamp: new Date(Date.now() - 80000).toISOString(),
    message: "Scraping complete — 12 pages collected via Bright Data Web Unlocker",
    data: { pages_scraped: 12, bright_data_pages: 12, anti_bot_bypass: "cloudflare/captcha-ready" },
  },
  {
    event_id: "evt-006",
    event_type: "step.started",
    job_id: "demo-job-001",
    agent_name: "analyzer",
    timestamp: new Date(Date.now() - 75000).toISOString(),
    message: "Analyzing Bright Data pages with Xiaomi Mimo 2.5 Pro...",
  },
  {
    event_id: "evt-007",
    event_type: "finding.found",
    job_id: "demo-job-001",
    agent_name: "analyzer",
    timestamp: new Date(Date.now() - 60000).toISOString(),
    message: "Found: Notion's Pricing Favors Large Teams",
    data: { finding_id: "finding-001", category: "pricing" },
  },
  {
    event_id: "evt-008",
    event_type: "finding.found",
    job_id: "demo-job-001",
    agent_name: "analyzer",
    timestamp: new Date(Date.now() - 55000).toISOString(),
    message: "Found: Obsidian's Plugin Ecosystem Creates Deep Lock-in",
    data: { finding_id: "finding-002", category: "ecosystem" },
  },
  {
    event_id: "evt-009",
    event_type: "comparison.generated",
    job_id: "demo-job-001",
    agent_name: "analyzer",
    timestamp: new Date(Date.now() - 40000).toISOString(),
    message: "Generated comparison table: Pricing Comparison",
  },
  {
    event_id: "evt-010",
    event_type: "step.started",
    job_id: "demo-job-001",
    agent_name: "verifier",
    timestamp: new Date(Date.now() - 35000).toISOString(),
    message: "Running verification passes...",
  },
  {
    event_id: "evt-011",
    event_type: "claim.verified",
    job_id: "demo-job-001",
    agent_name: "verifier",
    timestamp: new Date(Date.now() - 25000).toISOString(),
    message: "Verified: Pricing comparison claims (confidence: 0.92)",
  },
  {
    event_id: "evt-012",
    event_type: "verification.complete",
    job_id: "demo-job-001",
    agent_name: "verifier",
    timestamp: new Date(Date.now() - 15000).toISOString(),
    message: "Verification complete — 5/5 findings verified across pricing, features, about, and blog pages",
  },
  {
    event_id: "evt-013",
    event_type: "step.started",
    job_id: "demo-job-001",
    agent_name: "reporter",
    timestamp: new Date(Date.now() - 10000).toISOString(),
    message: "Generating final report...",
  },
  {
    event_id: "evt-014",
    event_type: "report.generated",
    job_id: "demo-job-001",
    agent_name: "reporter",
    timestamp: new Date(Date.now() - 5000).toISOString(),
    message: "Report generated successfully",
  },
  {
    event_id: "evt-015",
    event_type: "job.completed",
    job_id: "demo-job-001",
    agent_name: "orchestrator",
    timestamp: new Date().toISOString(),
    message: "Analysis complete — 5 findings, 2 comparison tables, 32 Bright Data sources verified",
  },
];

export const DEMO_JOB_STATUS: JobStatusResponse = {
  job_id: "demo-job-001",
  status: "completed",
  progress: 1.0,
  current_step: "completed",
  competitors_found: 2,
  pages_scraped: 12,
  findings_count: 5,
  started_at: new Date(Date.now() - 120000).toISOString(),
  completed_at: new Date().toISOString(),
};

export const DEMO_JOBS: JobStatusResponse[] = [
  DEMO_JOB_STATUS,
  {
    job_id: "demo-job-002",
    status: "completed",
    progress: 1.0,
    current_step: "completed",
    competitors_found: 3,
    pages_scraped: 15,
    findings_count: 8,
    started_at: new Date(Date.now() - 86400000).toISOString(),
    completed_at: new Date(Date.now() - 86300000).toISOString(),
  },
  {
    job_id: "demo-job-003",
    status: "failed",
    progress: 0.45,
    current_step: "analyzing",
    competitors_found: 2,
    pages_scraped: 6,
    findings_count: 2,
    started_at: new Date(Date.now() - 172800000).toISOString(),
    completed_at: new Date(Date.now() - 172700000).toISOString(),
    error: "LLM API rate limit exceeded after 3 retries",
  },
];
