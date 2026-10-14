# Couverture fonctionnelle de la V1

Cette matrice relie le cahier des charges au code livré. « API » signifie qu’un endpoint est implémenté ; ce terme ne prouve ni un test sur PostgreSQL ni un parcours navigateur. Les résultats de vérification sont séparés dans [validation.md](validation.md).

| Domaine source | Backend livré | Interface / accès | Limites et choix |
| --- | --- | --- | --- |
| 8.1 Authentification | Inscription étudiante avec OTP obligatoire, renvoi et expiration, session serveur, login/logout, récupération, invitation, profil, changement de mot de passe | `/register` depuis l’accueil et la connexion, `/login`, `/forgot-password`, `/reset-password`, `/accept-invitation`, `/app/profile` | Rôle étudiant imposé, établissement actif obligatoire ; compte créé seulement après vérification de l’adresse |
| 8.2 Plateforme | Établissements, comptes/statuts, rôles, paramètres et audit | `/app/platform` | Paramètres V1 limités au nom, courriel de support et message de maintenance |
| 8.3 Académique | Années, filières, niveaux, matières, inscriptions et historique | `/app/admin`, historique dans `/app/profile` | Pas d’import CSV ; inscriptions ajoutées individuellement |
| Adhésions/invitations | Adhésion étudiante publique ; création, invitation, renvoi et statut local par les administrateurs | `/register`, administration et API `/campuses/{id}/users` | Les autres rôles sont réservés aux administrateurs ; l’inscription académique ciblée et le statut global restent des opérations administratives |
| 8.4 Annonces | Brouillon/publication/archivage, ciblage, période de visibilité, commentaires conditionnels | `/app/announcements` et détail | Texte sans éditeur riche ; commentaires officiels sans signalement/modération dédiée |
| 8.4 Événements | Création, dates validées, statut, lien facultatif vers annonce | `/app/events` | Présentation en liste/cartes ; pas de calendrier mensuel, réservation ni rappels automatiques |
| 8.5 Documents | Métadonnées, catégories, ciblage, publication, archivage et téléchargement contrôlé | `/app/documents`, filtres année/filière/niveau/matière et détail | Stockage local uniquement ; pas de prévisualiseur ou de versionnement des fichiers |
| 7.3 Fichiers | Limite globale/campus, extension et signature, noms internes, hash SHA-256 | Formulaire de dépôt et téléchargement | PDF/TXT/PNG/JPEG/DOCX/XLSX/PPTX ; pas d’antivirus ni de quarantaine opérationnelle |
| 8.6 Communauté | Publications, commentaires et réponses, modifications/retraits, LIKE | `/app/community` et détail | Texte uniquement ; une réaction LIKE par cible et utilisateur |
| 8.6 Modération | Signalement d’une publication/commentaire, résolution/rejet, masquage/restauration, motif et journal | Administration et API de modération | Pas de sanctions automatiques ni de signalement documentaire |
| 8.7 Notifications | Notifications personnelles, lecture, publication dédupliquée, activité communautaire | `/app/notifications`, tableau de bord | Pas de WebSocket ou de notification push |
| Courriel | Codes OTP, bienvenue, invitations, récupération, annonces et réponses selon préférences, file persistante, worker, nouvelles tentatives | Mailpit en développement ; SMTP paramétrable | Pas d’interface de gestion de la file ; fournisseur externe non provisionné |
| 8.7 Tableau de bord | Résumé et activités filtrés selon les droits | `/app` | Indicateurs opérationnels simples, pas d’analytique avancée |
| 12 Exploitation | Compose, migration, scripts base/fichiers, santé et CI | Guides d’installation et d’exploitation | Hébergement, chiffrement des sauvegardes, supervision et restauration réelle restent à valider |

## Différences de modèle explicites

La source proposait 33 tables avec les pièces jointes communautaires optionnelles. La V1 omet `content_attachments` et ajoute une file SMTP `mail_outbox`, un compteur durable `auth_rate_limits` et les demandes temporaires `student_registrations` pour la vérification OTP : le schéma comprend 35 tables, hors `alembic_version`. Les préférences sont simplifiées en deux indicateurs de courriel par utilisateur. Les signalements et décisions de modération utilisent des références typées vers les publications/commentaires communautaires.

Les UUID sont des chaînes de 36 caractères et les métadonnées variables du JSON portable. Les règles entre établissements sont contrôlées par les services API et les transactions ; elles ne sont pas toutes matérialisées par des clés étrangères composites. Les diagrammes sont alignés sur le code, pas sur des colonnes proposées mais absentes.

## Capacités restant hors V1

Application mobile, messagerie privée, paiements, visioconférence, gestion officielle des notes/examens, IA de recommandation, import de masse, stockage S3, antivirus, pièces jointes communautaires et haute disponibilité. Les événements ne gèrent pas l’inscription des participants ; leur lien d’inscription peut renvoyer vers un service externe.

Le worker vérifie les annonces dont la date de début est arrivée, crée leurs notifications pour les destinataires éligibles et conserve un marqueur de traitement. Cette vérification fonctionne même si `SMTP_ENABLED=false` ; les courriels restent alors en file. Il faut donc faire fonctionner le worker pour les annonces programmées, et pas uniquement pour les invitations.

Les requêtes de contenu préfiltrent les établissements en SQL, puis certaines règles de ciblage et les destinataires de notifications sont évalués côté Python. La pagination de l’API ne garantit donc pas une consommation mémoire proportionnelle à la seule page affichée. Les sélecteurs de références de l’interface chargent actuellement au plus 100 éléments par collection ; au-delà, prévoir une recherche paginée. Un volume élevé exige des mesures de charge et l’optimisation de ces requêtes avant exploitation.
