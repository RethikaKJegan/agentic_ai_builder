import type { SafeError } from "./contracts.generated";
/** Only intentionally authored local validation messages may be shown verbatim. */
export class InputError extends Error {
  constructor(
    message: string,
    public readonly field?: string,
  ) {
    super(message);
  }
}
export type FeedbackKind =
  "unauthorized" | "forbidden" | "conflict" | "retryable" | "uncertain" | "error";
export function unsafeText(value: string) {
  return /Traceback|\b(?:TypeError|ReferenceError|SyntaxError|KeyError|sqlite3\.|psycopg\.)|\n\s*(?:at |File ")|\bsk-[\w-]{8,}|Bearer\s+\S+|-----BEGIN .*PRIVATE KEY|(?:api[_-]?key|password|secret|token)\s*[:=]\s*\S+|:\/\/[^/\s:@]+:[^/\s@]+@/i.test(
    value,
  );
}
export function safeError(error: SafeError): SafeError {
  const text = (value: string) =>
    unsafeText(value)
      ? "The server could not complete this request. Use the request reference for investigation."
      : value.slice(0, 1000);
  const reference = (value: string) => (/^[\w-]{1,128}$/.test(value) ? value : "req_unavailable");
  return {
    ...error,
    message: text(error.message),
    request_id: reference(error.request_id),
    ...(error.field
      ? { field: unsafeText(error.field) ? "request" : error.field.slice(0, 200) }
      : {}),
    ...(error.related_errors
      ? {
          related_errors: error.related_errors.map((item) => ({
            ...item,
            message: text(item.message),
            ...(item.field
              ? { field: unsafeText(item.field) ? "request" : item.field.slice(0, 200) }
              : {}),
          })),
        }
      : {}),
  };
}

/** Field feedback is matched by exact canonical path, never raw validator data. */
export function fieldMessages(error: Error | undefined, field: string): string[] {
  if (error instanceof InputError)
    return error.field === field && !unsafeText(error.message) ? [error.message] : [];
  if (error && "error" in error) {
    const candidate = (error as Error & { error: SafeError }).error;
    return [
      ...(candidate.field === field ? [candidate.message] : []),
      ...(candidate.related_errors ?? [])
        .filter((item) => item.field === field)
        .map((item) => item.message),
    ].filter((message) => !unsafeText(message));
  }
  return [];
}
