export function titleCase(value: string): string {
  return value
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function formatBytes(value: number | null): string {
  if (value == null) return "Unknown";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function shortPath(value: string): string {
  const parts = value.split("/");
  if (parts.length <= 3) return value;
  return `${parts[0]}/.../${parts.slice(-2).join("/")}`;
}
