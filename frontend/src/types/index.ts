export type Role =
  | "PLATFORM_ADMIN"
  | "CAMPUS_ADMIN"
  | "CONTENT_PUBLISHER"
  | "MODERATOR"
  | "STUDENT";
export interface Campus {
  id: string;
  name: string;
  code: string;
  slug?: string;
  status?: string;
  [key: string]: unknown;
}
export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  status: string;
  roles: { id: string; role: Role; campus_id: string | null }[];
  campuses: Campus[];
}
export interface Collection<T = RecordItem> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
export interface RecordItem {
  id: string;
  [key: string]: unknown;
}
