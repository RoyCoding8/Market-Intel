import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReportView } from '@/components/ReportView';
import type { IntelligenceReport } from '@/types';

const mockReport: IntelligenceReport = {
  id: 'report-1',
  title: 'Test Intelligence Report',
  created_at: '2025-06-15T14:30:00Z',
  competitors: [
    {
      id: 'comp-1',
      name: 'Notion',
      url: 'https://notion.so',
      scraped_pages: [],
      features: [],
      recent_news: [],
      last_updated: '2025-06-15T14:30:00Z',
    },
    {
      id: 'comp-2',
      name: 'Obsidian',
      url: 'https://obsidian.md',
      scraped_pages: [],
      features: [],
      recent_news: [],
      last_updated: '2025-06-15T14:30:00Z',
    },
  ],
  findings: [
    {
      id: 'finding-1',
      title: 'Pricing Advantage',
      summary: 'Notion is more expensive at scale.',
      category: 'pricing',
      confidence: 'high',
      confidence_score: 0.92,
      citations: [
        {
          url: 'https://notion.so/pricing',
          title: 'Notion Pricing',
          quote: '$18 per user per month',
          accessed_at: '2025-06-15T14:30:00Z',
          confidence: 'high',
        },
      ],
      competitor_ids: ['comp-1', 'comp-2'],
      impact: 'High impact for enterprise procurement',
      recommendation: 'Evaluate total cost of ownership',
    },
    {
      id: 'finding-2',
      title: 'Plugin Ecosystem',
      summary: 'Obsidian has 1000+ plugins creating lock-in.',
      category: 'ecosystem',
      confidence: 'high',
      confidence_score: 0.88,
      citations: [],
      competitor_ids: ['comp-2'],
    },
    {
      id: 'finding-3',
      title: 'AI Features',
      summary: 'Notion AI is a major differentiator.',
      category: 'features',
      confidence: 'medium',
      confidence_score: 0.78,
      citations: [],
      competitor_ids: ['comp-1'],
    },
  ],
  comparison_tables: [
    {
      title: 'Pricing Comparison',
      dimensions: ['Free tier', 'Team plan'],
      rows: [
        { dimension: 'Free tier', values: { 'comp-1': 'Yes', 'comp-2': 'Yes' }, winner: 'comp-2' },
        { dimension: 'Team plan', values: { 'comp-1': '$216/yr', 'comp-2': '$50/yr' }, winner: 'comp-2' },
      ],
      competitor_ids: ['comp-1', 'comp-2'],
    },
  ],
  executive_summary:
    'This report compares Notion and Obsidian across pricing, features, and market positioning.',
  trend_analysis: 'The note-taking market is consolidating around two paradigms.',
  recommendations: [
    'Adopt Notion-style collaboration features',
    'Prioritize local-first storage like Obsidian',
    'Invest in AI-powered features',
  ],
  total_sources: 24,
  verification_passes: 3,
};

describe('ReportView', () => {
  it('should render report title', () => {
    render(<ReportView report={mockReport} />);
    expect(screen.getByText('Test Intelligence Report')).toBeInTheDocument();
  });

  it('should render executive summary in overview tab', () => {
    render(<ReportView report={mockReport} />);
    expect(screen.getByText('Executive Summary')).toBeInTheDocument();
    expect(
      screen.getByText(/This report compares Notion and Obsidian/)
    ).toBeInTheDocument();
  });

  it('should render trend analysis', () => {
    render(<ReportView report={mockReport} />);
    expect(screen.getByText('Trend Analysis')).toBeInTheDocument();
    expect(
      screen.getByText(/The note-taking market is consolidating/)
    ).toBeInTheDocument();
  });

  it('should render stat badges (competitors, findings, sources, verifications)', () => {
    render(<ReportView report={mockReport} />);
    expect(screen.getByText('Competitors')).toBeInTheDocument();
    expect(screen.getByText('Findings')).toBeInTheDocument();
    expect(screen.getByText('Sources')).toBeInTheDocument();
    expect(screen.getByText('Verification Passes')).toBeInTheDocument();
  });

  it('should render stat values', () => {
    render(<ReportView report={mockReport} />);
    // total_sources is unique - only appears in stat badge
    expect(screen.getByText('24')).toBeInTheDocument(); // total_sources
    // "3" appears both as verification_passes stat and in tab label "Findings (3)"
    // Use getAllByText to verify it exists
    const threes = screen.getAllByText('3');
    expect(threes.length).toBeGreaterThanOrEqual(1);
    // "2" appears as competitors count and potentially in comparison tab label
    const twos = screen.getAllByText('2');
    expect(twos.length).toBeGreaterThanOrEqual(1);
  });

  it('should render tabs for Overview, Findings, Comparison, Recommendations', () => {
    render(<ReportView report={mockReport} />);
    const tabs = screen.getAllByRole('tab');
    const tabTexts = tabs.map((t) => t.textContent);
    expect(tabTexts.some((t) => t?.includes('Overview'))).toBe(true);
    expect(tabTexts.some((t) => t?.includes('Findings'))).toBe(true);
    expect(tabTexts.some((t) => t?.includes('Comparison'))).toBe(true);
    expect(tabTexts.some((t) => t?.includes('Recommendations'))).toBe(true);
  });

  it('should render findings tab content when clicked', async () => {
    const user = userEvent.setup();
    render(<ReportView report={mockReport} />);

    const findingsTab = screen.getAllByRole('tab').find((t) =>
      t.textContent?.includes('Findings')
    );
    await user.click(findingsTab!);

    expect(screen.getByText('Pricing Advantage')).toBeInTheDocument();
    expect(screen.getByText('Plugin Ecosystem')).toBeInTheDocument();
    expect(screen.getByText('AI Features')).toBeInTheDocument();
  });

  it('should render comparison table when comparison tab clicked', async () => {
    const user = userEvent.setup();
    render(<ReportView report={mockReport} />);

    const comparisonTab = screen.getAllByRole('tab').find((t) =>
      t.textContent?.includes('Comparison')
    );
    await user.click(comparisonTab!);

    expect(screen.getByText('Pricing Comparison')).toBeInTheDocument();
  });

  it('should render recommendations when recommendations tab clicked', async () => {
    const user = userEvent.setup();
    render(<ReportView report={mockReport} />);

    const recsTab = screen.getAllByRole('tab').find((t) =>
      t.textContent?.includes('Recommendations')
    );
    await user.click(recsTab!);

    expect(
      screen.getByText('Adopt Notion-style collaboration features')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Prioritize local-first storage like Obsidian')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Invest in AI-powered features')
    ).toBeInTheDocument();
  });

  it('should render category filter buttons on findings tab', async () => {
    const user = userEvent.setup();
    render(<ReportView report={mockReport} />);

    const findingsTab = screen.getAllByRole('tab').find((t) =>
      t.textContent?.includes('Findings')
    );
    await user.click(findingsTab!);

    // Should have "All" button and category buttons
    expect(screen.getByText(/All \(3\)/)).toBeInTheDocument();
    expect(screen.getByText(/pricing \(1\)/)).toBeInTheDocument();
    expect(screen.getByText(/ecosystem \(1\)/)).toBeInTheDocument();
    expect(screen.getByText(/features \(1\)/)).toBeInTheDocument();
  });

  it('should filter findings by category', async () => {
    const user = userEvent.setup();
    render(<ReportView report={mockReport} />);

    const findingsTab = screen.getAllByRole('tab').find((t) =>
      t.textContent?.includes('Findings')
    );
    await user.click(findingsTab!);

    // Click pricing filter
    await user.click(screen.getByText(/pricing \(1\)/));

    expect(screen.getByText('Pricing Advantage')).toBeInTheDocument();
    expect(screen.queryByText('Plugin Ecosystem')).not.toBeInTheDocument();
    expect(screen.queryByText('AI Features')).not.toBeInTheDocument();
  });

  it('should show all findings when "All" is selected', async () => {
    const user = userEvent.setup();
    render(<ReportView report={mockReport} />);

    const findingsTab = screen.getAllByRole('tab').find((t) =>
      t.textContent?.includes('Findings')
    );
    await user.click(findingsTab!);

    // Click All
    await user.click(screen.getByText(/All \(3\)/));

    expect(screen.getByText('Pricing Advantage')).toBeInTheDocument();
    expect(screen.getByText('Plugin Ecosystem')).toBeInTheDocument();
    expect(screen.getByText('AI Features')).toBeInTheDocument();
  });

  it('should render ExportButton when jobId is provided', () => {
    render(<ReportView report={mockReport} jobId="job-123" />);
    expect(screen.getByText('Export')).toBeInTheDocument();
  });

  it('should not render ExportButton when jobId is not provided', () => {
    render(<ReportView report={mockReport} />);
    expect(screen.queryByText('Export')).not.toBeInTheDocument();
  });

  it('should render "No findings" message when findings are empty', async () => {
    const emptyReport = { ...mockReport, findings: [] };
    const user = userEvent.setup();
    render(<ReportView report={emptyReport} />);

    const findingsTab = screen.getAllByRole('tab').find((t) =>
      t.textContent?.includes('Findings')
    );
    await user.click(findingsTab!);

    expect(screen.getByText('No findings in this category.')).toBeInTheDocument();
  });

  it('should render "No comparison tables" when empty', async () => {
    const emptyReport = { ...mockReport, comparison_tables: [] };
    const user = userEvent.setup();
    render(<ReportView report={emptyReport} />);

    await user.click(screen.getByText(/Comparison/));

    expect(screen.getByText('No comparison tables available.')).toBeInTheDocument();
  });

  it('should render "No recommendations" when empty', async () => {
    const emptyReport = { ...mockReport, recommendations: [] };
    const user = userEvent.setup();
    render(<ReportView report={emptyReport} />);

    await user.click(screen.getByText(/Recommendations/));

    expect(screen.getByText('No recommendations available.')).toBeInTheDocument();
  });

  it('should render generated date', () => {
    render(<ReportView report={mockReport} />);
    expect(screen.getByText(/Generated/)).toBeInTheDocument();
  });
});
