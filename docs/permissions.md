# Décisions et permissions

## Comptes, adhésions et rôles

Les permissions sont évaluées dans `backend/app/permissions.py` et dans les endpoints. Le compte doit être actif et la session valide. Pour un rôle local, l’établissement et l’adhésion doivent être actifs ; une attribution révoquée ou expirée ne donne plus de droit.

`PLATFORM_ADMIN` est global et ne porte pas de `campus_id`. `CAMPUS_ADMIN`, `CONTENT_PUBLISHER`, `MODERATOR` et `STUDENT` portent un établissement. Une même personne peut cumuler plusieurs attributions. La lecture et la participation de base reposent sur l’adhésion active ; la présence d’un rôle étudiant ne remplace pas cette adhésion.

L’inscription publique exige un code OTP reçu à l’adresse e-mail déclarée. Aucun compte ni droit n’existe avant sa validation. Celle-ci crée uniquement un compte actif avec `email_verified_at`, une adhésion `STUDENT` et le rôle `STUDENT` dans l’établissement actif choisi. Le formulaire et l’API ne permettent pas de choisir un autre rôle, un matricule, un niveau ou une année. L’année et le niveau sont attribués par un administrateur au moyen d’une inscription académique distincte. La création publique donne donc accès aux contenus généraux de l’établissement, pas automatiquement à ses contenus académiques ciblés.

L’administration d’établissement peut inviter des étudiants, des responsables de publication et des modérateurs dans son établissement. Seule l’administration de plateforme peut créer ou attribuer un rôle d’administrateur d’établissement. La validation OTP est obligatoire pour chaque nouvelle inscription publique. Les comptes déjà existants gardent leurs accès ; les invitations administratives utilisent toujours leur lien personnel expirant et à usage unique.

| Action | Plateforme | Admin établissement | Publication déléguée | Modération déléguée | Étudiant/membre |
| --- | --- | --- | --- | --- | --- |
| Établissements, comptes globaux, paramètres globaux | Tous | Non | Non | Non | Non |
| Structure académique et inscriptions | Tous | Son établissement | Non | Non | Son historique seulement |
| Invitations et rôles locaux autorisés | Tous | Son établissement | Non | Non | Non |
| Créer/publier/archiver annonce ou document | Tous, dont global | Son établissement | Son établissement | Non | Non |
| Administrer les événements | Tous | Son établissement | Son établissement | Non | Non |
| Lire les contenus publiés | Tous selon contexte de gestion | Son établissement | Son établissement | Selon adhésion/ciblage | Selon adhésion/ciblage |
| Publier/commenter/réagir dans la communauté | Établissement autorisé | Son établissement | Son établissement | Son établissement | Son établissement, si activé |
| Modifier/retirer son contenu communautaire | Oui | Oui | Oui | Oui | Oui, sous les règles de visibilité |
| Masquer/restaurer et traiter un signalement | Tous | Son établissement | Non | Son établissement | Non |
| Profil, notifications, préférences | Personnel | Personnel | Personnel | Personnel | Personnel |

Les droits de gestion permettent de consulter les brouillons dans le contexte de gestion. Le téléchargement de fichier exige toujours un document publié ; connaître l’identifiant du fichier ou l’avoir envoyé ne suffit pas.

## Ciblage et historique

Une annonce ou un document `CAMPUS` publié est accessible aux membres actifs du campus. Un objet `PLATFORM` publié est accessible aux utilisateurs authentifiés actifs. Seule la plateforme peut publier globalement. Les publications ciblées contiennent au moins une cible cohérente avec leur établissement.

Pour `TARGETED`, une dimension vide n’ajoute pas de filtre. Plusieurs filières forment un OU, plusieurs niveaux un OU, plusieurs années un OU. Les dimensions renseignées sont reliées par ET et doivent correspondre à **la même inscription** : l’année d’un premier parcours ne peut pas compléter le niveau d’un second parcours.

Exemple : filière Informatique, niveau L2 et année 2026–2027 exigent une inscription Informatique/L2/2026–2027. Une inscription L2 de l’année précédente plus une inscription L3 de l’année courante ne suffisent pas. L’accès documentaire conserve les inscriptions terminées `COMPLETED`, mais une adhésion suspendue bloque l’accès local.

Les administrateurs et responsables de publication disposent d’un accès de gestion à leurs contenus. Ce privilège ne doit pas être utilisé pour simuler les résultats d’un étudiant lors des tests de ciblage.

## Décisions V1 par rapport à la source

| Sujet | Décision |
| --- | --- |
| Création de compte | Inscription publique étudiante à partir de l’accueil ; invitations administratives pour les autres rôles et pour les étudiants invités |
| Inscription publique | Établissement actif obligatoire, rôle étudiant imposé, mot de passe d’au moins 12 caractères ; accès général uniquement après vérification OTP de l’adresse e-mail |
| Authentification | Session opaque serveur, cookie HttpOnly, CSRF, révocation à la déconnexion/changement de mot de passe |
| Plusieurs parcours | Autorisés, avec unicité utilisateur/niveau/année et matricule dans l’établissement |
| Délégations | Attribution rattachée au campus, expiration/révocation et audit |
| Adhésions locales | L’administrateur peut activer, suspendre ou terminer une adhésion de son établissement ; le statut global du compte reste administré par la plateforme |
| Suppression | Désactivation des comptes, archivage académique/officiel et retrait logique communautaire |
| Commentaires officiels | Double activation : paramètre d’établissement et annonce |
| Fichiers | Stockage local privé ; PDF, TXT, PNG, JPEG, DOCX, XLSX et PPTX validés ; pas de pièces jointes communautaires |
| Réactions | LIKE dans la première version |
| Signalements | Une publication ou un commentaire communautaire ; pas de signalement documentaire ou de commentaire officiel |
| Modération | Masquage/restauration et résolution/rejet avec motif ; pas de bannissement automatique |
| Courriels | File persistante et worker SMTP, paramètres séparés de l’API |
| Préférences | Deux catégories de courriel ; notifications internes toujours présentes |
| Sauvegardes | PostgreSQL et fichiers ensemble ; chiffrement et rétention confiés à l’exploitation |

Les contraintes SQL empêchent notamment certaines incohérences structurelles, les doubles réactions et les cibles multiples d’un signalement. D’autres contrôles, dont la compatibilité multi-établissements, sont effectués dans les transactions API : une écriture SQL directe contournerait cette couche et doit être réservée à l’exploitation autorisée.
