"use client";
import { useState } from "react";
import { usePreferences } from "@/components/preferences";
import { Shield, Search, UserPlus, X } from "lucide-react";
import { useSession } from "@/components/app-shell";
import {
  Badge,
  Button,
  Empty,
  ErrorNotice,
  Field,
  Loading,
  Modal,
  PageTitle,
  Pagination,
  Success,
  Tabs,
} from "@/components/ui";
import { useAction, useData } from "@/hooks/use-data";
import { date, label, params } from "@/lib/format";
import type { Collection, RecordItem } from "@/types";
import { ResourceManager } from "./resource-manager";
import { Settings } from "./settings";
import { RegistrationLinks } from "./registration-links";
function RolesDialog({
  campus,
  onClose,
}: {
  campus: RecordItem;
  onClose: () => void;
}) {
  const { t, locale } = usePreferences();
  const [page, setPage] = useState(1);
  const roles = useData<Collection>(
    `/campuses/${campus.id}/roles?page=${page}&page_size=20`,
  );
  const [q, setQ] = useState("");
  const users = useData<Collection>(
    `/platform/users${params({ q, page_size: 100 })}`,
  );
  const action = useAction();
  return (
    <Modal
      title={t(`Rôles · ${campus.name}`, `Roles · ${campus.name}`)}
      onClose={onClose}
    >
      <ErrorNotice error={roles.error || users.error || action.error} />
      <p className="form-help">
        {t(
        "Attribuez un rôle à un compte existant ou créez un lien d’inscription à partager.",
        "Assign a role to an existing account or create a shareable registration link.",
        )}
      </p>
      {roles.data?.items.map((role) => (
        <div className="settings-row" key={role.id}>
          <div>
            <strong>
              {String(role.user_name || role.user_email || role.user_id)}
            </strong>
            <p>
              {label(role.role, locale)}
              {role.expires_at
                ? ` · ${t("Expire le", "Expires on")} ${date(role.expires_at, false, locale)}`
                : ""}
              {role.revoked_at ? t(" · Révoqué", " · Revoked") : ""}
            </p>
          </div>
          {!role.revoked_at && (
            <button
              className="icon-button"
              aria-label={t("Révoquer ce rôle", "Revoke this role")}
              disabled={action.isPending}
              onClick={() => {
                if (
                  window.confirm(
                    t(
                      "Révoquer ce rôle ? Les permissions correspondantes seront retirées.",
                      "Revoke this role? The associated permissions will be removed.",
                    ),
                  )
                )
                  action.mutate({
                    path: `/roles/${role.id}`,
                    method: "DELETE",
                  });
              }}
            >
              <X size={16} />
            </button>
          )}
        </div>
      ))}
      <Pagination data={roles.data} page={page} setPage={setPage} />
      <form
        style={{ marginTop: 24 }}
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          action.mutate({
            path: `/platform/campuses/${campus.id}/admins`,
            data: {
              user_id: f.get("user_id"),
              role: f.get("role"),
              expires_at: f.get("expires_at")
                ? new Date(String(f.get("expires_at"))).toISOString()
                : null,
            },
          });
        }}
      >
        <Field label={t("Rechercher un compte", "Search accounts")}>
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("Nom ou email", "Name or email")}
          />
        </Field>
        <Field label={t("Compte", "Account")}>
          <select name="user_id" required defaultValue="">
            <option value="">
              {t("Choisir un compte", "Choose an account")}
            </option>
            {users.data?.items.map((u) => (
              <option value={u.id} key={u.id}>
                {String(u.first_name)} {String(u.last_name)} · {String(u.email)}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t("Rôle", "Role")}>
          <select name="role">
            {["CAMPUS_ADMIN", "CONTENT_PUBLISHER", "MODERATOR", "STUDENT"].map(
              (r) => (
                <option value={r} key={r}>
                  {label(r, locale)}
                </option>
              ),
            )}
          </select>
        </Field>
        <Field label={t("Expiration (facultative)", "Expiry (optional)")}>
          <input type="datetime-local" name="expires_at" />
        </Field>
        <Button busy={action.isPending}>
          <UserPlus size={16} />
          {t("Attribuer le rôle", "Assign role")}
        </Button>
      </form>
    </Modal>
  );
}
function PlatformUsers() {
  const { t, locale } = usePreferences();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [saved, setSaved] = useState(false);
  const { data, error, isPending } = useData<Collection>(
    `/platform/users${params({ q, page, page_size: 20 })}`,
  );
  const action = useAction(() => setSaved(true));
  return (
    <>
      <div className="section-heading">
        <h2>{t("Tous les comptes", "All accounts")}</h2>
      </div>
      <div className="toolbar">
        <div className="search-input">
          <Search size={17} />
          <input
            aria-label={t("Rechercher un compte", "Search accounts")}
            placeholder={t(
              "Nom, prénom ou adresse email…",
              "Name or email address…",
            )}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>
      <ErrorNotice error={error || action.error} />
      {saved && (
        <Success>
          {t(
            "Le statut du compte a été mis à jour.",
            "The account status has been updated.",
          )}
        </Success>
      )}
      <div className="panel">
        {isPending ? (
          <Loading />
        ) : !data?.items.length ? (
          <Empty title={t("Aucun compte trouvé", "No accounts found")} />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t("Nom", "Name")}</th>
                  <th>{t("Email", "Email")}</th>
                  <th>{t("Créé le", "Created")}</th>
                  <th>{t("Statut global", "Global status")}</th>
                  <th>{t("Modifier le statut", "Change status")}</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      {String(item.first_name)} {String(item.last_name)}
                    </td>
                    <td>{String(item.email)}</td>
                    <td>{date(item.created_at, false, locale)}</td>
                    <td>
                      <Badge value={item.status} />
                    </td>
                    <td>
                      <select
                        aria-label={t(
                          `Statut global de ${item.first_name}`,
                          `Global status of ${item.first_name}`,
                        )}
                        style={{
                          width: 140,
                          padding: "7px 10px",
                          fontSize: 12,
                        }}
                        value={String(item.status)}
                        disabled={action.isPending}
                        onChange={(e) => {
                          if (
                            window.confirm(
                              t(
                                "Modifier le statut global de ce compte ? Cela concerne tous ses établissements.",
                                "Change this account’s global status? This will affect all of its campuses.",
                              ),
                            )
                          ) {
                            setSaved(false);
                            action.mutate({
                              path: `/platform/users/${item.id}/status`,
                              method: "PATCH",
                              data: { status: e.target.value },
                            });
                          }
                        }}
                      >
                        <option value="ACTIVE">{t("Actif", "Active")}</option>
                        <option value="SUSPENDED">
                          {t("Suspendu", "Suspended")}
                        </option>
                        <option value="DISABLED">
                          {t("Désactivé", "Disabled")}
                        </option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <Pagination data={data} page={page} setPage={setPage} />
    </>
  );
}
function AuditLog() {
  const { t, locale } = usePreferences();
  const { campuses } = useSession();
  const [campus, setCampus] = useState("");
  const [page, setPage] = useState(1);
  const { data, error, isPending } = useData<Collection>(
    `/platform/audit-logs${params({ campus_id: campus, page, page_size: 20 })}`,
  );
  return (
    <>
      <div className="section-heading">
        <h2>{t("Journal d’audit", "Audit log")}</h2>
      </div>
      <Field label={t("Périmètre", "Scope")}>
        <select
          value={campus}
          onChange={(e) => {
            setCampus(e.target.value);
            setPage(1);
          }}
        >
          <option value="">
            {t("Tous les établissements", "All campuses")}
          </option>
          {campuses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </Field>
      <ErrorNotice error={error} />
      <div className="panel">
        {isPending ? (
          <Loading />
        ) : !data?.items.length ? (
          <Empty
            title={t("Aucune activité à afficher", "No activity to display")}
          />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t("Date", "Date")}</th>
                  <th>{t("Action", "Action")}</th>
                  <th>{t("Auteur", "Actor")}</th>
                  <th>{t("Ressource", "Resource")}</th>
                  <th>{t("Détails", "Details")}</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td>{date(item.created_at, true, locale)}</td>
                    <td>{String(item.action)}</td>
                    <td>
                      {String(
                        item.actor_name ||
                          item.actor_user_id ||
                          t("Système", "System"),
                      )}
                    </td>
                    <td>
                      {String(item.entity_type)}
                      <div className="small muted">
                        {String(item.entity_id || "")}
                      </div>
                    </td>
                    <td className="wrap">
                      {Object.entries(
                        (item.details || {}) as Record<string, unknown>,
                      ).map(([key, value]) => (
                        <p className="small" key={key}>
                          {key} :{" "}
                          {typeof value === "object"
                            ? JSON.stringify(value)
                            : String(value)}
                        </p>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <Pagination data={data} page={page} setPage={setPage} />
    </>
  );
}
export function PlatformPage() {
  const { t } = usePreferences();
  const { isPlatform, campusId } = useSession();
  const [tab, setTab] = useState("campuses");
  const [roles, setRoles] = useState<RecordItem>();
  if (!isPlatform)
    return (
      <Empty
        title={t(
          "Cet espace est réservé à la plateforme",
          "This area is for platform administrators",
        )}
        description={t(
          "Votre compte ne dispose pas des permissions d’administration globale.",
          "Your account does not have platform administration permissions.",
        )}
      />
    );
  return (
    <>
      <PageTitle
        eyebrow={t(
          "ADMINISTRATION DE LA PLATEFORME",
          "PLATFORM ADMINISTRATION",
        )}
        title={t("Faire grandir CampusPulse", "Grow CampusPulse")}
        description={t(
          "Gérez vos établissements, les accès et les paramètres de la plateforme.",
          "Manage your campuses, access and platform settings.",
        )}
      />
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: "campuses", label: t("Établissements", "Campuses") },
          { id: "users", label: t("Comptes", "Accounts") },
          { id: "invitations", label: t("Invitations", "Invitations") },
          { id: "audit", label: t("Journal d’audit", "Audit log") },
          { id: "settings", label: t("Paramètres", "Settings") },
        ]}
      />
      {tab === "campuses" && (
        <ResourceManager
          path="/platform/campuses"
          editPath="/platform/campuses"
          title={t("Les établissements", "Campuses")}
          singular={t("un établissement", "a campus")}
          searchable
          fields={[
            {
              name: "name",
              label: t("Nom de l’établissement", "Campus name"),
              required: true,
            },
            {
              name: "code",
              label: t("Code court", "Short code"),
              required: true,
            },
            {
              name: "slug",
              label: t("Identifiant URL", "URL identifier"),
              required: true,
              hint: t(
                "Lettres minuscules, chiffres et tirets (ex. universite-antananarivo).",
                "Lowercase letters, numbers and hyphens (e.g. antananarivo-university).",
              ),
            },
            {
              name: "description",
              label: t("Description", "Description"),
              type: "textarea",
              nullable: true,
            },
            {
              name: "email",
              label: t("Email de contact", "Contact email"),
              type: "email",
              nullable: true,
            },
            { name: "phone", label: t("Téléphone", "Phone"), nullable: true },
            { name: "address", label: t("Adresse", "Address"), nullable: true },
            { name: "city", label: t("Ville", "City"), nullable: true },
            {
              name: "country",
              label: t("Pays", "Country"),
              required: true,
              defaultValue: "Madagascar",
            },
            {
              name: "website_url",
              label: t("Site web", "Website"),
              type: "url",
              nullable: true,
            },
            {
              name: "status",
              label: t("Statut", "Status"),
              type: "select",
              required: true,
              defaultValue: "ACTIVE",
              options: [
                { value: "ACTIVE", label: t("Actif", "Active") },
                { value: "SUSPENDED", label: t("Suspendu", "Suspended") },
                { value: "ARCHIVED", label: t("Archivé", "Archived") },
              ],
            },
          ]}
          columns={[
            { key: "code", label: t("Code", "Code") },
            { key: "name", label: t("Établissement", "Campus") },
            { key: "city", label: t("Ville", "City") },
            { key: "status", label: t("Statut", "Status"), type: "badge" },
          ]}
          extraActions={(item) => (
            <button
              className="icon-button"
              aria-label={t(
                `Gérer les rôles de ${item.name}`,
                `Manage roles for ${item.name}`,
              )}
              onClick={() => setRoles(item)}
            >
              <Shield size={16} />
            </button>
          )}
        />
      )}{" "}
      {tab === "users" && <PlatformUsers />}{" "}
      {tab === "invitations" &&
        (campusId ? (
          <RegistrationLinks key={campusId} />
        ) : (
          <Empty
            title={t("Créez d’abord un établissement", "Create a campus first")}
            description={t(
              "Choisissez ensuite un établissement dans le menu latéral pour créer des liens de rôle.",
              "Then select a campus in the sidebar to create role links.",
            )}
          />
        ))}{" "}
      {tab === "audit" && <AuditLog />}{" "}
      {tab === "settings" && <Settings path="/platform/settings" platform />}{" "}
      {roles && (
        <RolesDialog campus={roles} onClose={() => setRoles(undefined)} />
      )}
    </>
  );
}
