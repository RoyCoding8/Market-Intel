import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { StatsCards } from '@/components/StatsCards';

vi.mock('@/lib/api', () => ({
  getStats: vi.fn(),
}));

import { getStats } from '@/lib/api';
const mockGetStats = vi.mocked(getStats);

describe('StatsCards', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render loading skeletons initially', () => {
    mockGetStats.mockImplementation(() => new Promise(() => {})); // Never resolves

    const { container } = render(<StatsCards />);

    // During loading, StatCard renders Skeleton components (not text labels)
    // Verify skeleton elements are present
    const skeletons = container.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);

    // Verify we have 4 stat cards in the grid
    const cards = container.querySelectorAll('[class*="grid"] > div');
    expect(cards.length).toBe(4);
  });

  it('should render stats with data when loaded', async () => {
    mockGetStats.mockResolvedValue({
      total_jobs: 12,
      completed_jobs: 9,
      failed_jobs: 2,
      total_findings: 47,
      high_confidence_findings: 31,
      total_competitors_tracked: 8,
      total_pages_scraped: 156,
      total_verifications: 12,
      average_confidence_score: 0.84,
      jobs_last_7_days: 5,
      findings_by_category: {},
      top_competitors: [],
    });

    render(<StatsCards />);

    await waitFor(() => {
      expect(screen.getByText('12')).toBeInTheDocument(); // total_jobs
      expect(screen.getByText('47')).toBeInTheDocument(); // total_findings
      expect(screen.getByText('8')).toBeInTheDocument(); // total_competitors_tracked
      expect(screen.getByText('84%')).toBeInTheDocument(); // average_confidence
    });
  });

  it('should format numbers with commas', async () => {
    mockGetStats.mockResolvedValue({
      total_jobs: 1234,
      completed_jobs: 900,
      failed_jobs: 200,
      total_findings: 5678,
      high_confidence_findings: 3100,
      total_competitors_tracked: 80,
      total_pages_scraped: 15600,
      total_verifications: 120,
      average_confidence_score: 0.84,
      jobs_last_7_days: 50,
      findings_by_category: {},
      top_competitors: [],
    });

    render(<StatsCards />);

    await waitFor(() => {
      expect(screen.getByText('1,234')).toBeInTheDocument();
      expect(screen.getByText('5,678')).toBeInTheDocument();
    });
  });

  it('should show demo fallback values when API fails', async () => {
    mockGetStats.mockRejectedValue(new Error('Network error'));

    render(<StatsCards />);

    await waitFor(() => {
      // Demo fallback values
      expect(screen.getByText('12')).toBeInTheDocument(); // demo total_jobs
      expect(screen.getByText('47')).toBeInTheDocument(); // demo total_findings
    });
  });

  it('should render trend indicators', async () => {
    mockGetStats.mockResolvedValue({
      total_jobs: 10,
      completed_jobs: 8,
      failed_jobs: 2,
      total_findings: 30,
      high_confidence_findings: 20,
      total_competitors_tracked: 5,
      total_pages_scraped: 100,
      total_verifications: 10,
      average_confidence_score: 0.8,
      jobs_last_7_days: 3,
      findings_by_category: {},
      top_competitors: [],
    });

    render(<StatsCards />);

    await waitFor(() => {
      expect(screen.getByText('+12% this week')).toBeInTheDocument();
      expect(screen.getByText('+8% this week')).toBeInTheDocument();
      expect(screen.getByText('+3% this week')).toBeInTheDocument();
      expect(screen.getByText('+2% this week')).toBeInTheDocument();
    });
  });

  it('should render four stat cards', async () => {
    mockGetStats.mockResolvedValue({
      total_jobs: 0,
      completed_jobs: 0,
      failed_jobs: 0,
      total_findings: 0,
      high_confidence_findings: 0,
      total_competitors_tracked: 0,
      total_pages_scraped: 0,
      total_verifications: 0,
      average_confidence_score: 0,
      jobs_last_7_days: 0,
      findings_by_category: {},
      top_competitors: [],
    });

    render(<StatsCards />);

    await waitFor(() => {
      expect(screen.getByText('Total Jobs')).toBeInTheDocument();
      expect(screen.getByText('Findings')).toBeInTheDocument();
      expect(screen.getByText('Competitors Tracked')).toBeInTheDocument();
      expect(screen.getByText('Avg Confidence')).toBeInTheDocument();
    });
  });

  it('should format confidence as percentage', async () => {
    mockGetStats.mockResolvedValue({
      total_jobs: 0,
      completed_jobs: 0,
      failed_jobs: 0,
      total_findings: 0,
      high_confidence_findings: 0,
      total_competitors_tracked: 0,
      total_pages_scraped: 0,
      total_verifications: 0,
      average_confidence_score: 0.915,
      jobs_last_7_days: 0,
      findings_by_category: {},
      top_competitors: [],
    });

    render(<StatsCards />);

    await waitFor(() => {
      expect(screen.getByText('92%')).toBeInTheDocument(); // 0.915 * 100 = 91.5 -> 92
    });
  });
});
