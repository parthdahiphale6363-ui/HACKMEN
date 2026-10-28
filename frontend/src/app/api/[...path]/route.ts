import { NextRequest, NextResponse } from 'next/server';

let _cachedWorkingBase: string | null = null;

function getCandidateBases(req?: NextRequest): string[] {
  const host = req?.headers.get('host') || '';
  const isLocal = host.includes('localhost') || host.includes('127.0.0.1');

  const localUrls = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://127.0.0.1:8080',
  ];

  const envList = [
    process.env.BACKEND_URL,
    process.env.NEXT_PUBLIC_BACKEND_URL,
  ].filter((u): u is string => Boolean(u && u.trim()));

  const expandedEnvUrls: string[] = [];
  for (const raw of envList) {
    let trimmed = raw.trim().replace(/\/$/, '');
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      if (!trimmed.includes('.') && !trimmed.includes(':')) {
        expandedEnvUrls.push(`https://${trimmed}.onrender.com`);
      }
      trimmed = `https://${trimmed}`;
    }
    expandedEnvUrls.push(trimmed);
  }

  const derivedUrls: string[] = [];
  if (host.includes('onrender.com')) {
    if (host.includes('frontend')) {
      derivedUrls.push(`https://${host.replace('-frontend', '-backend').replace('frontend', 'backend')}`);
    }
    derivedUrls.push('https://truthlens-backend-ca5w.onrender.com');
  }

  const cloudInternalUrls = [
    'https://truthlens-backend-ca5w.onrender.com',
    'http://truthlens-backend:10000',
    'http://truthlens-backend:8000',
    'http://multimodal-video-forensics-fact.railway.internal:8080',
    'http://multimodal-video-forensics-fact.railway.internal:8000',
  ];

  let order: string[];
  if (isLocal) {
    // When running locally via run.bat / localhost:3000, local FastAPI is primary
    order = [...localUrls, ...expandedEnvUrls, ...cloudInternalUrls];
  } else {
    // In cloud deployment, environment and derived Render URLs take priority
    order = [...expandedEnvUrls, ...derivedUrls, ...cloudInternalUrls, ...localUrls];
  }

  if (_cachedWorkingBase) {
    const isCachedLocal = _cachedWorkingBase.includes('localhost') || _cachedWorkingBase.includes('127.0.0.1');
    if (isLocal === isCachedLocal) {
      order = [_cachedWorkingBase, ...order];
    }
  }

  return Array.from(new Set(order));
}

async function handleProxy(req: NextRequest, params: { path?: string[] }) {
  const pathSegments = params.path || [];
  const pathStr = pathSegments.join('/');
  const search = req.nextUrl.search || '';
  const candidates = getCandidateBases(req);

  const isBodyMethod = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method);
  const rawBody = isBodyMethod ? await req.arrayBuffer() : undefined;

  const reqHeaders = new Headers();
  req.headers.forEach((val, key) => {
    if (!['host', 'content-length'].includes(key.toLowerCase())) {
      reqHeaders.set(key, val);
    }
  });

  const triedErrors: Array<{ base: string; error: string }> = [];

  for (const base of candidates) {
    const targetUrl = `${base}/${pathStr}${search}`;
    try {
      const res = await fetch(targetUrl, {
        method: req.method,
        headers: reqHeaders,
        body: rawBody,
        cache: 'no-store',
      });

      const contentType = res.headers.get('content-type') || '';
      // If an upstream host returns HTML (e.g. Cloudflare error or parked domain), reject it as an API backend!
      if (contentType.includes('text/html')) {
        triedErrors.push({ base, error: 'Host returned HTML instead of API JSON' });
        continue;
      }

      // If we got an authentic API response from the backend, cache and return!
      _cachedWorkingBase = base;

      const resBody = await res.arrayBuffer();
      const resHeaders = new Headers();
      res.headers.forEach((val, key) => {
        if (!['content-encoding', 'transfer-encoding', 'content-length'].includes(key.toLowerCase())) {
          resHeaders.set(key, val);
        }
      });

      return new NextResponse(resBody, {
        status: res.status,
        headers: resHeaders,
      });
    } catch (err: any) {
      triedErrors.push({ base, error: err.message || 'Connection failed' });
    }
  }

  return NextResponse.json(
    {
      error: 'Backend Proxy Error',
      message: 'Unable to connect to any backend candidate host',
      tried: triedErrors,
      path: pathStr,
    },
    { status: 502 }
  );
}

export async function GET(req: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const resolved = await context.params;
  return handleProxy(req, resolved);
}

export async function POST(req: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const resolved = await context.params;
  return handleProxy(req, resolved);
}

export async function PUT(req: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const resolved = await context.params;
  return handleProxy(req, resolved);
}

export async function DELETE(req: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const resolved = await context.params;
  return handleProxy(req, resolved);
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': '*',
    },
  });
}
