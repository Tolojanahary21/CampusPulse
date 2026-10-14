# Contrat d’implémentation CampusPulse

API REST `/api/v1`, backend FastAPI synchrone + SQLAlchemy 2, Pydantic 2. Frontend Next.js App Router + TypeScript + TanStack Query. PostgreSQL production, SQLite pour les tests locaux. UUID représentés en chaînes dans l’API. Dates ISO UTC. Interface française et anglaise.

## Conventions partagées

- GET collections : `{items: [...], total: number, page: number, page_size: number}`. Paramètres `page=1`, `page_size=20`, `q`, `campus_id` selon domaine. Pour petites collections imbriquées, même enveloppe.
- GET détail / POST / PATCH : objet direct. DELETE : 204.
- Erreurs FastAPI `{detail: string | validation[]}`.
- Base : `app.db.base.Base`; session : `app.db.session.get_db`, `SessionLocal`, `engine`.
- Modèles centralisés `app.models` (domaines créés par agent backend). Tous ont un UUID string généré `str(uuid4())`. Champs communs `created_at`, `updated_at` UTC.
- Auth implémentée par agent principal dans `app.api.auth`. `get_current_user(request, db=Depends(get_db))` dans `app.core.dependencies` retourne un modèle User. Permissions et périmètres domaines appartiennent à `app.permissions`.
- Modèles d’auth à fournir dans `app.models` : `User(id,email,password_hash,first_name,last_name,phone?,avatar_url?,status='ACTIVE',email_verified_at?,last_login_at?,created_at,updated_at)`, `UserSession(id,user_id,token_hash,csrf_token,expires_at,revoked_at?,created_at,last_used_at?,ip_address?,user_agent?)`, `PasswordResetToken(id,user_id,token_hash,expires_at,used_at?,created_at)`, `RoleAssignment(id,user_id,role,campus_id?,granted_by_user_id?,expires_at?,revoked_at?,created_at)`, `CampusMembership(id,user_id,campus_id,membership_type='STUDENT',status='ACTIVE',created_at,joined_at)`, `NotificationPreference(id,user_id,email_announcements=True,email_community=False)`.
- Rôles : PLATFORM_ADMIN global ; CAMPUS_ADMIN, CONTENT_PUBLISHER, MODERATOR, STUDENT rattachés à un campus.
- Paramètres `app.core.config.settings`: app_name, app_env, debug, database_url, frontend_url, cors_origins (list[str]), secret_key, session_cookie_name, session_expire_hours, cookie_secure, storage_path, max_upload_size_mb, smtp_host, smtp_port, smtp_username, smtp_password, smtp_starttls, smtp_ssl, smtp_from_email, smtp_from_name, smtp_timeout_seconds, smtp_enabled, password_reset_expire_minutes, public_registration_enabled.
- Cookies : `campuspulse_session` HttpOnly ; `campuspulse_csrf` lisible côté frontend. Envoyer `X-CSRF-Token` et credentials include sur mutations. Auth login/register/forgot/reset/invitation accept sont exemptés ; contrôles Origin côté serveur.
- Frontend utilise `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`.

## Auth et profil (agent principal)

- GET `/auth/registration-options` -> `{enabled:boolean,campuses:[{id,name,code}]}` sans authentification ; établissements actifs seulement, liste vide si inscription désactivée.
- POST `/auth/register` `{campus_id,email,first_name,last_name,password}` -> 202 `{verification_required:true,challenge_id,email,expires_at,resend_available_at,message}`. Mot de passe de 12 à 128 caractères ; champs supplémentaires refusés. Conserve une demande temporaire et place un code OTP dans la file SMTP. Aucun compte, droit ou session avant validation.
- POST `/auth/verify-email` `{challenge_id,code}` -> 201 `{message}`. Code de six chiffres, à usage unique, expirant et avec essais limités. Crée atomiquement le compte `ACTIVE` avec `email_verified_at`, une adhésion et le rôle `STUDENT`, puis supprime la demande temporaire. L’établissement doit toujours être actif. Connexion séparée via `/auth/login`.
- POST `/auth/resend-verification` `{challenge_id}` -> 200 même réponse que l’inscription. Délai minimal de renvoi, invalidation du code précédent et limites serveur par IP/adresse. Aucun code ni secret dans les réponses HTTP. Après 24 heures, recommencer l’inscription.
- La vérification est obligatoire même si SMTP est désactivé. Les comptes déjà existants et les invitations administratives sont conservés.
- POST `/auth/login` `{email,password}` -> profil (cookies).
- GET `/auth/me` et `/users/me` -> `{id,email,first_name,last_name,phone,avatar_url,status,roles:[{id,role,campus_id}],campuses:[{id,name,code}],...}`.
- POST `/auth/logout` ; POST `/auth/forgot-password` `{email}` ; POST `/auth/reset-password` `{token,password}`.
- POST `/auth/accept-invitation` `{token,password}` (même jetons reset pour compte créé par admin).
- PATCH `/users/me` `{first_name,last_name,phone?}` ; PATCH `/users/me/password` `{current_password,new_password}`.
- GET/PATCH `/notification-preferences` `{email_announcements,email_community}`.
- POST `/campuses/{campus_id}/users` `{email,first_name,last_name,role='STUDENT'}` crée compte/adhésion/rôle et envoie invitation ; GET `/campuses/{campus_id}/users` collection. Accès réservé aux administrateurs ; un administrateur d’établissement peut inviter STUDENT, CONTENT_PUBLISHER et MODERATOR. CAMPUS_ADMIN exige un administrateur de plateforme.

## Domaines (agent backend)

Tous les endpoints du cahier des charges (sections 8.2–8.7) sauf profil/préférences/auth/utilisateurs de campus ci-dessus. Exposer `router` dans `app.api.domain`. Les signatures/objets doivent être documentés dans `docs/api-domain.md` au fur et à mesure pour le frontend. Les listes retournent enveloppe standard ; sérialisation champs ORM publics sans secrets ni storage_key. Champs `program_ids`, `level_ids`, `year_ids` listes pour ciblage sur annonces/documents. Scope CAMPUS/TARGETED/PLATFORM ; status DRAFT/PUBLISHED/ARCHIVED.

Annonces : title, content, summary?, campus_id?, announcement_type, scope, status, is_pinned, allow_comments, starts_at?, ends_at?, program_ids, level_ids, year_ids. Documents : title,description?,campus_id?,file_asset_id,subject_id?,category,scope,status,program_ids,level_ids,year_ids. Upload multipart `file` et `campus_id` -> FileAsset public avec id. Communauté : campus_id,title?,content. Réactions `{post_id?,comment_id?,reaction_type:'LIKE'}`. Signalements `{post_id?,comment_id?,reason,description?}`. Modération PATCH report `{status:'RESOLVED'|'DISMISSED',action:'HIDE'|'RESTORE'|'NONE',reason}`.

Sécurité : accès campus actif + rôle valide ; refus IDOR entre campus ; cibles OR dans chaque dimension et AND entre dimensions pour une même inscription ACTIVE ou COMPLETED (annonces ACTIVE uniquement). Historique conservé. Validation références cross-campus. Téléchargement uniquement via permissions du document publié. Notifications internes publication ciblées. Audit mutations administratives et modération.

## Choix V1

Inscription publique étudiante activée par défaut et disponible sur `/register` depuis l’accueil et la connexion ; les autres rôles sont créés par les administrateurs. `PUBLIC_REGISTRATION_ENABLED=false` ferme uniquement l’inscription publique. L’administrateur attribue séparément l’inscription académique qui ouvre les contenus ciblés. Plusieurs parcours autorisés. Commentaires officiels désactivés par défaut. Contenus et comptes archivés/désactivés. Attachments communautaires facultatifs hors première version ; documents pédagogiques privés pris en charge. Aucun déploiement distant demandé : livraison dans le dossier local avec Docker Compose et guides d’exploitation.
