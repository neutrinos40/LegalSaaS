import re

from django import template
from django.utils.html import escape

register = template.Library()


@register.filter
def markdown_leger(texte):
    lignes = escape(texte or '').splitlines()
    resultat = []
    en_liste = False

    for ligne in lignes:
        ligne = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', ligne)
        ligne = re.sub(r'\*(.+?)\*', r'<em>\1</em>', ligne)
        if re.match(r'^#{1,4}\s', ligne):
            if en_liste:
                resultat.append('</ul>')
                en_liste = False
            niveau = ligne.index('#') + 1
            contenu = ligne.lstrip('#').strip()
            resultat.append(f'<h{niveau}>{contenu}</h{niveau}>')
        elif ligne.strip() == '':
            if en_liste:
                resultat.append('</ul>')
                en_liste = False
        elif re.match(r'^[-•]\s', ligne):
            if not en_liste:
                resultat.append('<ul>')
                en_liste = True
            resultat.append(f'<li>{ligne[2:].strip()}</li>')
        else:
            if en_liste:
                resultat.append('</ul>')
                en_liste = False
            resultat.append(f'<p>{ligne}</p>')

    if en_liste:
        resultat.append('</ul>')
    return ''.join(resultat)
