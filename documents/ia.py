# -*- coding: utf-8 -*-
import time

from decouple import config
import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout
from docx import Document as DocxDocument
from pypdf import PdfReader
from .prompts import SYSTEME_ANALYSE_JURIDIQUE, PROMPT_ANALYSE_JURIDIQUE

MODELE_GEMINI = "gemini-3.6-flash"
URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/"
MAX_TEXTE_ANALYSE = 25000


def _appel_gemini(prompt_systeme, prompt_utilisateur, max_tokens=2000, essais=3):
    cle = config('GEMINI_API_KEY')
    url = f"{URL_GEMINI}{MODELE_GEMINI}:generateContent?key={cle}"
    corps = {
        "system_instruction": {"parts": [{"text": prompt_systeme}]},
        "contents": [{"parts": [{"text": prompt_utilisateur}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": max_tokens},
    }
    derniere_erreur = None
    for tentative in range(essais):
        try:
            reponse = requests.post(url, json=corps, timeout=120)
            reponse.raise_for_status()
            donnees = reponse.json()
            return donnees["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (ConnectionError, Timeout) as erreur:
            derniere_erreur = erreur
            if tentative < essais - 1:
                time.sleep(2 * (tentative + 1))
        except HTTPError as erreur:
            if erreur.response is not None and erreur.response.status_code == 429:
                derniere_erreur = erreur
                if tentative < essais - 1:
                    time.sleep(5 * (tentative + 1))
            else:
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
    return _appel_gemini(systeme, prompt)


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
    return _appel_gemini(SYSTEME_ANALYSE_JURIDIQUE, prompt, max_tokens=8000)