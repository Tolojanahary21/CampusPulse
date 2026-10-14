# CampusPulse — cahier des charges revu

Version de livraison V1, 14 octobre 2026. Le [document source intégral](cahier-des-charges-source.txt) est conservé pour traçabilité. Ce document fixe les choix appliqués à la première version ; la [matrice de couverture](couverture-fonctionnelle.md) distingue les capacités livrées des extensions prévues.

## 1. Finalité et acteurs

Centraliser la communication universitaire, les supports pédagogiques et les échanges étudiants dans une application web multi-établissements. Trois acteurs principaux restent visibles dans le diagramme général : administrateur de plateforme, administrateur d’établissement et étudiant. Les rôles de publication et de modération sont des délégations de permissions, pas de nouveaux acteurs métier.

La plateforme administre les établissements et les responsables. L’établissement administre sa structure académique, ses membres, les contenus officiels et la modération. L’étudiant consulte les contenus autorisés, son historique et ses notifications, et contribue à sa communauté.

## 2. Périmètre retenu

| Domaine | Comportement attendu en V1 |
| --- | --- |
| Comptes | Inscription publique étudiante avec OTP obligatoire par e-mail, invitations administratives, connexion, déconnexion, récupération de mot de passe, profil et préférences |
| Plateforme | Établissements, attributions/révocations de rôles, statuts de comptes, paramètres et audit |
| Académique | Années, filières, niveaux, matières, inscriptions historiques et parcours multiples |
| Espace officiel | Brouillons, publication, archivage, ciblage, commentaires optionnels et événements |
| Bibliothèque | Fichier privé, métadonnées, filtres, publication et téléchargement autorisé |
| Communauté | Publications, commentaires/réponses, réaction LIKE et signalement |
| Modération | Traitement motivé, masquage/restauration, traçabilité |
| Services | Notifications internes, courriels en file persistante, tableaux de bord selon les permissions |

Une application mobile native, la messagerie privée, les notes, les paiements, la visioconférence et les recommandations par IA restent hors périmètre. Les pièces jointes communautaires, l’import massif des étudiants, l’antivirus et S3 sont des extensions identifiées.

## 3. Règles de gestion

1. Un compte actif peut être membre de plusieurs établissements. Un rôle local n’autorise aucune action dans un autre établissement.
2. Une inscription appartient à une personne, une année et un niveau. L’année, la filière du niveau et l’adhésion doivent correspondre au même établissement. Une progression crée une nouvelle inscription, sans remplacer l’ancienne.
3. Une annonce officielle et une publication communautaire sont deux objets différents, quel que soit le rôle de leur auteur.
4. Les périmètres sont `CAMPUS`, `TARGETED` et `PLATFORM`. Une publication globale exige un administrateur de plateforme. Le partage à une liste arbitraire d’établissements n’est pas proposé dans cette V1.
5. Les cibles sont alternatives au sein d’une dimension, cumulatives entre dimensions. Une **même inscription** doit satisfaire filière, niveau et année. Les annonces utilisent les inscriptions `ACTIVE` ; les documents acceptent `ACTIVE` et `COMPLETED`, sous réserve d’une adhésion toujours active.
6. Les commentaires officiels sont désactivés par défaut. L’annonce et les paramètres d’établissement doivent tous deux les autoriser.
7. Les modifications administratives et décisions de modération sont auditées. Un archivage ou une désactivation préserve les relations historiques.
8. Chaque lecture, mutation et téléchargement est autorisé par le backend. Les filtres et les identifiants reçus ne font jamais office d’autorisation.
9. Les dates techniques sont en UTC ; les dates civiles académiques restent de type date. L’interface affiche les dates dans le navigateur de l’utilisateur.
10. L’étudiant crée son compte depuis l’accueil et choisit un établissement actif. L’API impose le rôle `STUDENT` et une adhésion locale ; seul un administrateur peut créer un compte pour un autre rôle. L’administration de plateforme est seule habilitée à nommer les administrateurs d’établissement.
11. La création publique ne constitue pas une inscription académique. L’administrateur attribue l’année et le niveau pour les contenus ciblés. La validation d’un code OTP reçu par e-mail est obligatoire avant la création du compte et la connexion. Le code expire, le nombre d’essais est limité et le renvoi invalide le code précédent. Après validation, l’étudiant peut lire les contenus généraux de son établissement.

## 4. Architecture et données

Frontend : Next.js App Router, React, TypeScript, Tailwind CSS et TanStack Query. Backend : FastAPI synchrone, Pydantic 2, SQLAlchemy 2 et Alembic. Base de production et Docker : PostgreSQL 16 ; l’installation Windows demandée utilise PostgreSQL 15 et la base `campus_db`. SQLite sert aux tests isolés. Le stockage local est privé et persistant. Un worker séparé remet les courriels de la file durable.

Les UUID sont représentés par des chaînes `VARCHAR(36)` pour la portabilité, les dates techniques par `DateTime(timezone=True)` et les données variables par `JSON`. La V1 ne prétend donc pas utiliser partout les types PostgreSQL natifs UUID/JSONB/INET proposés dans la source. Les tables de ciblage sont relationnelles et disposent de clés primaires composées.

Le [diagramme relationnel](database-schema.puml) est généré depuis les modèles avec `python scripts/generate_database_diagram.py`. Les migrations constituent le schéma appliqué. La cohérence entre établissements est également contrôlée dans les transactions applicatives ; toutes ces règles ne sont pas représentées par des clés étrangères composites SQL.

## 5. API et interface

L’API utilise `/api/v1`, des identifiants UUID sous forme de chaînes et des dates ISO. Les listes utilisent `{items,total,page,page_size}`, avec pagination limitée. Les entrées passent par des schémas Pydantic. Les erreurs utilisent `detail`, les refus d’accès retournent 403/404, les erreurs de validation 422 et les conflits 409 selon le cas.

L’interface propose l’inscription étudiante sur `/register`, l’authentification, le tableau de bord, les annonces, la bibliothèque, les événements, la communauté, les notifications et le profil, ainsi que des espaces d’administration. L’accueil et la connexion donnent accès au formulaire d’inscription. Les données proviennent de l’API. Les parcours doivent conserver des états de chargement, d’erreur et de liste vide, et les formulaires doivent présenter les erreurs serveur.

Les routes précises sont décrites dans [api-domain.md](api-domain.md) et dans l’OpenAPI générée à `/docs`. Les champs ou opérations exposés seulement par API sont indiqués dans la couverture fonctionnelle.

## 6. Sécurité et exploitation

La session est révocable côté serveur. Le cookie de session est HttpOnly ; Secure est requis en production. Les mutations utilisent une protection CSRF et le contrôle d’origine. Les liens d’invitation et de réinitialisation sont expirants et à usage unique. Les mots de passe ne sont jamais conservés en clair.

Les fichiers sont renommés côté serveur et leur chemin interne n’est pas retourné. La taille, l’extension et la signature des formats pris en charge sont contrôlées. Un téléchargement exige un document publié accessible. La vérification des signatures ne remplace pas un antivirus.

La production exige HTTPS, des origines/hôtes autorisés explicites, des secrets distincts, un vrai SMTP, un worker surveillé et des sauvegardes base/fichiers avec restauration répétée. Les exemples locaux ne provisionnent pas automatiquement ces services.

## 7. Acceptation et livraison

Les critères restent : isolation des établissements, historique conservé, ciblage correct, fichiers privés, modération traçable, notifications destinées aux utilisateurs autorisés et installation reproductible. Leur validation exige des tests d’API et de permissions, une migration sur PostgreSQL, des parcours navigateur et une restauration complète.

La présence du code ou d’un workflow CI n’est pas une preuve d’exécution. Les résultats disponibles et les vérifications restant à effectuer sont consignés dans [validation.md](validation.md). Les [guides d’exploitation](deploiement.md), les trois diagrammes PlantUML, les exemples d’environnement et les scripts font partie du livrable.
