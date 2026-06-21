import { setTimeout as sleep } from 'node:timers/promises';
import pLimit from 'p-limit';

export function createThrottledFetcher(config) {
  const requestDelay =
    config.global.request_delay !== undefined ? config.global.request_delay : 1.0;

  const delayLimit = pLimit(1);
  let lastStartTime = 0;

  return (fn) => {
    if (requestDelay <= 0) {
      return fn();
    }
    return delayLimit(async () => {
      const delayMs = requestDelay * 1000;
      const now = Date.now();
      const nextStart = lastStartTime + delayMs;
      const diff = nextStart - now;

      if (diff > 0) {
        lastStartTime = nextStart;
        await sleep(diff);
      } else {
        lastStartTime = now;
      }
    }).then(() => fn());
  };
}
