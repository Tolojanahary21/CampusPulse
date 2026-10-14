const messages: Record<string, string> = {
  "Adresse e-mail ou mot de passe incorrect.":
    "Incorrect email address or password.",
  "Connexion au serveur impossible. Vérifiez votre connexion puis réessayez.":
    "Unable to connect to the server. Check your connection and try again.",
  "Les mots de passe ne correspondent pas.": "The passwords do not match.",
  "Les nouveaux mots de passe ne correspondent pas.":
    "The new passwords do not match.",
  "Le téléchargement a été refusé.": "The download was denied.",
  "Cette adresse est déjà utilisée.": "This email address is already in use.",
  "Les inscriptions étudiantes sont temporairement fermées. Contactez votre établissement.":
    "Student registration is temporarily closed. Contact your institution.",
  "Cet établissement ne propose pas d’inscription actuellement.":
    "This institution is not accepting registrations at the moment.",
  "L’inscription n’a pas pu être enregistrée. Réessayez.":
    "Your registration could not be saved. Please try again.",
  "Cette vérification est introuvable ou terminée. Recommencez votre inscription.":
    "This verification cannot be found or is already complete. Start your registration again.",
  "Cette inscription a expiré. Recommencez votre inscription.":
    "This registration has expired. Start your registration again.",
  "Ce code a expiré. Demandez un nouveau code.":
    "This code has expired. Request a new code.",
  "Le code de vérification est incorrect.":
    "The verification code is incorrect.",
  "Trop de codes incorrects. Demandez un nouveau code.":
    "Too many incorrect codes. Request a new code.",
  "Veuillez patienter avant de demander un nouveau code.":
    "Please wait before requesting a new code.",
  "La vérification a changé. Utilisez le dernier code reçu ou recommencez votre inscription.":
    "The verification has changed. Use the latest code received or start your registration again.",
  "Le mot de passe actuel est incorrect.": "The current password is incorrect.",
  "Trop de tentatives. Réessayez dans quelques minutes.":
    "Too many attempts. Please try again in a few minutes.",
  "Ce lien est invalide ou a expiré. Demandez un nouveau lien.":
    "This link is invalid or expired. Request a new link.",
  "Ce lien a déjà été utilisé.": "This link has already been used.",
  "Ce lien ne peut plus être utilisé.": "This link can no longer be used.",
  "Vous ne disposez pas des permissions nécessaires.":
    "You do not have permission to perform this action.",
  "Accès à cet établissement refusé.": "Access to this institution is denied.",
  "Ressource introuvable.": "Resource not found.",
  "Établissement introuvable.": "Institution not found.",
  "Le service de données est temporairement indisponible.":
    "The data service is temporarily unavailable.",
  "Cette opération entre en conflit avec des données existantes ou des références invalides.":
    "This action conflicts with existing data or invalid references.",
  "Ces données existent déjà ou sont liées à une autre ressource.":
    "This record already exists or is linked to another resource.",
  "Ce compte est déjà rattaché à cet établissement.":
    "This account already belongs to this institution.",
  "Ce compte est déjà activé. Son titulaire peut demander une réinitialisation.":
    "This account is already activated. Its owner can request a password reset.",
  "Seule l’administration de plateforme peut nommer un administrateur.":
    "Only a platform administrator can appoint an institution administrator.",
  "Vous ne pouvez pas désactiver votre propre compte.":
    "You cannot deactivate your own account.",
  "Vous ne pouvez pas révoquer votre propre accès plateforme.":
    "You cannot revoke your own platform access.",
  "La demande n’a pas pu aboutir.": "The request could not be completed.",
};

export function errorMessage(error: unknown, locale: "fr" | "en") {
  const message = error instanceof Error ? error.message : String(error);
  if (locale === "fr") {
    return (
      Object.entries(messages).find(
        ([, english]) => english === message,
      )?.[0] || message
    );
  }
  if (messages[message]) return messages[message];
  // Server-owned messages have a French fallback. Keep them useful in English
  // without translating or altering any user-authored content returned by the API.
  const status =
    error && typeof error === "object" && "status" in error
      ? Number(error.status)
      : null;
  if (status !== null) {
    if (status === 401) return "Please sign in to continue.";
    if (status === 403)
      return "You do not have permission to perform this action.";
    if (status === 404)
      return "This item is unavailable or could not be found.";
    if (status === 409)
      return "This action conflicts with an existing record. Check your entries.";
    if (status === 413) return "This file is too large. Choose a smaller file.";
    if (status === 422 || status === 400)
      return "Check the entered fields and try again.";
    if (status === 429)
      return "Too many attempts. Please try again in a few minutes.";
    return "The service is temporarily unavailable. Please try again.";
  }
  return message;
}
