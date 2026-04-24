import { fileURLToPath } from 'url'; import path from 'path'; console.log(process.argv[1] === fileURLToPath(import.meta.url)); console.log(process.argv[1] === path.resolve(process.argv[1]));
