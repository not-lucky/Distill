import { spawn } from 'child_process';

export function spawnCompiler(jsonPath, outputPath, options = {}) {
  const timeoutMs = options.timeout !== undefined ? options.timeout : 60000;

  return new Promise((resolve, reject) => {
    const args = ['run', 'src/compile.py', jsonPath];
    if (outputPath) {
      args.push('-o', outputPath);
    }
    if (options.deckName) {
      args.push('--deck-name', options.deckName);
    }
    if (options.subject) {
      args.push('--subject', options.subject);
    }
    if (options.source) {
      args.push('--source', options.source);
    }

    const child = spawn('uv', args);
    let stdout = '';
    let stderr = '';
    let timedOut = false;

    let timer = null;
    if (timeoutMs > 0) {
      timer = setTimeout(() => {
        timedOut = true;
        child.kill('SIGTERM');
        reject(new Error(`Compiler execution timed out after ${timeoutMs}ms.`));
      }, timeoutMs);
    }

    child.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    child.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    child.on('close', (code) => {
      if (timer) {
        clearTimeout(timer);
      }
      if (timedOut) return;

      if (code === 0) {
        resolve({ code, stdout, stderr });
      } else {
        const error = new Error(`Compiler process exited with code ${code}.\nStderr: ${stderr}`);
        error.code = code;
        error.stdout = stdout;
        error.stderr = stderr;
        reject(error);
      }
    });

    child.on('error', (err) => {
      if (timer) {
        clearTimeout(timer);
      }
      if (timedOut) return;
      reject(err);
    });
  });
}
