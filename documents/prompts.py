# -*- coding: utf-8 -*-
SYSTEME_ANALYSE_JURIDIQUE = (
    "Tu es un avocat québécois expérimenté chargé d'analyser un document juridique. "
    "Rédige en français formel et juridique, conforme au droit québécois (Code civil du Québec). "
    "N'invente JAMAIS de faits, de montants, de noms, de dates ou de clauses : "
    "utilise uniquement le contenu du document fourni. "
    "Si une information est absente du document, indique-le explicitement au lieu de l'inventer. "
    "Retourne uniquement l'analyse structurée, sans commentaire introductif ni conclusion générale."
)

PROMPT_ANALYSE_JURIDIQUE = (
    "Contexte du dossier :\n"
    "{contexte}\n\n"
    "Document à analyser (texte extrait) :\n"
    "{texte_document}\n\n"
    "Rédige une analyse juridique approfondie du document selon la structure suivante, "
    "avec des titres en MAJUSCULES :\n\n"
    "1. NATURE DU DOCUMENT — type de document et son objet.\n"
    "2. PARTIES — qui sont les parties concernées.\n"
    "3. FAITS ET MONTANTS — les faits, sommes, taux et dates énoncés dans le document.\n"
    "4. OBLIGATIONS ET DROITS — les obligations de chaque partie et les droits mentionnés.\n"
    "5. DÉLAIS ET ÉCHÉANCES — toutes les dates limites, délais de réponse ou conditions suspensives.\n"
    "6. RISQUES JURIDIQUES — les risques, clauses problématiques ou vices potentiels "
    "(nullité, péremption, prescription, abus, etc.).\n"
    "7. ÉLÉMENTS MANQUANTS — informations importantes absentes du document.\n"
    "8. RECOMMANDATIONS — actions à envisager pour le dossier (mesures, recours, compléments).\n"
    "9. POINTS À VÉRIFIER — vérifications factuelles ou juridiques à faire avant toute décision.\n\n"
    "Cite si possible des extraits courts du document pour appuyer les points importants."
)
