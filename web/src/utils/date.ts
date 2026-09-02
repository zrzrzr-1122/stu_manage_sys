const DATE_RE = /^(\d{4}-\d{2}-\d{2})/;
const DATETIME_RE = /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/;

export const DATE_FORMAT = "YYYY-MM-DD";
export const DATETIME_FORMAT = "YYYY-MM-DD HH:mm:ss";

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

export function formatDate(value: unknown): string {
  if (value == null || value === "") return "";
  const text = String(value).trim();
  const matched = DATE_RE.exec(text);
  if (matched) return matched[1];
  const d = new Date(text);
  if (Number.isNaN(d.getTime())) return text;
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

export function formatDateTime(value: unknown): string {
  if (value == null || value === "") return "";
  const text = String(value).trim();
  const matched = DATETIME_RE.exec(text);
  if (matched) return matched[1];
  if (DATE_RE.test(text)) return `${text.slice(0, 10)} 00:00:00`;
  const d = new Date(text);
  if (Number.isNaN(d.getTime())) return text;
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}
