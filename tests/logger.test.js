import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { setupLogging, getLogger, dispose } from '../src/logger.js';
import { configure } from '@logtape/logtape';
import { getTimeRotatingFileSink } from '@logtape/file';

vi.mock('@logtape/logtape', async (importOriginal) => {
  const original = await importOriginal();
  return {
    ...original,
    configure: vi.fn().mockImplementation(() => Promise.resolve()),
    dispose: vi.fn().mockImplementation(() => Promise.resolve()),
  };
});

vi.mock('@logtape/file', () => ({
  getTimeRotatingFileSink: vi.fn(() => 'mocked-file-sink'),
}));

describe('logger', () => {
  let errorSpy;

  beforeEach(() => {
    vi.clearAllMocks();
    errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    errorSpy.mockRestore();
  });

  it('should setup logging without logDir', async () => {
    await setupLogging();
    expect(configure).toHaveBeenCalled();
    const configCall = vi.mocked(configure).mock.calls[0][0];
    expect(configCall.sinks.console).toBeDefined();
    expect(configCall.sinks.file).toBeUndefined();
  });

  it('should setup logging with non-test env', async () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'production';
    try {
      await setupLogging();
      expect(configure).toHaveBeenCalled();
      const configCall = vi.mocked(configure).mock.calls[0][0];
      expect(configCall.loggers[0].lowestLevel).toBe('info');
      expect(configCall.loggers[1].lowestLevel).toBe('warning');
    } finally {
      process.env.NODE_ENV = originalEnv;
    }
  });

  it('should setup logging with logDir', async () => {
    await setupLogging({ logDir: '/tmp/test-logs' });
    expect(getTimeRotatingFileSink).toHaveBeenCalledWith({
      directory: '/tmp/test-logs',
      interval: 'daily',
    });
    expect(configure).toHaveBeenCalled();
    const configCall = vi.mocked(configure).mock.calls[0][0];
    expect(configCall.sinks.file).toBe('mocked-file-sink');
  });

  it('should handle errors when initializing file logging fails', async () => {
    vi.mocked(getTimeRotatingFileSink).mockImplementationOnce(() => {
      throw new Error('Failed to create file sink');
    });

    await setupLogging({ logDir: '/tmp/error-logs' });
    expect(errorSpy).toHaveBeenCalledWith(
      expect.stringContaining('Failed to initialize file logging in directory "/tmp/error-logs"'),
      expect.any(Error)
    );
    expect(configure).toHaveBeenCalled();
    const configCall = vi.mocked(configure).mock.calls[0][0];
    expect(configCall.sinks.file).toBeUndefined();
  });

  it('should get logger instance', () => {
    const logger = getLogger(['test-sub']);
    expect(logger).toBeDefined();
  });

  it('should dispose logtape', async () => {
    await dispose();
  });
});
