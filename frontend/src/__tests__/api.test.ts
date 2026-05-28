import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  createJob,
  getJobStatus,
  listJobs,
  getReport,
  cancelJob,
  exportReport,
  getHealth,
  getStats,
  getTrends,
  listSchedules,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  ApiError,
  API_BASE,
} from '@/lib/api';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function mockJsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  };
}

function mockTextResponse(body: string, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.reject(new Error('not json')),
    text: () => Promise.resolve(body),
  };
}

describe('API_BASE', () => {
  it('should default to localhost:8000', () => {
    expect(API_BASE).toBe('http://localhost:8000');
  });
});

describe('ApiError', () => {
  it('should store status and detail', () => {
    const err = new ApiError('test', 404, 'not found');
    expect(err.message).toBe('test');
    expect(err.status).toBe(404);
    expect(err.detail).toBe('not found');
    expect(err.name).toBe('ApiError');
  });
});

describe('createJob', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should POST to /api/jobs with payload', async () => {
    const response = { job_id: 'abc123', status: 'pending', message: 'Job created' };
    mockFetch.mockResolvedValue(mockJsonResponse(response, 201));

    const result = await createJob({
      competitors: [{ url: 'https://example.com', focus_areas: ['pricing'] }],
    });

    expect(result).toEqual(response);
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/api/jobs`,
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    );
  });

  it('should throw ApiError on 422 validation error', async () => {
    const errorBody = { error: 'Invalid input', detail: 'URL required', status_code: 422 };
    mockFetch.mockResolvedValue(mockJsonResponse(errorBody, 422));

    await expect(
      createJob({ competitors: [{ url: '', focus_areas: [] }] })
    ).rejects.toThrow(ApiError);
  });

  it('should throw ApiError on 429 rate limit', async () => {
    mockFetch.mockResolvedValue(mockTextResponse('Rate limited', 429));

    await expect(
      createJob({ competitors: [{ url: 'https://example.com', focus_areas: [] }] })
    ).rejects.toThrow(ApiError);
  });

  it('should throw ApiError with status 0 on network error', async () => {
    mockFetch.mockRejectedValue(new TypeError('fetch failed'));

    await expect(
      createJob({ competitors: [{ url: 'https://example.com', focus_areas: [] }] })
    ).rejects.toMatchObject({ status: 0 });
  });

  it('should throw ApiError with friendly message for 500', async () => {
    mockFetch.mockResolvedValue(mockTextResponse('', 500));

    await expect(
      createJob({ competitors: [{ url: 'https://example.com', focus_areas: [] }] })
    ).rejects.toMatchObject({ status: 500 });
  });

  it('should parse ErrorResponse JSON for error message', async () => {
    const errorBody = { error: 'Custom error message', status_code: 400 };
    mockFetch.mockResolvedValue(mockJsonResponse(errorBody, 400));

    await expect(
      createJob({ competitors: [{ url: 'https://example.com', focus_areas: [] }] })
    ).rejects.toMatchObject({ message: 'Custom error message' });
  });
});

describe('getJobStatus', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should GET /api/jobs/{id}', async () => {
    const status = { job_id: 'abc', status: 'scraping', progress: 0.3 };
    mockFetch.mockResolvedValue(mockJsonResponse(status));

    const result = await getJobStatus('abc');
    expect(result).toEqual(status);
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/api/jobs/abc`,
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    );
  });

  it('should throw on 404', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({ error: 'Not found', status_code: 404 }, 404));

    await expect(getJobStatus('nonexistent')).rejects.toThrow(ApiError);
  });
});

describe('listJobs', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should GET /api/jobs', async () => {
    const data = { jobs: [], total: 0 };
    mockFetch.mockResolvedValue(mockJsonResponse(data));

    const result = await listJobs();
    expect(result).toEqual(data);
  });
});

describe('getReport', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should GET /api/jobs/{id}/report', async () => {
    const report = { report: { id: 'r1', title: 'Test' } };
    mockFetch.mockResolvedValue(mockJsonResponse(report));

    const result = await getReport('abc');
    expect(result).toEqual(report);
  });

  it('should throw on 400 when job not completed', async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse({ error: 'Job is not yet completed', status_code: 400 }, 400)
    );

    await expect(getReport('abc')).rejects.toThrow(ApiError);
  });
});

describe('cancelJob', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should DELETE /api/jobs/{id}', async () => {
    const result = { job_id: 'abc', status: 'cancelled', message: 'Job cancelled' };
    mockFetch.mockResolvedValue(mockJsonResponse(result));

    const response = await cancelJob('abc');
    expect(response).toEqual(result);
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/api/jobs/abc`,
      expect.objectContaining({ method: 'DELETE' })
    );
  });
});

describe('exportReport', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should POST to /api/jobs/{id}/export', async () => {
    const result = { job_id: 'abc', format: 'json', content: '{}' };
    mockFetch.mockResolvedValue(mockJsonResponse(result));

    const response = await exportReport('abc', {
      format: 'json',
      include_citations: true,
      include_raw_data: false,
    });
    expect(response).toEqual(result);
  });
});

describe('getHealth', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should GET /api/health', async () => {
    const data = { status: 'ok', version: '0.2.0' };
    mockFetch.mockResolvedValue(mockJsonResponse(data));

    const result = await getHealth();
    expect(result).toEqual(data);
  });
});

describe('getStats', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should GET /api/stats', async () => {
    const data = { total_jobs: 10, completed_jobs: 8, failed_jobs: 2 };
    mockFetch.mockResolvedValue(mockJsonResponse(data));

    const result = await getStats();
    expect(result).toEqual(data);
  });
});

describe('getTrends', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should GET /api/trends with default params', async () => {
    const data = { metric: 'findings', data_points: [] };
    mockFetch.mockResolvedValue(mockJsonResponse(data));

    const result = await getTrends();
    expect(result).toEqual(data);
  });

  it('should pass metric and days as query params', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({ metric: 'jobs', data_points: [] }));

    await getTrends('jobs', 7);
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/api/trends?metric=jobs&days=7`,
      expect.any(Object)
    );
  });
});

describe('listSchedules', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should GET /api/schedules', async () => {
    const data = { schedules: [], total: 0 };
    mockFetch.mockResolvedValue(mockJsonResponse(data));

    const result = await listSchedules();
    expect(result).toEqual(data);
  });
});

describe('createSchedule', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should POST to /api/schedules', async () => {
    const result = { schedule_id: 'sch-1', frequency: 'daily', enabled: true };
    mockFetch.mockResolvedValue(mockJsonResponse(result, 201));

    const response = await createSchedule({
      competitors: [{ url: 'https://example.com', focus_areas: ['pricing'] }],
      schedule: { frequency: 'daily' },
    });
    expect(response).toEqual(result);
  });
});

describe('updateSchedule', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should PATCH /api/schedules/{id}', async () => {
    const result = { schedule_id: 'sch-1', enabled: false };
    mockFetch.mockResolvedValue(mockJsonResponse(result));

    const response = await updateSchedule('sch-1', { enabled: false });
    expect(response).toEqual(result);
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/api/schedules/sch-1`,
      expect.objectContaining({ method: 'PATCH' })
    );
  });
});

describe('deleteSchedule', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should DELETE /api/schedules/{id}', async () => {
    mockFetch.mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(), text: () => Promise.resolve('') });

    await deleteSchedule('sch-1');
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE}/api/schedules/sch-1`,
      expect.objectContaining({ method: 'DELETE' })
    );
  });
});

describe('Error handling edge cases', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should handle non-JSON error body gracefully', async () => {
    mockFetch.mockResolvedValue(mockTextResponse('Internal Server Error', 500));

    await expect(getHealth()).rejects.toMatchObject({ status: 500 });
  });

  it('should handle 0 status for non-fetch TypeErrors', async () => {
    mockFetch.mockRejectedValue(new Error('some other error'));

    await expect(getHealth()).rejects.toMatchObject({ status: 0 });
  });

  it('should handle 409 conflict', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({ error: 'Conflict' }, 409));

    await expect(getHealth()).rejects.toMatchObject({ status: 409 });
  });

  it('should handle 502 bad gateway', async () => {
    mockFetch.mockResolvedValue(mockTextResponse('', 502));

    await expect(getHealth()).rejects.toMatchObject({ status: 502 });
  });

  it('should handle 503 service unavailable', async () => {
    mockFetch.mockResolvedValue(mockTextResponse('', 503));

    await expect(getHealth()).rejects.toMatchObject({ status: 503 });
  });
});
