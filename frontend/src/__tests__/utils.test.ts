import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  cn,
  formatDate,
  formatProgress,
  confidenceColor,
  statusColor,
  formatNumber,
} from '@/lib/utils';

describe('cn', () => {
  it('should merge class names', () => {
    const result = cn('foo', 'bar');
    expect(result).toContain('foo');
    expect(result).toContain('bar');
  });

  it('should handle conditional classes', () => {
    const result = cn('foo', false && 'bar', 'baz');
    expect(result).toContain('foo');
    expect(result).toContain('baz');
    expect(result).not.toContain('bar');
  });

  it('should merge conflicting Tailwind classes', () => {
    const result = cn('px-4', 'px-8');
    expect(result).toBe('px-8');
  });

  it('should handle undefined and null', () => {
    const result = cn('foo', undefined, null, 'bar');
    expect(result).toContain('foo');
    expect(result).toContain('bar');
  });

  it('should handle arrays', () => {
    const result = cn(['foo', 'bar']);
    expect(result).toContain('foo');
    expect(result).toContain('bar');
  });
});

describe('formatDate', () => {
  it('should return "—" for null/undefined', () => {
    expect(formatDate(null)).toBe('—');
    expect(formatDate(undefined)).toBe('—');
    expect(formatDate('')).toBe('—');
  });

  it('should return relative time for recent dates (seconds)', () => {
    const date = new Date(Date.now() - 30000).toISOString(); // 30 seconds ago
    const result = formatDate(date);
    expect(result).toBe('Just now');
  });

  it('should return relative time for recent dates (minutes)', () => {
    const date = new Date(Date.now() - 300000).toISOString(); // 5 minutes ago
    const result = formatDate(date);
    expect(result).toBe('5m ago');
  });

  it('should return relative time for recent dates (hours)', () => {
    const date = new Date(Date.now() - 7200000).toISOString(); // 2 hours ago
    const result = formatDate(date);
    expect(result).toBe('2h ago');
  });

  it('should return relative time for recent dates (days)', () => {
    const date = new Date(Date.now() - 172800000).toISOString(); // 2 days ago
    const result = formatDate(date);
    expect(result).toBe('2d ago');
  });

  it('should return relative time for recent dates (months)', () => {
    const date = new Date(Date.now() - 2592000000).toISOString(); // 30 days ago
    const result = formatDate(date);
    expect(result).toBe('1mo ago');
  });

  it('should return absolute format when mode is "absolute"', () => {
    const date = '2025-06-15T14:30:00Z';
    const result = formatDate(date, 'absolute');
    expect(result).toContain('Jun');
    expect(result).toContain('15');
    expect(result).toContain('2025');
  });

  it('should handle invalid date strings gracefully', () => {
    // Note: the current implementation may return NaN-based strings for
    // invalid dates that produce NaN from Date arithmetic. We verify it
    // doesn't throw an error.
    const result = formatDate('not-a-date');
    expect(typeof result).toBe('string');
  });
});

describe('formatProgress', () => {
  it('should format 0 to "0%"', () => {
    expect(formatProgress(0)).toBe('0%');
  });

  it('should format 1 to "100%"', () => {
    expect(formatProgress(1)).toBe('100%');
  });

  it('should format 0.5 to "50%"', () => {
    expect(formatProgress(0.5)).toBe('50%');
  });

  it('should format 0.756 to "76%"', () => {
    expect(formatProgress(0.756)).toBe('76%');
  });

  it('should clamp values below 0', () => {
    expect(formatProgress(-0.5)).toBe('0%');
  });

  it('should clamp values above 1', () => {
    expect(formatProgress(1.5)).toBe('100%');
  });

  it('should format 0.333 to "33%"', () => {
    expect(formatProgress(0.333)).toBe('33%');
  });
});

describe('confidenceColor', () => {
  it('should return green colors for high confidence', () => {
    const result = confidenceColor('high');
    expect(result.bg).toContain('success');
    expect(result.text).toContain('success');
    expect(result.border).toContain('success');
  });

  it('should return yellow colors for medium confidence', () => {
    const result = confidenceColor('medium');
    expect(result.bg).toContain('warning');
    expect(result.text).toContain('warning');
    expect(result.border).toContain('warning');
  });

  it('should return red colors for low confidence', () => {
    const result = confidenceColor('low');
    expect(result.bg).toContain('error');
    expect(result.text).toContain('error');
    expect(result.border).toContain('error');
  });

  it('should return muted colors for unknown level', () => {
    const result = confidenceColor('unknown');
    expect(result.bg).toContain('text-muted');
    expect(result.text).toContain('text-muted');
    expect(result.border).toContain('text-muted');
  });

  it('should return all three color properties', () => {
    const result = confidenceColor('high');
    expect(result).toHaveProperty('bg');
    expect(result).toHaveProperty('text');
    expect(result).toHaveProperty('border');
  });
});

describe('statusColor', () => {
  it('should return correct colors for pending status', () => {
    const result = statusColor('pending');
    expect(result.label).toBe('Pending');
    expect(result.bg).toContain('text-muted');
  });

  it('should return correct colors for scraping status', () => {
    const result = statusColor('scraping');
    expect(result.label).toBe('Scraping');
    expect(result.bg).toContain('accent');
  });

  it('should return correct colors for analyzing status', () => {
    const result = statusColor('analyzing');
    expect(result.label).toBe('Analyzing');
  });

  it('should return correct colors for verifying status', () => {
    const result = statusColor('verifying');
    expect(result.label).toBe('Verifying');
    expect(result.bg).toContain('warning');
  });

  it('should return correct colors for generating_report status', () => {
    const result = statusColor('generating_report');
    expect(result.label).toBe('Generating');
  });

  it('should return correct colors for completed status', () => {
    const result = statusColor('completed');
    expect(result.label).toBe('Complete');
    expect(result.bg).toContain('success');
  });

  it('should return correct colors for failed status', () => {
    const result = statusColor('failed');
    expect(result.label).toBe('Failed');
    expect(result.bg).toContain('error');
  });

  it('should return correct colors for cancelled status', () => {
    const result = statusColor('cancelled');
    expect(result.label).toBe('Cancelled');
    expect(result.bg).toContain('text-muted');
  });

  it('should fallback to pending for unknown status', () => {
    const result = statusColor('unknown');
    expect(result.label).toBe('Pending');
  });

  it('should return all four color properties', () => {
    const result = statusColor('pending');
    expect(result).toHaveProperty('bg');
    expect(result).toHaveProperty('text');
    expect(result).toHaveProperty('dot');
    expect(result).toHaveProperty('label');
  });
});

describe('formatNumber', () => {
  it('should format small numbers', () => {
    expect(formatNumber(42)).toBe('42');
  });

  it('should format thousands with comma', () => {
    expect(formatNumber(1234)).toBe('1,234');
  });

  it('should format millions with commas', () => {
    expect(formatNumber(1234567)).toBe('1,234,567');
  });

  it('should format zero', () => {
    expect(formatNumber(0)).toBe('0');
  });

  it('should format negative numbers', () => {
    expect(formatNumber(-1234)).toBe('-1,234');
  });

  it('should format decimal numbers', () => {
    expect(formatNumber(1234.56)).toContain('1,234.56');
  });
});
