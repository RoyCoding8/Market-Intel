import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProgressConsole } from '@/components/ProgressConsole';
import type { AgentEvent, JobStatusResponse } from '@/types';

describe('ProgressConsole', () => {
  it('should render empty state with skeleton loading', () => {
    render(
      <ProgressConsole events={[]} jobStatus={null} isDemoMode={false} />
    );
    expect(screen.getByText('Agent Console')).toBeInTheDocument();
  });

  it('should render "Demo" badge in demo mode', () => {
    render(
      <ProgressConsole events={[]} jobStatus={null} isDemoMode={true} />
    );
    expect(screen.getByText('Demo')).toBeInTheDocument();
  });

  it('should not render "Demo" badge when not in demo mode', () => {
    render(
      <ProgressConsole events={[]} jobStatus={null} isDemoMode={false} />
    );
    expect(screen.queryByText('Demo')).not.toBeInTheDocument();
  });

  it('should render events from store', () => {
    const events: AgentEvent[] = [
      {
        event_id: 'evt-1',
        event_type: 'job.started',
        job_id: 'job-1',
        agent_name: 'orchestrator',
        timestamp: new Date().toISOString(),
        message: 'Job started',
      },
      {
        event_id: 'evt-2',
        event_type: 'step.started',
        job_id: 'job-1',
        agent_name: 'scraper',
        timestamp: new Date().toISOString(),
        message: 'Scraping started',
      },
    ];

    render(
      <ProgressConsole events={events} jobStatus={null} isDemoMode={false} />
    );

    expect(screen.getByText('Job started')).toBeInTheDocument();
    expect(screen.getByText('Scraping started')).toBeInTheDocument();
  });

  it('should render progress bar', () => {
    const status: JobStatusResponse = {
      job_id: 'job-1',
      status: 'scraping',
      progress: 0.5,
      competitors_found: 2,
      pages_scraped: 4,
      findings_count: 0,
    };

    render(
      <ProgressConsole events={[]} jobStatus={status} isDemoMode={false} />
    );

    const progressbar = screen.getByRole('progressbar');
    expect(progressbar).toBeInTheDocument();
  });

  it('should render stats footer when job status is present', () => {
    const status: JobStatusResponse = {
      job_id: 'job-1',
      status: 'scraping',
      progress: 0.5,
      competitors_found: 3,
      pages_scraped: 12,
      findings_count: 5,
    };

    render(
      <ProgressConsole events={[]} jobStatus={status} isDemoMode={false} />
    );

    expect(screen.getByText('3')).toBeInTheDocument(); // competitors
    expect(screen.getByText('12')).toBeInTheDocument(); // pages scraped
    expect(screen.getByText('5')).toBeInTheDocument(); // findings
  });

  it('should render cancel button when job is running and onCancel is provided', () => {
    const status: JobStatusResponse = {
      job_id: 'job-1',
      status: 'scraping',
      progress: 0.5,
      competitors_found: 2,
      pages_scraped: 4,
      findings_count: 0,
    };

    render(
      <ProgressConsole
        events={[]}
        jobStatus={status}
        isDemoMode={false}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('should not render cancel button when job is completed', () => {
    const status: JobStatusResponse = {
      job_id: 'job-1',
      status: 'completed',
      progress: 1.0,
      competitors_found: 2,
      pages_scraped: 8,
      findings_count: 5,
    };

    render(
      <ProgressConsole
        events={[]}
        jobStatus={status}
        isDemoMode={false}
        onCancel={vi.fn()}
      />
    );

    expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
  });

  it('should not render cancel button when onCancel is not provided', () => {
    const status: JobStatusResponse = {
      job_id: 'job-1',
      status: 'scraping',
      progress: 0.5,
      competitors_found: 2,
      pages_scraped: 4,
      findings_count: 0,
    };

    render(
      <ProgressConsole events={[]} jobStatus={status} isDemoMode={false} />
    );

    expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
  });

  it('should show status label', () => {
    const status: JobStatusResponse = {
      job_id: 'job-1',
      status: 'analyzing',
      progress: 0.6,
      competitors_found: 2,
      pages_scraped: 8,
      findings_count: 3,
    };

    render(
      <ProgressConsole events={[]} jobStatus={status} isDemoMode={false} />
    );

    expect(screen.getByText('Analyzing Data')).toBeInTheDocument();
  });

  it('should show "Running" indicator for active jobs', () => {
    const status: JobStatusResponse = {
      job_id: 'job-1',
      status: 'scraping',
      progress: 0.3,
      competitors_found: 2,
      pages_scraped: 2,
      findings_count: 0,
    };

    render(
      <ProgressConsole events={[]} jobStatus={status} isDemoMode={false} />
    );

    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  it('should show current step in footer', () => {
    const status: JobStatusResponse = {
      job_id: 'job-1',
      status: 'scraping',
      progress: 0.3,
      current_step: 'scraping competitor pages',
      competitors_found: 2,
      pages_scraped: 2,
      findings_count: 0,
    };

    render(
      <ProgressConsole events={[]} jobStatus={status} isDemoMode={false} />
    );

    expect(screen.getByText(/scraping competitor pages/)).toBeInTheDocument();
  });

  it('should group page.scraped events together', () => {
    const events: AgentEvent[] = [
      {
        event_id: 'evt-1',
        event_type: 'page.scraped',
        job_id: 'job-1',
        agent_name: 'scraper',
        timestamp: new Date().toISOString(),
        message: 'Scraped: example.com/pricing',
      },
      {
        event_id: 'evt-2',
        event_type: 'page.scraped',
        job_id: 'job-1',
        agent_name: 'scraper',
        timestamp: new Date().toISOString(),
        message: 'Scraped: example.com/about',
      },
    ];

    render(
      <ProgressConsole events={events} jobStatus={null} isDemoMode={false} />
    );

    // Grouped as "Scraped 2 pages"
    expect(screen.getByText('Scraped 2 pages')).toBeInTheDocument();
  });

  it('should show "Complete" label for completed jobs', () => {
    const status: JobStatusResponse = {
      job_id: 'job-1',
      status: 'completed',
      progress: 1.0,
      competitors_found: 2,
      pages_scraped: 8,
      findings_count: 5,
    };

    render(
      <ProgressConsole events={[]} jobStatus={status} isDemoMode={false} />
    );

    expect(screen.getByText('Complete')).toBeInTheDocument();
  });

  it('should show "Failed" label for failed jobs', () => {
    const status: JobStatusResponse = {
      job_id: 'job-1',
      status: 'failed',
      progress: 0.45,
      competitors_found: 2,
      pages_scraped: 6,
      findings_count: 2,
      error: 'LLM timeout',
    };

    render(
      <ProgressConsole events={[]} jobStatus={status} isDemoMode={false} />
    );

    expect(screen.getByText('Failed')).toBeInTheDocument();
  });
});
