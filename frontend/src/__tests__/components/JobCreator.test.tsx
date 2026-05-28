import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JobCreator } from '@/components/JobCreator';

// Mock the store
vi.mock('@/stores/jobStore', () => ({
  useJobStore: vi.fn((selector) => {
    const store = {
      createJob: mockCreateJob,
    };
    return selector ? selector(store) : store;
  }),
}));

const mockCreateJob = vi.fn();

describe('JobCreator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateJob.mockResolvedValue('job-123');
  });

  it('should render the form with title', () => {
    render(<JobCreator isLoading={false} />);
    expect(screen.getByText('New Analysis Job')).toBeInTheDocument();
  });

  it('should render two competitor fields by default', () => {
    render(<JobCreator isLoading={false} />);
    const urlInputs = screen.getAllByPlaceholderText('https://example.com');
    expect(urlInputs).toHaveLength(2);
  });

  it('should render "Add Competitor" button', () => {
    render(<JobCreator isLoading={false} />);
    expect(screen.getByText('Add Competitor')).toBeInTheDocument();
  });

  it('should render the submit button', () => {
    render(<JobCreator isLoading={false} />);
    expect(screen.getByText('Start Intelligence Analysis')).toBeInTheDocument();
  });

  it('should render analysis query textarea', () => {
    render(<JobCreator isLoading={false} />);
    expect(screen.getByLabelText('Analysis Query (optional)')).toBeInTheDocument();
  });

  it('should add a competitor field when "Add Competitor" is clicked', async () => {
    const user = userEvent.setup();
    render(<JobCreator isLoading={false} />);

    await user.click(screen.getByText('Add Competitor'));

    const urlInputs = screen.getAllByPlaceholderText('https://example.com');
    expect(urlInputs).toHaveLength(3);
  });

  it('should show remove button for extra competitors', async () => {
    const user = userEvent.setup();
    render(<JobCreator isLoading={false} />);

    // Add a third competitor
    await user.click(screen.getByText('Add Competitor'));

    // Now we should have remove buttons (trash icons with aria-labels)
    const removeButtons = screen.getAllByLabelText(/Remove competitor/);
    expect(removeButtons).toHaveLength(3); // all 3 have remove buttons when > 2
  });

  it('should not show remove button when only 2 competitors', () => {
    render(<JobCreator isLoading={false} />);
    const removeButtons = screen.queryAllByLabelText(/Remove competitor/);
    expect(removeButtons).toHaveLength(0);
  });

  it('should remove a competitor when remove is clicked', async () => {
    const user = userEvent.setup();
    render(<JobCreator isLoading={false} />);

    // Add third competitor
    await user.click(screen.getByText('Add Competitor'));
    expect(screen.getAllByPlaceholderText('https://example.com')).toHaveLength(3);

    // Remove the third one
    const removeButtons = screen.getAllByLabelText(/Remove competitor/);
    await user.click(removeButtons[2]);

    expect(screen.getAllByPlaceholderText('https://example.com')).toHaveLength(2);
  });

  it('should disable submit when URLs are empty', () => {
    render(<JobCreator isLoading={false} />);
    const submitButton = screen.getByText('Start Intelligence Analysis');
    expect(submitButton).toBeDisabled();
  });

  it('should enable submit when valid URLs are entered', async () => {
    const user = userEvent.setup();
    render(<JobCreator isLoading={false} />);

    const urlInputs = screen.getAllByPlaceholderText('https://example.com');
    await user.type(urlInputs[0], 'https://example.com');
    await user.type(urlInputs[1], 'https://test.com');

    const submitButton = screen.getByText('Start Intelligence Analysis');
    expect(submitButton).not.toBeDisabled();
  });

  it('should call createJob on form submit with valid URLs', async () => {
    const user = userEvent.setup();
    render(<JobCreator isLoading={false} />);

    const urlInputs = screen.getAllByPlaceholderText('https://example.com');
    await user.type(urlInputs[0], 'https://example.com');
    await user.type(urlInputs[1], 'https://test.com');

    await user.click(screen.getByText('Start Intelligence Analysis'));

    expect(mockCreateJob).toHaveBeenCalledWith({
      competitors: [
        { url: 'https://example.com', name: undefined, focus_areas: [] },
        { url: 'https://test.com', name: undefined, focus_areas: [] },
      ],
    });
  });

  it('should include optional query in payload when filled', async () => {
    const user = userEvent.setup();
    render(<JobCreator isLoading={false} />);

    const urlInputs = screen.getAllByPlaceholderText('https://example.com');
    await user.type(urlInputs[0], 'https://example.com');
    await user.type(urlInputs[1], 'https://test.com');

    const queryInput = screen.getByLabelText('Analysis Query (optional)');
    await user.type(queryInput, 'Compare pricing');

    await user.click(screen.getByText('Start Intelligence Analysis'));

    expect(mockCreateJob).toHaveBeenCalledWith(
      expect.objectContaining({ query: 'Compare pricing' })
    );
  });

  it('should include name and focus_areas in payload when filled', async () => {
    const user = userEvent.setup();
    render(<JobCreator isLoading={false} />);

    const urlInputs = screen.getAllByPlaceholderText('https://example.com');
    await user.type(urlInputs[0], 'https://example.com');
    await user.type(urlInputs[1], 'https://test.com');

    const nameInputs = screen.getAllByPlaceholderText('Name (optional)');
    await user.type(nameInputs[0], 'Example Inc');

    const focusInputs = screen.getAllByPlaceholderText('Focus areas (comma-sep)');
    await user.type(focusInputs[0], 'pricing, features');

    await user.click(screen.getByText('Start Intelligence Analysis'));

    expect(mockCreateJob).toHaveBeenCalledWith({
      competitors: [
        { url: 'https://example.com', name: 'Example Inc', focus_areas: ['pricing', 'features'] },
        { url: 'https://test.com', name: undefined, focus_areas: [] },
      ],
    });
  });

  it('should show loading state on submit button', () => {
    render(<JobCreator isLoading={true} />);
    const submitButton = screen.getByText('Start Intelligence Analysis');
    expect(submitButton).toBeDisabled();
  });

  it('should render competitor labels', () => {
    render(<JobCreator isLoading={false} />);
    expect(screen.getByText('Competitor 1')).toBeInTheDocument();
    expect(screen.getByText('Competitor 2')).toBeInTheDocument();
  });
});
