/**
 * Cloudflare Worker for email subscriptions
 *
 * Endpoints:
 * - POST /subscribe - Subscribe an email
 * - GET /unsubscribe?token=xxx - Unsubscribe via token
 * - GET /subscribers?key=SECRET - List all subscribers (protected)
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function generateToken() {
  return crypto.randomUUID();
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

async function handleSubscribe(request, env) {
  try {
    const { email } = await request.json();

    if (!email || !isValidEmail(email)) {
      return new Response(JSON.stringify({ error: 'Invalid email' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
      });
    }

    const normalizedEmail = email.toLowerCase().trim();

    // Check if already subscribed
    const existing = await env.SUBSCRIBERS.get(normalizedEmail);
    if (existing) {
      return new Response(JSON.stringify({ message: 'Already subscribed' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
      });
    }

    // Create new subscription
    const token = generateToken();
    const data = {
      token,
      subscribed_at: new Date().toISOString(),
    };

    await env.SUBSCRIBERS.put(normalizedEmail, JSON.stringify(data));

    return new Response(JSON.stringify({ message: 'Subscribed successfully' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: 'Server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }
}

async function handleUnsubscribe(request, env) {
  const url = new URL(request.url);
  const token = url.searchParams.get('token');

  if (!token) {
    return new Response(htmlPage('Error', 'Invalid unsubscribe link.'), {
      status: 400,
      headers: { 'Content-Type': 'text/html' },
    });
  }

  // Find and remove subscriber by token
  const list = await env.SUBSCRIBERS.list();
  let found = false;

  for (const key of list.keys) {
    const data = await env.SUBSCRIBERS.get(key.name);
    if (data) {
      const parsed = JSON.parse(data);
      if (parsed.token === token) {
        await env.SUBSCRIBERS.delete(key.name);
        found = true;
        break;
      }
    }
  }

  if (found) {
    return new Response(htmlPage('Unsubscribed', 'You have been unsubscribed from job alerts.'), {
      status: 200,
      headers: { 'Content-Type': 'text/html' },
    });
  } else {
    return new Response(htmlPage('Not Found', 'Subscription not found or already unsubscribed.'), {
      status: 404,
      headers: { 'Content-Type': 'text/html' },
    });
  }
}

async function handleListSubscribers(request, env) {
  const url = new URL(request.url);
  const key = url.searchParams.get('key');

  if (key !== env.API_SECRET) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const list = await env.SUBSCRIBERS.list();
  const subscribers = [];

  for (const key of list.keys) {
    const data = await env.SUBSCRIBERS.get(key.name);
    if (data) {
      const parsed = JSON.parse(data);
      subscribers.push({
        email: key.name,
        token: parsed.token,
        subscribed_at: parsed.subscribed_at,
      });
    }
  }

  return new Response(JSON.stringify({ subscribers }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

function htmlPage(title, message) {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title} - Quality Jobs</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }
    .card { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }
    h1 { margin: 0 0 16px; color: #333; }
    p { color: #666; margin: 0; }
    a { color: #0066cc; }
  </style>
</head>
<body>
  <div class="card">
    <h1>${title}</h1>
    <p>${message}</p>
    <p style="margin-top: 20px;"><a href="https://dankopenko.github.io/QualityJobs/">Back to Quality Jobs</a></p>
  </div>
</body>
</html>`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    // Route requests
    if (url.pathname === '/subscribe' && request.method === 'POST') {
      return handleSubscribe(request, env);
    }

    if (url.pathname === '/unsubscribe' && request.method === 'GET') {
      return handleUnsubscribe(request, env);
    }

    if (url.pathname === '/subscribers' && request.method === 'GET') {
      return handleListSubscribers(request, env);
    }

    return new Response('Not Found', { status: 404 });
  },
};
