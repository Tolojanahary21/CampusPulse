"use client";
import { useEffect, useId, useRef } from "react";
import { usePreferences } from "./preferences";
import { errorMessage } from "@/lib/error-message";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Inbox,
  Loader2,
  X,
} from "lucide-react";
import type { Collection } from "@/types";
import { label } from "@/lib/format";
export function Button({
  children,
  variant = "primary",
  busy = false,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  busy?: boolean;
}) {
  return (
    <button
      {...props}
      aria-busy={busy || undefined}
      disabled={busy || props.disabled}
      className={`button ${variant} ${props.className || ""}`}
    >
      {busy && <Loader2 size={16} className="spin" />}
      {children}
    </button>
  );
}
export function Badge({ value }: { value: unknown }) {
  const { locale } = usePreferences();
  return (
    <span className={`badge ${String(value).toLowerCase()}`}>
      {label(value, locale)}
    </span>
  );
}
export function ErrorNotice({ error }: { error: unknown }) {
  const { locale } = usePreferences();
  if (!error) return null;
  return (
    <div role="alert" className="notice error">
      <AlertCircle size={18} />
      <span>{errorMessage(error, locale)}</span>
    </div>
  );
}
export function Success({ children }: { children: React.ReactNode }) {
  return (
    <div role="status" className="notice success">
      {children}
    </div>
  );
}
export function Loading() {
  const { t } = usePreferences();
  return (
    <div className="loading" role="status">
      <Loader2 className="spin" size={23} />
      <span>{t("Chargement de votre espace…", "Loading your workspace…")}</span>
    </div>
  );
}
export function Empty({
  title,
  description,
  children,
}: {
  title?: string;
  description?: string;
  children?: React.ReactNode;
}) {
  const { t } = usePreferences();
  return (
    <div className="empty">
      <span className="empty-icon">
        <Inbox size={26} />
      </span>
      <h3>{title || t("Rien pour le moment", "Nothing here yet")}</h3>
      <p>
        {description ||
          t(
            "Les nouveaux éléments apparaîtront ici.",
            "New items will appear here.",
          )}
      </p>
      {children}
    </div>
  );
}
export function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}
export function Field({
  label: caption,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{caption}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const { t } = usePreferences();
  useEffect(() => {
    dialog.current?.showModal();
    const current = dialog.current;
    return () => current?.close();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="modal"
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-head">
        <h2 id={titleId}>{title}</h2>
        <button
          className="icon-button"
          aria-label={t("Fermer", "Close")}
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Pagination({
  data,
  page,
  setPage,
}: {
  data?: Collection<unknown>;
  page: number;
  setPage: (p: number) => void;
}) {
  const { t } = usePreferences();
  if (!data || data.total <= data.page_size) return null;
  const pages = Math.ceil(data.total / data.page_size);
  return (
    <div className="pagination">
      <span>
        {t(
          `${data.total} résultats · Page ${page} sur ${pages}`,
          `${data.total} results · Page ${page} of ${pages}`,
        )}
      </span>
      <div className="actions">
        <Button
          variant="secondary"
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
          aria-label={t("Page précédente", "Previous page")}
        >
          <ArrowLeft size={16} />
        </Button>
        <Button
          variant="secondary"
          disabled={page >= pages}
          onClick={() => setPage(page + 1)}
          aria-label={t("Page suivante", "Next page")}
        >
          <ArrowRight size={16} />
        </Button>
      </div>
    </div>
  );
}
export function Tabs({
  items,
  value,
  onChange,
}: {
  items: { id: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="tabs" role="tablist">
      {items.map((item) => (
        <button
          key={item.id}
          role="tab"
          aria-selected={value === item.id}
          onClick={() => onChange(item.id)}
          className={value === item.id ? "active" : ""}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
