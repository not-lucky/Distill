import path from 'path'; console.log(import.meta.url === `file://${path.resolve(process.argv[1])}`);
