"use client";
import { useState } from "react";
import { usePreferences } from "@/components/preferences";
import { Archive, Edit3, Plus, Search } from "lucide-react";
import {
  Badge,
  Button,
  Empty,
  ErrorNotice,
  Field,
  Loading,
  Modal,
  Pagination,
} from "@/components/ui";
import { useAction, useData } from "@/hooks/use-data";
import { date, params } from "@/lib/format";
import type { Collection, RecordItem } from "@/types";
export interface FormField {
  name: string;
  label: string;
  type?:
    | "text"
    | "textarea"
    | "date"
    | "email"
    | "url"
    | "number"
    | "checkbox"
    | "select";
  required?: boolean;
  options?: { value: string; label: string }[];
  defaultValue?: string | number | boolean;
  min?: number;
  max?: number;
  nullable?: boolean;
  createOnly?: boolean;
  hint?: string;
}
export interface Column {
  key: string;
  label: string;
  type?: "badge" | "date";
  render?: (item: RecordItem) => React.ReactNode;
}
export function ResourceManager({
  path,
  editPath,
  title,
  singular,
  fields,
  columns,
  archive = false,
  searchable = false,
  extraActions,
  allowCreate = true,
}: {
  path: string;
  editPath: string;
  title: string;
  singular: string;
  fields: FormField[];
  columns: Column[];
  archive?: boolean;
  searchable?: boolean;
  extraActions?: (item: RecordItem) => React.ReactNode;
  allowCreate?: boolean;
}) {
  const { t, locale } = usePreferences();
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [editor, setEditor] = useState<RecordItem | null | undefined>();
  const { data, error, isPending } = useData<Collection>(
    `${path}${params({ page, page_size: 15, q })}`,
    !!path,
  );
  const action = useAction(() => setEditor(undefined));
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {};
    fields
      .filter((f) => !editor || !f.createOnly)
      .forEach((f) => {
        const value = form.get(f.name);
        body[f.name] =
          f.type === "checkbox"
            ? value === "on"
            : f.type === "number"
              ? value === ""
                ? null
                : Number(value)
              : f.nullable && !value
                ? null
                : value;
      });
    action.mutate({
      path: editor ? `${editPath}/${editor.id}` : path,
      method: editor ? "PATCH" : "POST",
      data: body,
    });
  }
  return (
    <>
      <div className="section-heading">
        <h2>{title}</h2>
        {allowCreate && (
          <Button disabled={!path} onClick={() => setEditor(null)}>
            <Plus size={16} />
            {t("Ajouter", "Add")} {singular}
          </Button>
        )}
      </div>
      {searchable && (
        <div className="toolbar">
          <div className="search-input">
            <Search size={17} />
            <input
              aria-label={t(`Rechercher ${singular}`, `Search for ${singular}`)}
              placeholder={t("Rechercher…", "Search…")}
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </div>
        </div>
      )}
      <ErrorNotice
        error={error || (editor === undefined ? action.error : null)}
      />
      <div className="panel">
        {!path ? (
          <Empty
            title={t("Sélectionnez le contexte", "Select a context")}
            description={t(
              "Choisissez une filière ou un niveau pour afficher ses éléments.",
              "Choose a program or level to display its items.",
            )}
          />
        ) : isPending ? (
          <Loading />
        ) : !data?.items.length ? (
          <Empty
            title={t("Aucun élément pour le moment", "No items yet")}
            description={t(
              `Ajoutez ${singular} pour organiser votre établissement.`,
              `Add ${singular} to organize your campus.`,
            )}
          />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  {columns.map((c) => (
                    <th key={c.key}>{c.label}</th>
                  ))}
                  <th>{t("Actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    {columns.map((c) => (
                      <td
                        key={c.key}
                        className={
                          c.key === "name" || c.key === "title" ? "wrap" : ""
                        }
                      >
                        {c.render ? (
                          c.render(item)
                        ) : c.type === "badge" ? (
                          <Badge value={item[c.key]} />
                        ) : c.type === "date" ? (
                          date(item[c.key], false, locale)
                        ) : (
                          String(item[c.key] ?? "—")
                        )}
                      </td>
                    ))}
                    <td>
                      <div className="actions">
                        <button
                          className="icon-button"
                          aria-label={t(
                            `Modifier ${String(item.name || singular)}`,
                            `Edit ${String(item.name || singular)}`,
                          )}
                          onClick={() => setEditor(item)}
                        >
                          <Edit3 size={15} />
                        </button>
                        {archive && item.status !== "ARCHIVED" && (
                          <button
                            className="icon-button"
                            aria-label={t(
                              `Archiver ${String(item.name || singular)}`,
                              `Archive ${String(item.name || singular)}`,
                            )}
                            onClick={() => {
                              if (
                                window.confirm(
                                  t(
                                    `Archiver ${String(item.name || "cet élément")} ? Son historique sera conservé.`,
                                    `Archive ${String(item.name || "this item")}? Its history will be preserved.`,
                                  ),
                                )
                              )
                                action.mutate({
                                  path: `${editPath}/${item.id}`,
                                  method: "DELETE",
                                });
                            }}
                          >
                            <Archive size={15} />
                          </button>
                        )}
                        {extraActions?.(item)}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <Pagination data={data} page={page} setPage={setPage} />
      {editor !== undefined && (
        <Modal
          title={`${editor ? t("Modifier", "Edit") : t("Ajouter", "Add")} ${singular}`}
          onClose={() => setEditor(undefined)}
        >
          <form onSubmit={submit}>
            <ErrorNotice error={action.error} />
            {fields
              .filter((f) => !editor || !f.createOnly)
              .map((f) => {
                const value = editor?.[f.name] ?? f.defaultValue ?? "";
                return f.type === "checkbox" ? (
                  <label className="checkbox" key={f.name}>
                    <input
                      type="checkbox"
                      name={f.name}
                      defaultChecked={!!value}
                    />
                    {f.label}
                  </label>
                ) : (
                  <Field key={f.name} label={f.label} hint={f.hint}>
                    {f.type === "textarea" ? (
                      <textarea
                        name={f.name}
                        required={f.required}
                        defaultValue={String(value)}
                      />
                    ) : f.type === "select" ? (
                      <select
                        name={f.name}
                        required={f.required}
                        defaultValue={String(value)}
                      >
                        {!f.required && (
                          <option value="">{t("Aucun", "None")}</option>
                        )}
                        {f.required && !f.defaultValue && !editor && (
                          <option value="">
                            {t("Sélectionner…", "Select…")}
                          </option>
                        )}
                        {f.options?.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={f.type || "text"}
                        name={f.name}
                        required={f.required}
                        defaultValue={String(value)}
                        min={f.min}
                        max={f.max}
                        maxLength={
                          f.type === "text" || !f.type ? 255 : undefined
                        }
                      />
                    )}
                  </Field>
                );
              })}
            <div className="form-actions">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setEditor(undefined)}
              >
                {t("Annuler", "Cancel")}
              </Button>
              <Button busy={action.isPending}>
                {t("Enregistrer", "Save")}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
