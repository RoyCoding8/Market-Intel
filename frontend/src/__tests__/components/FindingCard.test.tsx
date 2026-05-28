import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FindingCard } from '@/components/FindingCard';
import type { Finding } from '@/types';

const mockFinding: Finding = {
  id: 'finding-1',
  title: "Notion's Pricing Favors Large Teams",
  summary:
    "Notion's per-user pricing model becomes expensive at scale. A 100-person team on the Business plan costs $21,600/year.",
  category: 'pricing',
  confidence: 'high',
  confidence_score: 0.92,
  citations: [
    {
      url: 'https://notion.so/pricing',
      title: 'Notion Pricing Page',
      quote: 'Business plan: $18 per user per month, billed annually',
      accessed_at: '2025-06-15T14:30:00Z',
      confidence: 'high',
    },
    {
      url: 'https://obsidian.md/pricing',
      title: 'Obsidian Pricing Page',
      quote: 'Commercial license: $50 per user per year',
      accessed_at: '2025-06-15T14:30:00Z',
      confidence: 'high',
    },
  ],
  competitor_ids: ['comp-notion', 'comp-obsidian'],
  impact: 'High impact for enterprise procurement decisions',
  recommendation: 'Evaluate total cost of ownership including sync and admin features',
};

describe('FindingCard', () => {
  it('should render finding title', () => {
    render(<FindingCard finding={mockFinding} index={0} />);
    expect(
      screen.getByText("Notion's Pricing Favors Large Teams")
    ).toBeInTheDocument();
  });

  it('should render finding summary', () => {
    render(<FindingCard finding={mockFinding} index={0} />);
    expect(
      screen.getByText(/Notion's per-user pricing model becomes expensive/)
    ).toBeInTheDocument();
  });

  it('should render finding index', () => {
    render(<FindingCard finding={mockFinding} index={4} />);
    expect(screen.getByText('5')).toBeInTheDocument(); // index + 1
  });

  it('should render confidence badge', () => {
    render(<FindingCard finding={mockFinding} index={0} />);
    expect(screen.getByText(/High \(92%\)/)).toBeInTheDocument();
  });

  it('should render category badge', () => {
    render(<FindingCard finding={mockFinding} index={0} />);
    expect(screen.getByText('pricing')).toBeInTheDocument();
  });

  it('should render impact section', () => {
    render(<FindingCard finding={mockFinding} index={0} />);
    expect(screen.getByText('Impact')).toBeInTheDocument();
    expect(
      screen.getByText('High impact for enterprise procurement decisions')
    ).toBeInTheDocument();
  });

  it('should render recommendation section', () => {
    render(<FindingCard finding={mockFinding} index={0} />);
    expect(screen.getByText('Recommendation')).toBeInTheDocument();
    expect(
      screen.getByText(/Evaluate total cost of ownership/)
    ).toBeInTheDocument();
  });

  it('should render citations toggle button', () => {
    render(<FindingCard finding={mockFinding} index={0} />);
    expect(screen.getByText('2 sources')).toBeInTheDocument();
  });

  it('should expand citations when toggle is clicked', async () => {
    const user = userEvent.setup();
    render(<FindingCard finding={mockFinding} index={0} />);

    await user.click(screen.getByText('2 sources'));

    expect(
      screen.getByText(/Business plan: \$18 per user per month/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Commercial license: \$50 per user per year/)
    ).toBeInTheDocument();
  });

  it('should collapse citations when toggle is clicked again', async () => {
    const user = userEvent.setup();
    render(<FindingCard finding={mockFinding} index={0} />);

    // Expand
    await user.click(screen.getByText('2 sources'));
    expect(
      screen.getByText(/Business plan: \$18 per user per month/)
    ).toBeInTheDocument();

    // Collapse
    await user.click(screen.getByText('2 sources'));
    expect(
      screen.queryByText(/Business plan: \$18 per user per month/)
    ).not.toBeInTheDocument();
  });

  it('should render citation source links', async () => {
    const user = userEvent.setup();
    render(<FindingCard finding={mockFinding} index={0} />);

    await user.click(screen.getByText('2 sources'));

    const links = screen.getAllByRole('link');
    expect(links.length).toBeGreaterThanOrEqual(2);
  });

  it('should render citation titles when available', async () => {
    const user = userEvent.setup();
    render(<FindingCard finding={mockFinding} index={0} />);

    await user.click(screen.getByText('2 sources'));

    expect(screen.getByText('Notion Pricing Page')).toBeInTheDocument();
    expect(screen.getByText('Obsidian Pricing Page')).toBeInTheDocument();
  });

  it('should use URL when citation title is not available', async () => {
    const finding: Finding = {
      ...mockFinding,
      citations: [
        {
          url: 'https://example.com/page',
          quote: 'A quote from source',
          accessed_at: '2025-06-15T14:30:00Z',
          confidence: 'high',
        },
      ],
    };

    const user = userEvent.setup();
    render(<FindingCard finding={finding} index={0} />);

    await user.click(screen.getByText('1 source'));

    expect(screen.getByText('https://example.com/page')).toBeInTheDocument();
  });

  it('should not render impact section when impact is not provided', () => {
    const finding: Finding = { ...mockFinding, impact: undefined };
    render(<FindingCard finding={finding} index={0} />);
    expect(screen.queryByText('Impact')).not.toBeInTheDocument();
  });

  it('should not render recommendation section when recommendation is not provided', () => {
    const finding: Finding = { ...mockFinding, recommendation: undefined };
    render(<FindingCard finding={finding} index={0} />);
    expect(screen.queryByText('Recommendation')).not.toBeInTheDocument();
  });

  it('should not render citations toggle when citations are empty', () => {
    const finding: Finding = { ...mockFinding, citations: [] };
    render(<FindingCard finding={finding} index={0} />);
    expect(screen.queryByText(/source/)).not.toBeInTheDocument();
  });

  it('should show singular "source" for 1 citation', () => {
    const finding: Finding = {
      ...mockFinding,
      citations: [mockFinding.citations[0]],
    };
    render(<FindingCard finding={finding} index={0} />);
    expect(screen.getByText('1 source')).toBeInTheDocument();
  });

  it('should render medium confidence badge correctly', () => {
    const finding: Finding = {
      ...mockFinding,
      confidence: 'medium',
      confidence_score: 0.78,
    };
    render(<FindingCard finding={finding} index={0} />);
    expect(screen.getByText(/Medium \(78%\)/)).toBeInTheDocument();
  });

  it('should render low confidence badge correctly', () => {
    const finding: Finding = {
      ...mockFinding,
      confidence: 'low',
      confidence_score: 0.35,
    };
    render(<FindingCard finding={finding} index={0} />);
    expect(screen.getByText(/Low \(35%\)/)).toBeInTheDocument();
  });

  it('should render category with underscores replaced by spaces', () => {
    const finding: Finding = { ...mockFinding, category: 'market_positioning' };
    render(<FindingCard finding={finding} index={0} />);
    expect(screen.getByText('market positioning')).toBeInTheDocument();
  });

  it('should render accessed date for citations', async () => {
    const user = userEvent.setup();
    render(<FindingCard finding={mockFinding} index={0} />);

    await user.click(screen.getByText('2 sources'));

    const accessedElements = screen.getAllByText(/Accessed:/);
    expect(accessedElements.length).toBeGreaterThanOrEqual(1);
  });
});
