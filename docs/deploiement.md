# Mise en production et maintenance

Le fichier `compose.yaml` livré est prévu pour le développement local. Il publie ses ports sur `127.0.0.1` et utilise Mailpit. Aucun hébergement distant n’est créé par ce dépôt ou par sa CI.

## Préparer un environnement isolé

1. Créer une instance PostgreSQL 16 et un stockage privé persistant. Éviter de partager la base et les volumes avec le développement.
2. Configurer les secrets backend et le compte SMTP dans le gestionnaire de secrets de l’hébergement, ou dans un fichier protégé non versionné.
3. Définir `APP_ENV=production`, `APP_DEBUG=false`, `COOKIE_SECURE=true`, un `SECRET_KEY` aléatoire, l’URL PostgreSQL et l’URL HTTPS du frontend.
4. Limiter `CORS_ORIGINS` aux origines publiques exactes et utiliser un reverse proxy HTTPS. Servir de préférence l’interface et `/api/v1` sous le même domaine. Acheminer aussi le contrôle de santé interne vers l’API.
5. Construire le frontend avec l’URL publique de l’API. Les arguments de build et les variables runtime sont deux étapes distinctes.
6. Configurer le relais SMTP TLS, l’expéditeur et le worker. Avec Compose, définir `COMPOSE_SMTP_HOST/PORT` dans le fichier racine, puis les identifiants et TLS dans `backend/.env` ; ces paramètres servent au backend et au worker. Retirer Mailpit des services exploités.

Le proxy doit transférer le chemin `/api/v1` sans le supprimer, limiter la taille des requêtes selon `MAX_UPLOAD_SIZE_MB`, préserver l’en-tête Host et transmettre les informations HTTPS depuis une source de confiance. Le répertoire des fichiers privés ne doit jamais devenir une racine statique du proxy.

## Publier une version

Effectuer une sauvegarde base et fichiers avant une mise à jour. Construire les deux images depuis un commit identifié, exécuter les tests puis appliquer `alembic upgrade head` avec un processus unique avant de relancer les instances API. Le démarrage Compose local le fait automatiquement ; un déploiement à plusieurs réplicas doit isoler cette étape.

Lancer l’API avec `uvicorn app.main:app --host 0.0.0.0 --port 8000`, le worker avec `python -m app.mail_worker`, et le frontend avec la commande définie dans son Dockerfile. Aucun seed de démonstration ne doit être lancé sur une base réelle.

Créer le premier administrateur avec `python -m app.create_admin --email responsable@votre-domaine.example` depuis `backend/` ou dans le conteneur backend. Le mot de passe est demandé sans être affiché. Pour une initialisation automatisée, fournir `ADMIN_BOOTSTRAP_PASSWORD` par un secret d’environnement temporaire puis le retirer. Utiliser une adresse réelle de votre organisation ; les exemples `campuspulse.test` sont réservés aux démonstrations.

Vérifier `/health/live`, `/health`, une connexion, une consultation autorisée et un téléchargement privé. Vérifier aussi une interdiction entre établissements et la réception d’une invitation. Consigner la version appliquée et le résultat de la restauration de préproduction.

## Exploiter

- Sauvegarder la base **et** les fichiers ; chiffrer les copies hors serveur, contrôler leur accès et définir leur rétention.
- Surveiller la santé API/base, l’espace disque, l’erreur applicative et la progression de la file de courriels. Un worker arrêté peut laisser l’application utilisable tout en empêchant les invitations d’arriver.
- Protéger les journaux ; ne pas enregistrer les cookies, mots de passe, liens de réinitialisation ou contenus de courriels. Les audits applicatifs ne remplacent pas les logs techniques.
- Surveiller les dépendances et tester leurs mises à jour en préproduction. Les versions d’images doivent être fixées par digest dans la chaîne de livraison retenue.
- Préparer les règles de rétention, d’anonymisation et de réponse à un incident avec l’établissement exploitant.

## Limites à lever avant une exposition réelle

Le stockage S3, l’analyse antivirus, la quarantaine opérationnelle, les sauvegardes chiffrées automatisées, la haute disponibilité et la supervision externe ne sont pas provisionnés. Les tests locaux utilisant SQLite ne démontrent pas à eux seuls les garanties PostgreSQL. La limitation des tentatives est conservée en base ; le worker utilise des verrous PostgreSQL pour partager la file. Les performances et scénarios concurrents doivent être évalués sur cet environnement ; consulter [validation.md](validation.md).

Les scripts de restauration refusent les bases et stockages non vides. Pour un retour arrière, restaurer sur une nouvelle instance, contrôler son intégrité et basculer le trafic après validation ; ne pas appliquer aveuglément un downgrade de migration sur les données réelles.
