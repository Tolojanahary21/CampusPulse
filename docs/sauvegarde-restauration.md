# Sauvegarde et restauration

Une sauvegarde CampusPulse réunit PostgreSQL et le répertoire de fichiers privés. Une copie de la base seule ne restaure pas les documents téléchargés. Les exemples ci-dessous utilisent Docker Compose et PowerShell ; ils ne ciblent pas automatiquement une base externe.

## Créer une sauvegarde cohérente

Depuis la racine du dépôt :

```powershell
.\scripts\database-backup.ps1 -Action Backup
```

Le script vérifie que PostgreSQL fonctionne, suspend les services API et worker qui étaient actifs, crée un dump PostgreSQL au format custom et archive le volume `uploads`. Il remet ensuite en route les services précédemment actifs, même si la sauvegarde a échoué. Pendant cette opération l’application est indisponible ; aucune autre application ou session SQL ne doit écrire dans la base ou le stockage.

Le dossier `backups/<date-UTC>-<identifiant>/` contient `database.dump`, `uploads.tar.gz` et `manifest.json` avec leurs empreintes SHA-256. L’absence de manifeste signifie que la sauvegarde n’est pas complète. Le script refuse les liens symboliques et entrées spéciales dans le stockage.

Exécuter une seule opération de sauvegarde/restauration à la fois pour un projet Compose. Les fichiers temporaires de dump dans le conteneur PostgreSQL sont supprimés à la fin ; un arrêt brutal du processus peut nécessiter leur nettoyage manuel.

Les sauvegardes ne contiennent pas les fichiers de configuration, clés ou mots de passe d’environnement. Conserver ceux-ci séparément dans le gestionnaire de secrets. Le dump contient toutefois des données personnelles, des hashes d’authentification et des courriels en attente : chiffrer la sauvegarde hors du projet et limiter son accès. Le script ne met en place ni chiffrement, ni copie hors serveur, ni rétention automatique.

## Restaurer sur une cible vide

Choisir une nouvelle instance PostgreSQL et un nouveau volume de fichiers. Le script **refuse** une base contenant des tables ou un volume contenant des entrées ; il n’effectue ni suppression récursive, ni `DROP`, ni `pg_restore --clean`.

Pour répéter une restauration locale avec des volumes séparés, utiliser un autre nom de projet Compose. Arrêter d’abord les services du projet d’origine pour libérer ses ports ; ses volumes restent conservés :

```powershell
docker compose stop
$env:COMPOSE_PROJECT_NAME = 'campuspulse-restore'
docker compose up -d postgres
.\scripts\database-backup.ps1 -Action Restore -BackupPath '.\backups\DOSSIER_DE_SAUVEGARDE' -RestoreToEmptyTarget
docker compose up -d
```

Les images backend doivent déjà être construites pour exécuter le helper ; au besoin lancer `docker compose build backend` avant la restauration. Conserver le même nom de projet dans le terminal pendant toute la procédure. Les variables `.env` doivent fournir les identifiants de la nouvelle base. Ne pas lancer le backend avant la restauration : son démarrage appliquerait les migrations et rendrait la base non vide.

Le script vérifie les empreintes et les chemins des entrées de l’archive, contrôle les cibles vides, restaure PostgreSQL dans une transaction puis les fichiers. Une restauration échouée laisse les services applicatifs arrêtés. Si la base a été restaurée mais que la copie des fichiers échoue, ne pas rouvrir l’application : diagnostiquer l’échec et recommencer sur une nouvelle cible vide. Les données déjà présentes ne sont jamais effacées par le script.

## Vérifier avant de rouvrir

Contrôler les migrations, les comptes, les inscriptions historiques, un document téléchargé et son contenu, puis le refus d’accès depuis un autre établissement. Vérifier les notifications et le statut des messages en attente avant de remettre le worker SMTP en service : une copie de production peut contenir des destinataires réels. Effectuer les exercices de restauration avec SMTP désactivé ou dirigé vers Mailpit.

Consigner la date, la durée, la taille des fichiers, les empreintes et le résultat des vérifications. Adapter fréquence et durée de rétention aux besoins de l’établissement. Les scripts sont livrés et leur syntaxe est contrôlée ; le succès d’une restauration réelle PostgreSQL/volumes doit être attesté sur l’hébergement retenu.
