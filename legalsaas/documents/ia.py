# -*- coding: utf-8 -*-
import time

from decouple import config
import anthropic
from docx import Document as DocxDocument
from pypdf import PdfReader
from .prompts import SYSTEME_ANALYSE_JURIDIQUE, PROMPT_ANALYSE_JURIDIQUE

MODELE_CLAUDE = "claude-sonnet-4-6"
MAX_TEXTE_ANALYSE = 25000

_client = anthropic.Anthropic(api_key=config('ANTHROPIC_API_KEY'))


def _appel_claude(prompt_systeme, prompt_utilisateur, max_tokens=2000, essais=3):
    derniere_erreur = None
    for tentative in range(essais):
        try:
            reponse = _client.messages.create(
                model=MODELE_CLAUDE,
                max_tokens=max_tokens,
                system=prompt_systeme,
                messages=[{"role": "user", "content": prompt_utilisateur}],
            )
            return reponse.content[0].text.strip()
        except anthropic.RateLimitError as erreur:
            derniere_erreur = erreur
            if tentative < essais - 1:
                time.sleep(5 * (tentative + 1))
        except anthropic.APIConnectionError as erreur:
            derniere_erreur = erreur
            if tentative < essais - 1:
                time.sleep(2 * (tentative + 1))
        except anthropic.APIStatusError:
            raise
    raise derniere_erreur





def generer_mise_en_demure(gabarit_rempli, valeurs):
    systeme = (
        "Tu es un avocat québécois rédigeant une mise en demeure. "
        "Rédige en français formel et juridique, conforme au droit québécois "
        "(Code civil du Québec). "
        "N'invente JAMAIS de faits, de montants, de noms, de dates ou d'adresses : "
        "utilise uniquement les informations fournies. "
        "Ne modifie ni les montants ni les délais. "
        "Retourne uniquement le texte de la lettre, sans commentaire ni explication."
    )
    prompt = (
        "Voici le gabarit de la mise en demeure, avec les données réelles du dossier "
        "déjà insérées :\n\n"
        f"{gabarit_rempli}\n\n"
        "Informations complémentaires du dossier :\n"
        f"{valeurs}\n\n"
        "Rédige la mise en demeure finale en respectant exactement la structure "
        "et les faits fournis."
    )
    return _appel_claude(systeme, prompt)


def extraire_texte(chemin, nom_fichier):
    ext = (nom_fichier or '').lower().rsplit('.', 1)[-1]
    if ext == 'docx':
        document = DocxDocument(chemin)
        return '\n'.join(p.text for p in document.paragraphs if p.text.strip())
    if ext == 'pdf':
        lecteur = PdfReader(chemin)
        return '\n'.join((page.extract_text() or '') for page in lecteur.pages)
    if ext == 'txt':
        with open(chemin, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    return ''


def analyser_document(texte, contexte):
    texte_tronque = (texte or '')[:MAX_TEXTE_ANALYSE]
    prompt = PROMPT_ANALYSE_JURIDIQUE.format(contexte=contexte, texte_document=texte_tronque)
    return _appel_claude(SYSTEME_ANALYSE_JURIDIQUE, prompt, max_tokens=8000)
