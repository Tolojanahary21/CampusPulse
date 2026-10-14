# CampusPulse

CampusPulse réunit les annonces officielles, les ressources pédagogiques et la communauté de plusieurs établissements universitaires. Le backend applique les permissions par établissement et conserve l’historique des inscriptions.

Le projet comprend une API FastAPI/SQLAlchemy, une interface Next.js/TypeScript, PostgreSQL, les migrations Alembic et des tests. L’interface est disponible en français et en anglais, avec un mode clair et un mode sombre. Les étudiants peuvent créer leur compte depuis l’accueil ; les autres rôles sont créés par les administrateurs. Les sessions sont conservées côté serveur et les fichiers dans un stockage privé local.

## Langue et apparence

Les commandes **FR / EN** et **clair / sombre** sont accessibles sur l’accueil, les pages de connexion et d’inscription, ainsi que dans l’espace connecté. Elles s’appliquent aux libellés, formulaires, messages de l’interface et formats de date. Les annonces, documents, messages et autres contenus publiés conservent leur langue d’origine ; les courriels ne sont pas traduits automatiquement.

Au premier accès, la langue est le français et le thème suit la préférence du système. Un choix explicite est mémorisé dans le navigateur pour les visites suivantes et partagé entre ses onglets. Ces préférences ne sont pas enregistrées sur le compte utilisateur. Si le navigateur refuse le stockage local, les commandes restent utilisables pendant la navigation.

Les photographies de l’accueil sont servies depuis le projet ; leurs sources et auteurs sont indiqués dans les [crédits photographiques](frontend/public/images/CREDITS.md).

## Création des comptes

Depuis l’accueil ou la connexion, ouvrir `/register`, choisir un établissement actif et renseigner son identité, son adresse e-mail et un mot de passe d’au moins 12 caractères. Un code OTP à six chiffres est envoyé par e-mail. Le compte étudiant, son adhésion et son rôle sont créés uniquement après validation du code ; aucune connexion n’est possible avant cette étape. Le code est valable 10 minutes, avec 5 essais au maximum et un délai de 60 secondes avant renvoi, selon les paramètres `OTP_*` du backend.

L’étudiant accède aux contenus destinés à l’ensemble de son établissement. Un administrateur doit ensuite lui attribuer son année et son niveau pour ouvrir les contenus académiques ciblés. L’administration d’établissement invite les étudiants, les responsables de publication et les modérateurs ; seule l’administration de plateforme nomme les administrateurs d’établissement. Aucun rôle privilégié n’est proposé à l’inscription publique.

Le worker `python -m app.mail_worker` doit être lancé avec un SMTP configuré pour remettre les codes. Désactiver SMTP ne supprime pas la vérification : l’inscription reste en attente. Les comptes existants et les invitations administratives conservent leur parcours.

L’inscription est activée par `PUBLIC_REGISTRATION_ENABLED=true` dans `backend/.env`. Il faut créer au moins un établissement actif dans `/app/platform` pour qu’un étudiant puisse le choisir. Le premier administrateur peut être créé avec `python -m app.create_admin --email votre-adresse@example.org` depuis `backend/`, après les migrations.

## Démarrage avec Docker Desktop

Prérequis : Docker Desktop avec les conteneurs Linux et Docker Compose v2. Depuis PowerShell, à la racine du projet :

```powershell
.\scripts\bootstrap.ps1
```

Renseigner `SECRET_KEY` dans `backend/.env` avec une valeur aléatoire longue. Changer le mot de passe PostgreSQL public de développement dans `.env` si nécessaire. Ces fichiers sont ignorés par Git. Le script conserve les fichiers déjà présents sans afficher leur contenu.

```powershell
docker compose up --build -d
docker compose ps
```

| Service | Adresse locale |
| --- | --- |
| Application | <http://localhost:3000> |
| API interactive | <http://localhost:8000/docs> |
| Santé API et base | <http://localhost:8000/health> |
| Boîte de réception de développement Mailpit | <http://localhost:8025> |
| PostgreSQL Compose | `localhost:5432` par défaut ; port défini par `POSTGRES_PORT` dans `.env` |
| SMTP Mailpit | `localhost:1025` |

Les migrations sont exécutées au démarrage du backend. Le worker de courriels fonctionne dans un service distinct. Mailpit capture les courriels localement ; il ne les remet pas aux véritables destinataires.

Le `.env` local préparé utilise le port `5433` pour PostgreSQL Compose, afin de laisser `5432` au service PostgreSQL Windows existant. Ces deux bases sont indépendantes ; l’application lancée directement suit `DATABASE_URL` dans `backend/.env`.

## Données de démonstration

Choisir explicitement un mot de passe de démonstration d’au moins 12 caractères, puis exécuter le seed. Exemple PowerShell évitant d’inscrire le mot de passe dans l’historique des commandes :

```powershell
$demoCredential = Get-Credential -UserName demo -Message 'Mot de passe des comptes de démonstration'
$env:DEMO_PASSWORD = $demoCredential.GetNetworkCredential().Password
docker compose exec -e DEMO_PASSWORD backend python -m app.seed
Remove-Item Env:\DEMO_PASSWORD
Remove-Variable demoCredential
```

| Parcours | Identifiant |
| --- | --- |
| Administrateur de plateforme | `admin@campuspulse.test` |
| Administrateur d’établissement | `responsable@campuspulse.test` |
| Étudiant | `etudiant@campuspulse.test` |

Utiliser les données de démonstration uniquement dans un environnement isolé. Le seed n’est jamais lancé automatiquement par Compose. Voir les [parcours de démonstration](docs/demonstration.md).

## Développement Windows sans conteneur applicatif

Installer Python 3.13 ou supérieur et Node.js 24. La configuration locale demandée utilise PostgreSQL 15, déjà installé sur cette machine, avec la base `campus_db` sur `localhost:5432`. Docker Compose et la CI utilisent PostgreSQL 16 ; il est aussi possible de garder seulement PostgreSQL et Mailpit dans Docker avec `docker compose up -d postgres mailpit`.

Après `scripts/bootstrap.ps1`, renseigner `DATABASE_URL` dans `backend/.env` pour atteindre PostgreSQL, par exemple `postgresql+psycopg://utilisateur:motdepasse@localhost:5432/campus_db`. Le `.env` de la racine configure uniquement Docker Compose ; il ne configure pas le backend lancé directement et ne change pas les identifiants de PostgreSQL déjà installé. Les identifiants doivent correspondre à un compte autorisé sur la base choisie.

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Dans un second terminal, depuis `backend/`, lancer la remise des courriels :

```powershell
.\.venv\Scripts\python.exe -m app.mail_worker
```

Dans un troisième terminal, depuis la racine :

```powershell
Set-Location frontend
npm ci
npm run dev
```

Pour les données de démonstration locales, définir `DEMO_PASSWORD` puis lancer `python -m app.seed` avec le Python du venv depuis `backend/`. Pour Mailpit local, utiliser `SMTP_HOST=localhost`, `SMTP_PORT=1025`, `SMTP_ENABLED=true`, sans TLS. Pour un vrai fournisseur, voir la [configuration SMTP](docs/configuration.md).

## Vérifications

```powershell
# Depuis backend/
.\.venv\Scripts\python.exe -m pytest -q

# Depuis frontend/
npm run typecheck
npm test
npm run build
```

Validation de l’interface bilingue : **16 tests frontend, 15 parcours navigateur, contrôle TypeScript et build de production Next.js 16.4 réussis**. Les vues ont été inspectées entre 320 et 1440 pixels ; neuf écrans connectés en anglais et en mode sombre ont été contrôlés sans erreur JavaScript, erreur API ni débordement horizontal. Les **52 tests backend et 4 tests de sauvegarde de fichiers** de la précédente recette n’ont pas été relancés pour cette modification de l’interface. Les migrations et les parcours API d’inscription/permissions ont aussi été vérifiés sur PostgreSQL 15 isolé. La base locale `campus_db` a été migrée et sa connexion administrateur vérifiée. La CI prévoit PostgreSQL 16 mais n’a pas été exécutée. Docker, la concurrence PostgreSQL, la restauration complète et la remise SMTP à un destinataire externe restent à vérifier ; voir [validation et limites](docs/validation.md).

## Documentation

- [Cahier des charges revu](docs/cahier-des-charges.md), [source intégrale](docs/cahier-des-charges-source.txt) et [couverture fonctionnelle](docs/couverture-fonctionnelle.md).
- [Décisions et permissions](docs/permissions.md), [contrat partagé](docs/implementation-contract.md) et [API métier](docs/api-domain.md).
- [Environnement et SMTP](docs/configuration.md), [production](docs/deploiement.md), [sauvegarde et restauration](docs/sauvegarde-restauration.md).
- Diagrammes PlantUML : [cas d’utilisation](docs/campuspulse-use-case.puml), [classes](docs/campuspulse-class-diagram.puml), [base de données](docs/database-schema.puml).
- Diagrammes consultables sans outil : [cas d’utilisation SVG](docs/rendered/campuspulse-use-case.svg), [classes SVG](docs/rendered/campuspulse-class-diagram.svg), [base de données SVG](docs/rendered/database-schema.svg).

Les fichiers `.env`, les fichiers privés et les sauvegardes ne doivent pas être versionnés. `docker compose down` conserve les volumes ; l’option `-v` les détruit et ne fait pas partie de la procédure de mise à jour.
