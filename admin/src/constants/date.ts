import { dayjs } from "element-plus";

/** 与后端 DATE_FMT 一致 */
export const DATE_FORMAT = "YYYY-MM-DD";
/** 与后端 DATETIME_FMT 一致 */
export const DATETIME_FORMAT = "YYYY-MM-DD HH:mm:ss";

export function formatDate(value: unknown): string {
  if (value == null || value === "") return "";
  const parsed = dayjs(value as string | number | Date);
  return parsed.isValid() ? parsed.format(DATE_FORMAT) : String(value);
}

export function formatDateTime(value: unknown): string {
  if (value == null || value === "") return "";
  const parsed = dayjs(value as string | number | Date);
  return parsed.isValid() ? parsed.format(DATETIME_FORMAT) : String(value);
}
