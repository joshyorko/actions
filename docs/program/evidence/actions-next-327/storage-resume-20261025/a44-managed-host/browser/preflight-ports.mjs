// Run only when the owner authorizes launch; never imports serve.ts.
import net from 'node:net';
const held = [];
try {
  for (const port of [8080, 8081]) {
    const server = net.createServer();
    held.push(server);
    await new Promise((resolve, reject) => {
      server.once('error', reject);
      server.listen({ host: '127.0.0.1', port, exclusive: true }, resolve);
    });
  }
  console.log('Loopback ports 8080 and 8081 are available; start the authorized host immediately.');
} finally {
  await Promise.all(held.map(server => new Promise(resolve => server.close(() => resolve()))));
}
