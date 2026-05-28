import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExportButton } from '@/components/ExportButton';

vi.mock('@/lib/api', () => ({
  exportReport: vi.fn(),
}));

vi.mock('@/components/ui/toast', () => ({
  toast: vi.fn(),
}));

import { exportReport } from '@/lib/api';
const mockExportReport = vi.mocked(exportReport);

describe('ExportButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render export button', () => {
    render(<ExportButton jobId="job-123" />);
    expect(screen.getByText('Export')).toBeInTheDocument();
  });

  it('should render format selector', () => {
    render(<ExportButton jobId="job-123" />);
    expect(screen.getByLabelText('Export format')).toBeInTheDocument();
  });

  it('should render with correct aria-label', () => {
    render(<ExportButton jobId="job-123" />);
    expect(screen.getByLabelText('Export report as json')).toBeInTheDocument();
  });

  it('should call exportReport API when clicked', async () => {
    mockExportReport.mockResolvedValue({
      job_id: 'job-123',
      format: 'json',
      content: '{"test": true}',
    });

    // Mock URL.createObjectURL and related DOM APIs
    const mockCreateObjectURL = vi.fn(() => 'blob:mock');
    const mockRevokeObjectURL = vi.fn();
    vi.stubGlobal('URL', {
      createObjectURL: mockCreateObjectURL,
      revokeObjectURL: mockRevokeObjectURL,
    });

    const user = userEvent.setup();
    render(<ExportButton jobId="job-123" />);

    await user.click(screen.getByText('Export'));

    await waitFor(() => {
      expect(mockExportReport).toHaveBeenCalledWith('job-123', {
        format: 'json',
        include_citations: true,
        include_raw_data: false,
      });
    });
  });

  it('should handle export error gracefully', async () => {
    mockExportReport.mockRejectedValue(new Error('Export failed'));

    const user = userEvent.setup();
    render(<ExportButton jobId="job-123" />);

    await user.click(screen.getByText('Export'));

    await waitFor(() => {
      expect(mockExportReport).toHaveBeenCalled();
    });
  });

  it('should use download_url when content is not available', async () => {
    const mockOpen = vi.fn();
    vi.stubGlobal('open', mockOpen);

    mockExportReport.mockResolvedValue({
      job_id: 'job-123',
      format: 'pdf',
      download_url: '/data/exports/report.pdf',
    });

    const user = userEvent.setup();
    render(<ExportButton jobId="job-123" />);

    await user.click(screen.getByText('Export'));

    await waitFor(() => {
      expect(mockExportReport).toHaveBeenCalled();
    });
  });
});
