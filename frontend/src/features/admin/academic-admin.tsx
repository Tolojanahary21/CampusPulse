"use client";
import { useState } from "react";
import { usePreferences } from "@/components/preferences";
import { ErrorNotice, Field, Tabs } from "@/components/ui";
import { useSession } from "@/components/app-shell";
import { useAcademic, options } from "@/features/academic/use-academic";
import { useData } from "@/hooks/use-data";
import type { Collection } from "@/types";
import { ResourceManager, type FormField } from "./resource-manager";
export function AcademicAdmin() {
  const { t } = usePreferences();
  const status: FormField = {
    name: "status",
    label: t("Statut", "Status"),
    type: "select",
    defaultValue: "ACTIVE",
    required: true,
    options: [
      { value: "ACTIVE", label: t("Actif", "Active") },
      { value: "ARCHIVED", label: t("Archivé", "Archived") },
    ],
  };
  const common: FormField[] = [
    { name: "name", label: t("Nom", "Name"), required: true },
    { name: "code", label: t("Code", "Code"), required: true },
    {
      name: "description",
      label: t("Description", "Description"),
      type: "textarea",
      nullable: true,
    },
    status,
  ];

  const { campusId } = useSession();
  const [tab, setTab] = useState("years");
  const [program, setProgram] = useState("");
  const [level, setLevel] = useState("");
  const academic = useAcademic(campusId);
  return (
    <>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: "years", label: t("Années universitaires", "Academic years") },
          { id: "programs", label: t("Filières", "Programs") },
          { id: "levels", label: t("Niveaux", "Levels") },
          { id: "subjects", label: t("Matières", "Subjects") },
        ]}
      />
      <ErrorNotice error={academic.error} />
      {(tab === "levels" || tab === "subjects") && (
        <div className="form-grid">
          <Field label={t("Filière", "Program")}>
            <select
              value={program}
              onChange={(e) => {
                setProgram(e.target.value);
                setLevel("");
              }}
            >
              <option value="">
                {t("Choisir une filière", "Choose a program")}
              </option>
              {options(academic.programs)}
            </select>
          </Field>
          {tab === "subjects" && (
            <Field label={t("Niveau", "Level")}>
              <select value={level} onChange={(e) => setLevel(e.target.value)}>
                <option value="">
                  {t("Choisir un niveau", "Choose a level")}
                </option>
                {options(
                  academic.levels.filter((l) => l.program_id === program),
                )}
              </select>
            </Field>
          )}
        </div>
      )}
      {tab === "years" && (
        <ResourceManager
          key={`${campusId}-years`}
          path={`/campuses/${campusId}/academic-years`}
          editPath="/academic-years"
          title={t("Années universitaires", "Academic years")}
          singular={t("une année", "an academic year")}
          fields={[
            { name: "name", label: t("Nom", "Name"), required: true },
            {
              name: "starts_on",
              label: t("Date de début", "Start date"),
              type: "date",
              required: true,
            },
            {
              name: "ends_on",
              label: t("Date de fin", "End date"),
              type: "date",
              required: true,
            },
            {
              name: "is_current",
              label: t("Année en cours", "Current academic year"),
              type: "checkbox",
            },
            status,
          ]}
          columns={[
            { key: "name", label: t("Année", "Year") },
            { key: "starts_on", label: t("Début", "Start"), type: "date" },
            { key: "ends_on", label: t("Fin", "End"), type: "date" },
            {
              key: "is_current",
              label: t("En cours", "Current"),
              render: (i) => (i.is_current ? t("Oui", "Yes") : t("Non", "No")),
            },
            { key: "status", label: t("Statut", "Status"), type: "badge" },
          ]}
        />
      )}{" "}
      {tab === "programs" && (
        <ResourceManager
          key={`${campusId}-programs`}
          path={`/campuses/${campusId}/programs`}
          editPath="/programs"
          title={t("Les filières de l’établissement", "Campus programs")}
          singular={t("une filière", "a program")}
          fields={common}
          columns={[
            { key: "code", label: t("Code", "Code") },
            { key: "name", label: t("Filière", "Program") },
            { key: "status", label: t("Statut", "Status"), type: "badge" },
          ]}
          archive
        />
      )}{" "}
      {tab === "levels" && (
        <ResourceManager
          key={program}
          path={program ? `/programs/${program}/levels` : ""}
          editPath="/levels"
          title={t("Niveaux de la filière", "Program levels")}
          singular={t("un niveau", "a level")}
          fields={[
            ...common,
            {
              name: "level_order",
              label: t("Ordre du niveau", "Level order"),
              type: "number",
              min: 1,
              required: true,
              defaultValue: 1,
            },
          ]}
          columns={[
            { key: "code", label: t("Code", "Code") },
            { key: "name", label: t("Niveau", "Level") },
            { key: "level_order", label: t("Ordre", "Order") },
            { key: "status", label: t("Statut", "Status"), type: "badge" },
          ]}
          archive
        />
      )}{" "}
      {tab === "subjects" && (
        <ResourceManager
          key={level}
          path={level ? `/levels/${level}/subjects` : ""}
          editPath="/subjects"
          title={t("Matières du niveau", "Level subjects")}
          singular={t("une matière", "a subject")}
          fields={[
            ...common,
            {
              name: "credits",
              label: t("Crédits", "Credits"),
              type: "number",
              min: 0,
            },
            {
              name: "semester",
              label: t("Semestre", "Semester"),
              type: "number",
              min: 1,
            },
          ]}
          columns={[
            { key: "code", label: t("Code", "Code") },
            { key: "name", label: t("Matière", "Subject") },
            { key: "credits", label: t("Crédits", "Credits") },
            { key: "semester", label: t("Semestre", "Semester") },
            { key: "status", label: t("Statut", "Status"), type: "badge" },
          ]}
          archive
        />
      )}
    </>
  );
}
export function EnrollmentAdmin() {
  const { t } = usePreferences();
  const { campusId } = useSession();
  const academic = useAcademic(campusId);
  const users = useData<Collection>(
    `/campuses/${campusId}/users?page_size=100`,
  );
  return (
    <>
      <p className="form-help">
        {t(
          "Chaque année et chaque parcours disposent de leur propre inscription. Terminez une ancienne inscription, puis créez la suivante pour préserver l’historique.",
          "Each academic year and program has its own enrollment. Complete an existing enrollment before creating the next one to preserve the student’s history.",
        )}
      </p>
      <ErrorNotice error={academic.error || users.error} />
      <ResourceManager
        key={campusId}
        path={`/campuses/${campusId}/enrollments`}
        editPath="/enrollments"
        title={t("Inscriptions universitaires", "Academic enrollments")}
        singular={t("une inscription", "an enrollment")}
        searchable
        fields={[
          {
            name: "user_id",
            label: t("Étudiant", "Student"),
            type: "select",
            required: true,
            createOnly: true,
            options: users.data?.items.map((u) => ({
              value: u.id,
              label: `${u.first_name} ${u.last_name} · ${u.email}`,
            })),
          },
          {
            name: "program_level_id",
            label: t("Filière et niveau", "Program and level"),
            type: "select",
            required: true,
            createOnly: true,
            options: academic.levels.map((l) => ({
              value: l.id,
              label: `${l.program_name} · ${l.name}`,
            })),
          },
          {
            name: "academic_year_id",
            label: t("Année universitaire", "Academic year"),
            type: "select",
            required: true,
            createOnly: true,
            options: academic.years.map((y) => ({
              value: y.id,
              label: String(y.name),
            })),
          },
          {
            name: "enrollment_number",
            label: t("Numéro d’inscription", "Enrollment number"),
            required: true,
            createOnly: true,
          },
          {
            name: "status",
            label: t("Statut", "Status"),
            type: "select",
            required: true,
            defaultValue: "ACTIVE",
            options: [
              { value: "ACTIVE", label: t("Active", "Active") },
              { value: "PENDING", label: t("En attente", "Pending") },
              { value: "COMPLETED", label: t("Terminée", "Completed") },
              { value: "SUSPENDED", label: t("Suspendue", "Suspended") },
              { value: "CANCELLED", label: t("Annulée", "Cancelled") },
            ],
          },
          {
            name: "notes",
            label: t("Notes", "Notes"),
            type: "textarea",
            nullable: true,
          },
        ]}
        columns={[
          { key: "student_name", label: t("Étudiant", "Student") },
          { key: "program_name", label: t("Filière", "Program") },
          { key: "level_name", label: t("Niveau", "Level") },
          { key: "academic_year_name", label: t("Année", "Year") },
          {
            key: "enrollment_number",
            label: t("N° inscription", "Enrollment no."),
          },
          { key: "status", label: t("Statut", "Status"), type: "badge" },
        ]}
      />
    </>
  );
}
