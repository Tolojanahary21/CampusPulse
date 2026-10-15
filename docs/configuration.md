# Configuration des environnements et du courriel

## Trois fichiers distincts

| Fichier | Lecteur | Usage |
| --- | --- | --- |
| `.env` à la racine | Docker Compose | `POSTGRES_*`, ports hôtes et `COMPOSE_SMTP_HOST/PORT` ; interpolation de `compose.yaml` |
| `backend/.env` | FastAPI, Alembic, seed et worker | Base, sessions, CORS, stockage, SMTP et fonctionnalités |
| `frontend/.env.local` | Next.js | `NEXT_PUBLIC_API_URL` accessible au navigateur |

Copier les exemples avec `scripts/bootstrap.ps1`. Ne pas placer de secret dans une variable `NEXT_PUBLIC_*` : sa valeur est publique et peut être intégrée au JavaScript livré. Redémarrer les processus après une modification de configuration. Dans les conteneurs, les clés explicites de `environment:` prennent priorité sur `env_file`.

## Backend

Les noms précis et les valeurs par défaut sont définis dans `backend/.env.example` et `backend/app/core/config.py`.

| Variables | Rôle |
| --- | --- |
| `APP_ENV`, `APP_DEBUG` | Environnement et diagnostic ; désactiver le debug en production |
| `SECRET_KEY` | Secret applicatif aléatoire ; valeur distincte par environnement |
| `DATABASE_URL` | URL SQLAlchemy ; `postgresql+psycopg://utilisateur:motdepasse@localhost:5432/campus_db` pour la base locale demandée |
| `FRONTEND_URL` | URL externe du frontend, utilisée pour les liens d’invitation et de réinitialisation |
| `CORS_ORIGINS` | Liste JSON explicite des origines autorisées, par exemple `["http://localhost:3000"]` |
| `TRUSTED_HOSTS` | Liste JSON des noms d’hôtes acceptés ; ajouter le domaine public en production |
| `COOKIE_SECURE`, `SESSION_COOKIE_NAME`, `CSRF_COOKIE_NAME`, `SESSION_EXPIRE_HOURS` | Protection et durée de la session ; en production utiliser `COOKIE_SECURE=true`, les noms `__Host-campuspulse_session` et `__Host-campuspulse_csrf`, et une durée maximale de 24 h |
| `COOKIE_DOMAIN` | Doit rester vide en production avec les cookies `__Host-`; publier idéalement l’API sous le même nom d’hôte que l’interface |
| `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT_SECONDS` | Connexions maximales et attente avant saturation du pool, par processus API/worker |
| `PASSWORD_RESET_EXPIRE_MINUTES`, `INVITATION_EXPIRE_HOURS` | Validité respective des réinitialisations et invitations |
| `PUBLIC_REGISTRATION_ENABLED` | `true` par défaut : inscription étudiante publique ; `false` ferme ce parcours sans empêcher les invitations administratives |
| `OTP_SECRET_KEY` | Secret aléatoire pour protéger les codes ; vide, utilise `SECRET_KEY`. Ne jamais placer cette valeur dans le frontend |
| `OTP_TTL_MINUTES`, `OTP_MAX_ATTEMPTS`, `OTP_RESEND_COOLDOWN_SECONDS` | Durée du code (10 minutes), essais autorisés (5) et délai de renvoi (60 secondes) par défaut |
| `STORAGE_PATH`, `MAX_UPLOAD_SIZE_MB` | Répertoire privé et limite globale de téléversement |
| `SMTP_*` | Transport du courriel décrit ci-dessous |

La configuration locale utilise `localhost` pour PostgreSQL et Mailpit. Dans Compose, `postgres` et `mailpit` sont les noms DNS des services ; Compose remplace `DATABASE_URL`, `STORAGE_PATH` ainsi que l’hôte et le port SMTP. Les autres paramètres SMTP viennent de `backend/.env`. Ne pas mettre `localhost` pour joindre un autre conteneur.

Le service PostgreSQL installé sur cette machine est en version 15 ; la base locale retenue est `campus_db` sur le port 5432. Les exemples Docker et la CI restent sur PostgreSQL 16. Un mot de passe généré dans le `.env` racine ne configure pas ce service Windows existant : renseigner ses véritables identifiants dans `DATABASE_URL`, puis appliquer `python -m alembic upgrade head` depuis `backend/`. Encoder les caractères réservés d’URL dans le nom et le mot de passe de connexion.

Le `.env` racine préparé définit `POSTGRES_DB=campus_db` et `POSTGRES_PORT=5433` pour l’option Docker. Cette base Compose reste indépendante du service Windows de port 5432 : les identifiants et les comptes applicatifs ne sont pas automatiquement partagés.

La page `/register` propose uniquement les établissements actifs. L’inscription attend obligatoirement la validation d’un code OTP à six chiffres reçu par e-mail. Avant validation, aucun compte, rôle, adhésion ou session n’est créé. Après validation, le compte porte `email_verified_at`, une adhésion locale et le rôle `STUDENT` ; un administrateur attribue séparément l’année et le niveau académiques. Les comptes préexistants et les invitations administratives ne sont pas modifiés.

Les valeurs par défaut sont `OTP_TTL_MINUTES=10`, `OTP_MAX_ATTEMPTS=5` et `OTP_RESEND_COOLDOWN_SECONDS=60`. Chaque renvoi invalide le code précédent. Une demande peut être reprise dans le même onglet après rechargement ; après 24 heures, recommencer l’inscription. Les limites serveur par adresse e-mail et adresse IP restent applicables. Le navigateur ne conserve ni mot de passe ni code OTP.

La vérification ne peut pas être désactivée. `SMTP_ENABLED=false` conserve le courriel en attente et ne permet pas d’activer le compte. Le worker et le SMTP doivent fonctionner avant l’expiration du code. Une erreur de remise ne signifie jamais que l’adresse est vérifiée. Renseigner `OTP_SECRET_KEY` avec une valeur aléatoire longue, ou conserver le champ vide pour réutiliser `SECRET_KEY`.

Pour le mot de passe PostgreSQL interpolé dans l’URL Compose, employer une valeur aléatoire URL-safe (lettres, chiffres, tiret ou souligné). Les caractères réservés d’URL imposent un encodage et un override `DATABASE_URL` cohérent ; la valeur brute donnée à PostgreSQL reste inchangée. Modifier `POSTGRES_PASSWORD` après la création d’un volume ne change pas automatiquement le mot de passe déjà enregistré en base.

## SMTP et file d’envoi

Les codes OTP, messages de bienvenue, invitations et réinitialisations utilisent le service de courriel du backend. Les messages sont placés dans une file persistante ; `python -m app.mail_worker` assure la remise. Avec `SMTP_ENABLED=false`, les messages restent en attente : démarrer uniquement l’API ne suffit pas à les envoyer.

Ce worker déclenche également les notifications des annonces programmées lorsque leur période de visibilité commence, y compris lorsque SMTP est désactivé. `python -m app.mail_worker --once` traite un passage unique ; `--retry-failed` remet en attente les messages échoués encore valides. Une remise SMTP est « au moins une fois » : un arrêt entre l’envoi et la confirmation en base peut produire une nouvelle remise, malgré l’identifiant de message stable.

| Variable | Signification |
| --- | --- |
| `SMTP_ENABLED` | Active la remise des messages par le worker |
| `SMTP_HOST`, `SMTP_PORT` | Serveur et port du fournisseur |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | Identifiants SMTP ; laisser vides pour Mailpit |
| `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME` | Expéditeur présenté aux destinataires |
| `SMTP_STARTTLS` | Passage à TLS, généralement port 587 |
| `SMTP_SSL` | TLS dès la connexion, généralement port 465 |
| `SMTP_TIMEOUT_SECONDS` | Délai maximal d’une opération SMTP |
| `SMTP_ALLOW_INSECURE` | Dérogation explicite au TLS, destinée au relais local de développement |
| `MAIL_MAX_ATTEMPTS`, `MAIL_POLL_SECONDS` | Nombre maximal de tentatives et intervalle de relève du worker |

`SMTP_STARTTLS` et `SMTP_SSL` sont mutuellement exclusifs. Pour un fournisseur externe, renseigner une seule méthode TLS, ses identifiants et l’expéditeur autorisé. En production, laisser `SMTP_ALLOW_INSECURE=false`. Les exigences de domaine expéditeur, SPF/DKIM et quotas dépendent du fournisseur choisi et restent à configurer chez celui-ci.

Compose utilise Mailpit sur le port 1025 par défaut. Pour un vrai SMTP depuis les conteneurs, définir `COMPOSE_SMTP_HOST=smtp.votre-fournisseur.example` et `COMPOSE_SMTP_PORT=587` dans le `.env` racine ; définir `SMTP_STARTTLS=true`, `SMTP_SSL=false`, `SMTP_USERNAME`, `SMTP_PASSWORD` et l’expéditeur dans `backend/.env`. Ces réglages sont partagés par **backend et mail-worker**. `SMTP_PORT` à la racine désigne seulement le port hôte publié par Mailpit : il ne remplace pas `COMPOSE_SMTP_PORT`. Ne pas exposer l’interface Mailpit à Internet.

## Frontend, ports et cookies

En développement, `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`. Le navigateur doit pouvoir joindre cette adresse : `http://backend:8000` n’est pas une URL publique. Conserver `localhost` de part et d’autre ; mélanger `localhost` et `127.0.0.1` peut empêcher le partage attendu des cookies.

Dans le Dockerfile frontend, l’URL publique est un argument de build. Compose la construit à partir de `API_PORT`. Changer uniquement `frontend/.env.local` après le build ne réécrit pas le bundle : reconstruire l’image et adapter `build.args.NEXT_PUBLIC_API_URL` avec l’URL publique souhaitée.

La session utilise un cookie HttpOnly ; le cookie CSRF est lisible par le client. Le frontend transmet les cookies et `X-CSRF-Token` sur les mutations. Ne pas substituer au contrôle serveur une condition d’affichage dans l’interface.
