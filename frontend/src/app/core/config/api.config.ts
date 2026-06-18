import { environment } from '../../../environments/environment';

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

function normalizePath(path: string): string {
  return path.startsWith('/') ? path : `/${path}`;
}

function resolveApiBaseUrl(): string {
  return trimTrailingSlash(environment.apiBaseUrl || '/api/v1');
}

function resolveWebSocketBaseUrl(): string {
  if (environment.wsBaseUrl) {
    return trimTrailingSlash(environment.wsBaseUrl);
  }

  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}`;
  }

  return 'ws://localhost:8000';
}

export function buildApiUrl(path: string): string {
  return `${resolveApiBaseUrl()}${normalizePath(path)}`;
}

export function buildWsUrl(path: string): string {
  return `${resolveWebSocketBaseUrl()}${normalizePath(path)}`;
}

export function isAppApiUrl(url: string): boolean {
  return url.startsWith(resolveApiBaseUrl()) || url.startsWith('/');
}
