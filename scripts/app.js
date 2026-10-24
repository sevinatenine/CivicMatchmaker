#!/usr/bin/env node
/**
 * One entry point for running and deploying, driven by APP_ENV in .env.
 *
 *   npm start | web | android | ios [-- --native]
 *       local:  starts the Python API server (Julia 1 or OpenRouter, see LLM_PROVIDER) and the
 *               Expo dev server pointed at it
 *       hosted: starts only the Expo dev server, pointed at the deployed API (HOSTED_URL)
 *       Both print QR codes for the web app and for Expo Go once Metro is up.
 *       --native: build and run the native app (expo run:android|ios) instead of Expo Go
 *   npm run server                  API server only (local)
 *   npm run deploy                  export the web app + deploy it to Cloudflare (free Worker),
 *                                   with /api proxied to the Render API server (BACKEND_URL)
 */
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const qrcode = require('qrcode-terminal');

const ROOT = path.resolve(__dirname, '..');
const API_DIR = path.join(ROOT, 'CivicAI');

// ------------------------------------------------------------------ config
function readEnvFile(file) {
  const out = {};
  if (!fs.existsSync(file)) return out;
  for (let line of fs.readFileSync(file, 'utf8').split('\n')) {
    line = line.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const i = line.indexOf('=');
    const value = line.slice(i + 1).split(' #')[0].trim().replace(/^['"]|['"]$/g, '');
    out[line.slice(0, i).trim()] = value;
  }
  return out;
}

// Real environment variables win over .env, same as CivicAI/config.py
const config = { ...readEnvFile(path.join(ROOT, '.env')), ...process.env };
const APP_ENV = config.APP_ENV || 'local';
const PORT = config.PORT || '4000';
const HOSTED_URL = (config.HOSTED_URL || '').replace(/\/+$/, '');
const BACKEND_URL = (config.BACKEND_URL || '').replace(/\/+$/, '');
const METRO_PORT = 8081;

function fail(msg) {
  console.error(`\n✖ ${msg}\n`);
  process.exit(1);
}

function requireKeys(...keys) {
  const missing = keys.filter((k) => !config[k]);
  if (missing.length) fail(`Set ${missing.join(', ')} in .env (see .env.example).`);
}

// ------------------------------------------------------------------ helpers
function lanIp() {
  for (const addrs of Object.values(os.networkInterfaces())) {
    for (const a of addrs || []) {
      if (a.family === 'IPv4' && !a.internal) return a.address;
    }
  }
  return 'localhost';
}

function run(cmd, args, env = {}) {
  const r = spawnSync(cmd, args, { cwd: ROOT, stdio: 'inherit', env: { ...process.env, ...env } });
  if (r.status !== 0) fail(`${cmd} ${args.join(' ')} failed.`);
}

function python() {
  const venv = path.join(API_DIR, '.venv', 'bin', 'python');
  return fs.existsSync(venv) ? venv : 'python3';
}

async function waitFor(url, tries = 120) {
  for (let i = 0; i < tries; i++) {
    try {
      if ((await fetch(url, { signal: AbortSignal.timeout(2000) })).ok) return true;
    } catch {}
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

function printQr(label, url) {
  qrcode.generate(url, { small: true }, (qr) => console.log(`\n${label}: ${url}\n${qr}`));
}

async function serverRunning() {
  try {
    const res = await fetch(`http://localhost:${PORT}/status`, { signal: AbortSignal.timeout(1000) });
    return res.ok;
  } catch {
    return false;
  }
}

/** Starts CivicAI/main.py unless a server already answers on PORT. Returns the child or null. */
async function startServer() {
  if (await serverRunning()) {
    console.log(`API server already running on :${PORT}, using it.`);
    return null;
  }
  console.log(`Starting API server on :${PORT} (${python()})`);
  const child = spawn(python(), ['main.py'], { cwd: API_DIR, stdio: 'inherit', env: process.env });
  child.on('exit', (code) => code && console.error(`API server exited with code ${code}`));
  return child;
}

// ------------------------------------------------------------------ commands
async function start(platform) {
  let apiUrl;
  let server = null;
  const ip = lanIp();
  if (APP_ENV === 'hosted') {
    requireKeys('HOSTED_URL');
    apiUrl = `${HOSTED_URL}/api`;
  } else {
    server = await startServer();
    // LAN IP so emulators and phones on the same Wi-Fi can reach it too
    apiUrl = `http://${ip}:${PORT}`;
  }
  console.log(`APP_ENV=${APP_ENV}  ->  app talks to ${apiUrl}\n`);

  let args = ['expo', 'start'];
  if (extra.includes('--native') && platform !== 'web') {
    args = ['expo', `run:${platform}`]; // local native build instead of Expo Go
  } else if (platform === 'ios' && process.platform !== 'darwin') {
    console.log('No iOS simulator on this OS: scan the Expo Go QR code with your iPhone.\n');
  } else if (platform) {
    args.push(`--${platform}`);
  }
  // Anything else goes to Expo, e.g. `npm start -- -c` to clear the bundler cache
  args.push(...extra.filter((a) => a !== '--native'));
  const expo = spawn('npx', args, {
    cwd: ROOT,
    stdio: 'inherit',
    env: { ...process.env, EXPO_PUBLIC_API_URL: apiUrl },
  });
  const stop = () => server && !server.killed && server.kill();
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
  expo.on('exit', (code) => {
    stop();
    process.exit(code ?? 0);
  });

  // After Metro is up, so Expo's own startup output doesn't push them off screen
  if (await waitFor(`http://localhost:${METRO_PORT}/status`)) {
    printQr('Web (phone on the same Wi-Fi)', APP_ENV === 'hosted' ? HOSTED_URL : `http://${ip}:${METRO_PORT}`);
    printQr('App (scan with Expo Go on Android / the Camera app on iOS)', `exp://${ip}:${METRO_PORT}`);
  }
}

async function serverOnly() {
  const child = await startServer();
  if (child) child.on('exit', (code) => process.exit(code ?? 0));
}

async function deploy() {
  requireKeys('CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_API_TOKEN', 'BACKEND_URL');

  // Same origin as the Worker, so the web app calls a relative /api
  run('npx', ['expo', 'export', '-p', 'web'], { EXPO_PUBLIC_API_URL: '/api' });
  run('npx', ['wrangler', 'deploy', '--var', `API_ORIGIN:${BACKEND_URL}`], {
    CLOUDFLARE_ACCOUNT_ID: config.CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_API_TOKEN: config.CLOUDFLARE_API_TOKEN,
  });

  // Render's free plan sleeps when idle; wake it so the first visitor doesn't wait
  console.log(`\nWaking the API server at ${BACKEND_URL} ...`);
  console.log((await waitFor(`${BACKEND_URL}/status`, 30)) ? 'API server is up.' : 'API server did not answer yet (still starting?).');

  if (HOSTED_URL) {
    printQr('Web', HOSTED_URL);
  } else {
    console.log('\nNext: copy the workers.dev URL above into HOSTED_URL in .env (for QR codes and APP_ENV=hosted).');
  }
}

// ------------------------------------------------------------------ main
const [cmd, ...extra] = process.argv.slice(2);
const commands = {
  web: () => start('web'),
  android: () => start('android'),
  ios: () => start('ios'),
  start: () => start(null),
  server: serverOnly,
  deploy,
};
if (!commands[cmd]) fail(`Unknown command "${cmd}". Use one of: ${Object.keys(commands).join(', ')}`);
commands[cmd]();
