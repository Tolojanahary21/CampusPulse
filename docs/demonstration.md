# Parcours de démonstration

Installer les services et exécuter le seed explicitement selon le README. Tous les comptes de démonstration utilisent le mot de passe fourni dans `DEMO_PASSWORD` ; aucun mot de passe universel n’est livré. Le seed refuse la production et ne remplace pas le mot de passe d’une démonstration déjà initialisée.

Les noms d’établissements et supports fournis servent à la démonstration : ils ne constituent pas des données officielles d’université. Les ressources pédagogiques du seed sont des fichiers texte fictifs. Les événements sont datés relativement au moment du seed.

## Création autonome d’un compte étudiant

1. Depuis l’accueil ou `/login`, ouvrir « Créer un compte étudiant » et sélectionner un établissement actif sur `/register`.
2. Renseigner une adresse nouvelle, son identité et un mot de passe d’au moins 12 caractères. Aucun choix de rôle, d’année ou de niveau ne doit être proposé.
3. Avec Mailpit ou le SMTP configuré et le worker actifs, récupérer le code à six chiffres reçu par e-mail. Avant sa validation, la connexion doit échouer et aucun compte n’est créé.
4. Saisir un code incorrect pour constater le refus, puis le code valide. Vérifier aussi que le renvoi reste indisponible pendant 60 secondes et que l’ancien code est refusé après renvoi. Un code expire après 10 minutes par défaut. SMTP désactivé ne permet jamais de contourner cette étape.
5. Après validation, se connecter avec ce compte. Les espaces généraux de l’établissement sont accessibles ; l’administration reste inaccessible et l’historique académique est vide.
6. Avec le compte administrateur d’établissement, ajouter une inscription à l’année et au niveau voulus. Revenir au compte étudiant pour contrôler l’accès aux contenus ciblés correspondants.

Sur une base vide, l’administrateur de plateforme doit d’abord créer un établissement actif. Avec `PUBLIC_REGISTRATION_ENABLED=false`, le formulaire signale la fermeture et l’API refuse les créations publiques ; les invitations administratives restent disponibles.

## 1. Étudiant

Se connecter sur `/login` avec `etudiant@campuspulse.test`. Le tableau de bord et les espaces de l’Université d’Antananarivo sont accessibles.

1. Ouvrir les annonces et lire « L2 Informatique : organisation des travaux pratiques ».
2. Ouvrir la bibliothèque, filtrer le niveau et télécharger un support. La requête passe par l’API authentifiée ; aucun lien statique public ne doit être utilisé.
3. Consulter le profil : les inscriptions 2025–2026 terminée et 2026–2027 active doivent toutes deux apparaître.
4. Ouvrir une publication communautaire, commenter et ajouter une réaction.
5. Créer une publication de test, puis la signaler depuis un autre compte étudiant, par exemple `lina@campuspulse.test` dans une session séparée.
6. Consulter les notifications et les marquer comme lues ; modifier ses préférences de courriel.

## 2. Administrateur d’établissement

Se connecter avec `responsable@campuspulse.test`.

1. Dans l’administration, consulter les années, filières, niveaux, matières, membres et inscriptions.
2. Inviter une adresse fictive nouvelle. Lire l’invitation dans Mailpit à `http://localhost:8025`, ouvrir son lien et définir un mot de passe. Sans worker en fonctionnement, le message reste dans la file.
3. Créer une annonce ciblant Informatique/L2/2026–2027, enregistrer son brouillon puis la publier. Revenir au compte étudiant pour contrôler sa visibilité et sa notification.
4. Ajouter un fichier `.txt` ou PDF, renseigner ses métadonnées et son ciblage, puis publier le document. Un brouillon ne doit pas être téléchargeable par un étudiant.
5. Résoudre le signalement créé précédemment avec un motif et l’action de masquage ; vérifier que le contenu est retiré de la vue d’un autre étudiant.
6. Ajouter une nouvelle inscription à l’étudiant ou changer son statut ; vérifier que l’inscription de l’année précédente subsiste.

Pour vérifier l’accès aux anciens documents, créer un document ciblé sur L1/2025–2026 sans lui associer une matière L2. L’étudiant conserve cet accès grâce à son inscription `COMPLETED`, tant que son adhésion est active.

## 3. Administrateur de plateforme

Se connecter avec `admin@campuspulse.test`.

1. Consulter les deux établissements, créer un établissement de démonstration et modifier ses coordonnées.
2. Attribuer un rôle local à un compte autorisé, puis vérifier l’attribution et sa révocation dans l’audit.
3. Consulter les comptes et leurs statuts ; suspendre uniquement un compte de démonstration sans session importante en cours.
4. Consulter les paramètres globaux et les journaux des actions précédentes.

## 4. Vérification de l’isolation

Le seed contient aussi `responsable.toamasina@campuspulse.test` et `etudiant.toamasina@campuspulse.test`. Utiliser un profil de navigateur séparé ou se déconnecter entre les essais.

Un étudiant de Toamasina ne doit pas lire les annonces ou documents d’Antananarivo, même en réutilisant un identifiant connu dans une URL. Un responsable de Toamasina ne doit pas modifier une inscription, un contenu ou un signalement d’Antananarivo. Les API renvoient un refus 403/404. Une publication `PLATFORM` est une exception explicite de partage global.

Ces étapes sont un protocole de recette, pas un compte rendu attestant leur exécution. Les résultats automatisés disponibles et les parcours effectivement contrôlés figurent dans [validation.md](validation.md).
