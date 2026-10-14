# Vérifications et limites de validation

Les tests fonctionnels et les vérifications d’exploitation sont distincts. Un build réussi ne démontre pas l’isolation de la base, et les tests SQLite ne prouvent pas le comportement PostgreSQL en concurrence.

## Vérifications réalisées dans l’environnement de livraison

| Vérification | État attesté |
| --- | --- |
| Helper d’archives privées | Dernière recette : 4 tests réussis (aller-retour binaire, refus de traversée de chemin, refus de lien symbolique, refus de cible non vide) ; non relancés pour la refonte de l’interface |
| Scripts PowerShell | Syntaxe de `bootstrap.ps1` et `database-backup.ps1` contrôlée par le parseur PowerShell |
| Diagramme de base | Généré depuis les déclarations Python : 34 tables, sans charger de configuration ni de base |
| Backend | Dernière recette : 52 tests Pytest réussis, dont inscription publique étudiante, refus des rôles privilégiés, transport SMTP réel sur boucle locale, sécurité, ciblage, annonces programmées et cycle de migrations SQLite ; non relancés pour cette modification de l’interface |
| Frontend | TypeScript, 16 tests unitaires et build de production Next.js 16.4 réussis ; les tests unitaires incluent 4 contrôles de formats et messages FR/EN |
| Navigateur | 15 parcours Playwright réussis avec Microsoft Edge : les 8 parcours métier existants et 7 parcours de langue, thème, persistance et affichage mobile. Les 7 parcours de préférences ont également été rejoués avec succès après la modification du titre de l’onglet |
| Inspection visuelle | Contrôles réalisés à 320, 390, 768 et 1440 pixels, ainsi que dans l’espace connecté à 1024 pixels. Neuf écrans connectés en anglais et en mode sombre contrôlés sans erreur JavaScript, erreur API ni débordement horizontal. Captures locales dans `.qa/` |
| PostgreSQL 15 isolé | Cycle `upgrade head`, `check`, `downgrade base`, `upgrade head` réussi ; parcours API administrateur, inscription STUDENT, doublon 409, refus des privilèges, santé et sessions réussis ; serveur arrêté après les contrôles |
| Base applicative PostgreSQL 15 | `localhost:5432/campus_db` : `upgrade head`, `check` et `current` réussis, 35 tables dont `alembic_version` ; compte administrateur créé, connexion PLATFORM_ADMIN, accès plateforme, santé et déconnexion vérifiés |
| SMTP Gmail | Connexion SSL/TLS sur le port 465 et authentification acceptées (235) ; aucun courriel envoyé pendant ce contrôle |
| PostgreSQL 16 | Prévu par la CI, non exécuté dans cet environnement |
| Docker Compose et Mailpit | Non exécutés localement : Docker est absent de l’environnement de livraison |
| Sauvegarde/restauration Compose complète | Non exécutée localement ; les tests du helper ne la remplacent pas |
| Diagrammes PlantUML | Syntaxe des trois fichiers validée par PlantUML ; trois rendus SVG générés dans `docs/rendered/` |

La refonte de l’interface a été contrôlée le 14 octobre 2026 avec Node.js 24. Les résultats backend et d’exploitation proviennent de la précédente recette locale sous Python 3.14 ; ils ne constituent pas une nouvelle exécution de ces suites. La CI distante n’a pas été exécutée. Le transport SMTP en boucle locale et l’authentification Gmail sont validés séparément ; la remise d’un courriel à un destinataire externe reste à vérifier. La bibliothèque de tests Starlette affiche un avertissement de dépréciation de son transport httpx ; il ne faisait échouer aucun test de la recette backend.

## Interface bilingue et thèmes

Les commandes de langue et d’apparence sont disponibles sur les pages publiques et dans les espaces étudiant et administrateur. L’interface propose le français et l’anglais ; les dates et les messages d’interface suivent la langue choisie. Les contenus publiés et les noms saisis restent dans leur langue d’origine. La langue de l’interface ne modifie pas les courriels du backend.

Le français est la langue initiale. Sans choix enregistré, le thème suit le mode clair ou sombre du système. Un choix explicite est conservé dans le stockage local du navigateur et synchronisé entre ses onglets, sans modifier le profil en base. Un refus de stockage ne doit empêcher ni l’utilisation des commandes ni la navigation ; après rechargement, les valeurs initiales s’appliquent dans ce cas.

Les sept scénarios de `frontend/e2e/preferences.spec.ts` ont réussi : persistance après navigation et rechargement, synchronisation entre onglets, messages de connexion FR/EN, espaces étudiant et administrateur en anglais, absence de débordement à 390 pixels en mode sombre, suivi du thème système et fonctionnement sans stockage des préférences. Les quatre tests unitaires de `frontend/tests/localization.test.ts` ont également réussi. Ces vérifications couvrent les parcours exécutés ; elles ne remplacent pas une recette complète d’accessibilité sur les navigateurs et appareils de production.

Les photographies de l’accueil sont stockées localement. Les [crédits photographiques](../frontend/public/images/CREDITS.md) précisent leurs auteurs, sources et conditions d’utilisation ; elles illustrent la vie universitaire sans présenter un établissement client.

## Reproduire

Depuis `backend/`, après installation de `requirements-dev.txt` :

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Les fixtures isolent chaque test dans SQLite en mémoire et un stockage temporaire. Elles remplacent l’URL de base et désactivent le SMTP applicatif. La suite couvre notamment l’inscription étudiante publique, l’authentification, la révocation, le CSRF, les invitations, les permissions et le transport courriel. Les scénarios exacts résident dans `backend/tests/`.

Pour reproduire les migrations et les parcours API sur un PostgreSQL isolé, depuis la racine avec les binaires PostgreSQL 15 installés :

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\check_postgres_local.py --bin-dir "C:\Program Files\PostgreSQL\15\bin"
```

Ce script crée un nouveau cluster sous `.qa/postgres-validation-*`, sur `127.0.0.1:55432` par défaut ; `--port` permet de choisir un autre port libre. Il définit ses propres secrets et sa propre URL de base, puis arrête son serveur à la fin. Les fichiers de contrôle restent dans `.qa/`. Le cycle de retour à zéro s’applique uniquement à ce cluster de test : la base applicative `campus_db` n’est pas utilisée. Ces parcours séquentiels ne constituent pas un test de concurrence PostgreSQL.

Depuis `frontend/` :

```powershell
npm run typecheck
npm test
npm run build
```

Pour les parcours navigateur, le venv `backend/.venv` doit exister. Les tests démarrent leurs propres serveurs sur les ports 8001 et 3101 et utilisent uniquement `.qa/e2e.sqlite3` et `.qa/e2e-storage`, sans toucher à la base applicative. Le port 3101 évite une plage de ports réservée par Windows sur cette machine. Depuis `frontend/`, avec Edge installé sous Windows :

```powershell
$env:PLAYWRIGHT_CHANNEL='msedge'
npm run test:e2e
Remove-Item Env:\PLAYWRIGHT_CHANNEL
```

Avec Chromium Playwright : `npx playwright install chromium`, puis `npm run test:e2e` sans `PLAYWRIGHT_CHANNEL`. L’exécution doit autoriser le lancement et l’arrêt des processus de test ; une sandbox Windows restrictive peut empêcher leur nettoyage.

Depuis la racine, pour le helper indépendant :

```powershell
python -m unittest discover -s scripts -p test_storage_archive.py
```

## CI livrée

Le workflow `.github/workflows/ci.yml` prévoit quatre jobs sans publication :

1. Installation backend, migration SQLite, tests Pytest et tests du helper d’archives.
2. PostgreSQL 16 isolé, migration `upgrade head`, comparaison Alembic, `downgrade base` et nouvelle montée. Cette procédure s’applique à une base CI vide, jamais à une base réelle.
3. Installation frontend, tests unitaires, TypeScript et build Next.js.
4. Parcours Playwright dans Chromium avec base de démonstration isolée.

La suite Pytest force SQLite. Le job PostgreSQL 16 vérifie les migrations ; il ne transforme pas cette suite en tests d’API PostgreSQL. Les parcours API PostgreSQL 15 attestés ci-dessus proviennent du script local distinct. La CI distante n’a pas été exécutée par la simple création du fichier.

## Recette requise avant production

Exécuter les parcours des trois acteurs, le ciblage multi-parcours et les refus d’accès par changement d’identifiant sur l’environnement cible. Rejouer les migrations sur la version PostgreSQL retenue et tester les accès concurrents, encore non évalués. Vérifier une restauration complète base/fichiers, le transport SMTP choisi avec TLS et l’accessibilité clavier/mobile de l’interface. Les [parcours de démonstration](demonstration.md) donnent une trame reproductible.

Les limites fonctionnelles et d’exploitation sont précisées dans [la couverture](couverture-fonctionnelle.md) et [le guide de déploiement](deploiement.md). Aucun déploiement de production, certification de sécurité ou test de charge n’est attesté par cette livraison locale.
