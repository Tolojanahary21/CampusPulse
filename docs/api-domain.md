# API métier CampusPulse

Préfixe `/api/v1`, session cookie + `X-CSRF-Token` pour mutations. Toutes les listes acceptent `page=1&page_size=20` (maximum 100), retournent `{items,total,page,page_size}`. Dates UTC ISO, identifiants chaînes UUID. Les objets retournent leurs champs métier, `id`, `created_at`, `updated_at` ; aucun secret ni chemin de stockage.

## Inscription et création des comptes

- `GET /auth/registration-options` public : `{enabled,campuses:[{id,name,code}]}`. Cette liste de référence, sans pagination, contient seulement les établissements actifs ; elle est vide si l’inscription est désactivée.
- `POST /auth/register` public : `{campus_id,email,first_name,last_name,password}` ; mot de passe de 12 à 128 caractères. Un lien de rôle peut ajouter `invitation_token`; le campus et le rôle sont alors vérifiés côté serveur. Retour 202 `{verification_required:true,challenge_id,email,expires_at,resend_available_at,message}` ; 403 si fermé, 404 pour un établissement ou lien indisponible, 409 pour une adresse déjà utilisée, 422 pour une entrée invalide et 429 en cas de dépassement de la limite de tentatives. Une demande temporaire et un code en file SMTP sont créés ; aucun compte n’existe encore.
- `GET /auth/registration-link/{token}` public : vérifie un lien de rôle partageable. Le token est aléatoire, stocké sous forme de hash, valable 30 jours et utilisable une seule fois après vérification OTP.
- `POST /platform/registration-links` administrateur de plateforme : `{campus_id,role}` pour STUDENT, CAMPUS_ADMIN, CONTENT_PUBLISHER ou MODERATOR. Renvoie le token partageable une seule fois ; PLATFORM_ADMIN ne peut pas être créé par inscription.
- `POST /auth/verify-email` public : `{challenge_id,code}`. Après validation du code à six chiffres, retour 201 `{message}` et création atomique du compte vérifié, de son adhésion et de son rôle `STUDENT`. Code incorrect, expiré ou déjà utilisé : refus ; essais limités. Aucun champ de rôle ou d’inscription académique n’est accepté. Aucune session n’est créée : `POST /auth/login` permet ensuite la connexion.
- `POST /auth/resend-verification` public : `{challenge_id}`. Retour 200 avec les métadonnées actualisées de vérification ; l’ancien code est invalidé. Retour 429 avec `Retry-After` pendant le délai de renvoi. Les demandes de plus de 24 heures doivent être recommencées. Aucun code n’est retourné par l’API.
- `POST /campuses/{id}/users` administratif : `{email,first_name,last_name,role}`. Un administrateur d’établissement peut inviter STUDENT, CONTENT_PUBLISHER et MODERATOR dans son établissement ; CAMPUS_ADMIN exige un administrateur de plateforme. Les inscriptions académiques restent administrées via `/campuses/{id}/enrollments`.

Les endpoints publics d’authentification n’exigent pas de jeton CSRF, mais restent soumis au contrôle d’origine. Le contrat complet de connexion, récupération et profil figure dans [implementation-contract.md](implementation-contract.md).

## Plateforme

- `GET /campuses` : établissements accessibles.
- `GET/POST /platform/campuses`, `GET/PATCH /platform/campuses/{id}`. Champs : `name,code,slug,description?,email?,phone?,address?,city?,country='Madagascar',website_url?,status='ACTIVE'`.
- `POST /platform/campuses/{id}/admins` : `{user_id,role='CAMPUS_ADMIN',expires_at?}`. Rôles délégués possibles : CAMPUS_ADMIN, CONTENT_PUBLISHER, MODERATOR, STUDENT.
- `GET /campuses/{id}/roles`, `DELETE /roles/{id}` : attribution et révocation traçables. `GET /platform/users?q=`, `PATCH /platform/users/{id}/status` : `{status:ACTIVE|SUSPENDED|DISABLED}`.
- `GET /platform/audit-logs?campus_id=`. `GET/PATCH /platform/settings` : `{platform_name,support_email?,maintenance_message?}`.
- `GET/PATCH /campuses/{id}/settings` : `{allow_announcement_comments,allow_student_posts,allow_student_comments,allow_student_reactions,max_upload_size_mb}`.

## Académique

- `GET/POST /campuses/{id}/academic-years` : `{name,starts_on:'YYYY-MM-DD',ends_on,is_current=false,status:'ACTIVE'|'ARCHIVED'}` ; `PATCH /academic-years/{id}`.
- `GET/POST /campuses/{id}/programs` : `{name,code,description?,status:'ACTIVE'|'ARCHIVED'}` ; `PATCH/DELETE /programs/{id}` (DELETE archive).
- `GET/POST /programs/{id}/levels` : `{name,code,level_order,description?,status}` ; `PATCH/DELETE /levels/{id}`.
- `GET/POST /levels/{id}/subjects` : `{name,code,description?,credits?,semester?,status}` ; `PATCH/DELETE /subjects/{id}`.
- `GET/POST /campuses/{id}/enrollments` : `{user_id,program_level_id,academic_year_id,enrollment_number,status='ACTIVE',notes?}`. Statuts PENDING, ACTIVE, COMPLETED, CANCELLED, SUSPENDED. `GET/PATCH /enrollments/{id}` (PATCH statut et notes seulement). `GET /students/{id}/enrollments` historique.
- Inscriptions enrichies : `student_name,student_email,program_name,level_name,academic_year_name,campus_name`.

## Annonces, documents, événements

- `GET /announcements?q=&campus_id=&status=&scope=&program_id=&level_id=&year_id=&manage=false` ; idem `/documents`, avec `category=&subject_id=`. Par défaut seuls contenus publiés visibles ; `manage=true` inclut les brouillons administrables.
- `POST /announcements` : `{title,content,summary?,campus_id?,announcement_type='GENERAL',scope='CAMPUS',status='DRAFT',is_pinned=false,allow_comments=false,starts_at?,ends_at?,program_ids:[],level_ids:[],year_ids:[]}`. Types GENERAL, ADMINISTRATIVE, ACADEMIC, EVENT, URGENT.
- `POST /documents` : `{title,description?,campus_id?,file_asset_id,subject_id?,category='COURSE',scope='CAMPUS',status='DRAFT',program_ids:[],level_ids:[],year_ids:[]}`. Catégories COURSE, EXERCISE, SOLUTION, EXAM, SUMMARY, OTHER.
- Pour les deux : `GET/PATCH /{collection}/{id}`, `POST /{collection}/{id}/publish`, `POST /{collection}/{id}/archive`. Modifier campus ou portée nécessite permissions source ET destination. Les créations acceptent PUBLISHED avec les mêmes contrôles que publish.
- `GET/POST /announcements/{id}/comments` : `{content}`. Les commentaires doivent être activés dans l'annonce et les paramètres de l'établissement.
- `GET/POST /events?campus_id=&manage=false`, `GET/PATCH /events/{id}` : `{campus_id?,announcement_id?,title,description,location?,starts_at,ends_at,registration_url?,status='DRAFT'}`. Statuts DRAFT, PUBLISHED, CANCELLED, COMPLETED.
- `POST /files/upload` multipart `{file,campus_id?}` -> `{id,original_filename,mime_type,size_bytes,...}` ; `GET /files/{id}/download` exige un document publié visible qui référence ce fichier. Formats PDF, TXT, PNG, JPEG, DOCX, XLSX, PPTX ; maximum configurable.

## Communauté

- `GET/POST /community/posts?campus_id=&q=` : `{campus_id,title?,content,post_type='DISCUSSION'}` ; types QUESTION, DISCUSSION, RESOURCE, ANNOUNCEMENT, OTHER.
- `GET/PATCH/DELETE /community/posts/{id}` : PATCH `{title?,content?}`, DELETE retrait logique.
- Publications enrichies : `author_name,comment_count,reaction_count,my_reaction_id`.
- `GET/POST /community/posts/{id}/comments` : `{content,parent_comment_id?}`, enrichissement `author_name` ; `PATCH/DELETE /community/comments/{id}`.
- `POST /community/reactions` : `{post_id? OU comment_id?,reaction_type:'LIKE'}` ; `DELETE /community/reactions/{id}`.
- `POST /reports` : `{post_id? OU comment_id?,reason:'SPAM'|'HARASSMENT'|'INAPPROPRIATE'|'MISINFORMATION'|'OTHER',description?}`.
- `GET /moderation/reports?campus_id=&status=` (OPEN par défaut), enrichissement `post_title,content,reporter_name`.
- `PATCH /moderation/reports/{id}` : `{status:'RESOLVED'|'DISMISSED',action:'HIDE'|'RESTORE'|'NONE',reason}`.
- `POST /moderation/actions` : `{post_id? OU comment_id?,action:'HIDE'|'RESTORE',reason}`.

## Notifications / tableau de bord

- `GET /notifications?unread=false`, `PATCH /notifications/{id}/read`, `POST /notifications/read-all`. Champs `notification_type,title,message,link,read_at,campus_id`.
- `GET /dashboard/summary?campus_id=` -> `{campuses,students,announcements,documents,events,posts,unread_notifications,pending_reports,enrollments}` (indicateurs autorisés).
- `GET /dashboard/activity?campus_id=` -> collection `{id,type,title,created_at,link,campus_id}`.

Historique documentaire ACTIVE + COMPLETED ; annonces ciblées ACTIVE seulement. Cibles OR dans une dimension, AND entre dimensions d'une même inscription. Les auteurs/modérateurs peuvent consulter leurs publications masquées ; aucun autre étudiant ne les voit. Les objets d'un autre établissement renvoient 403/404. Erreurs validation 422, conflit 409.
