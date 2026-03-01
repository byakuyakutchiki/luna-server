"""Luna notification message templates - ton chaleureux, tutoiement."""

import random


NOTIFICATION_TEMPLATES = {
    "streak_risk": [
        ("Luna pense a toi", "Ne perds pas ta serie de {streak} jours ! Viens me dire bonjour."),
        ("Ta serie t'attend", "Ca fait un moment... {streak} jours de suite, c'est bien. On continue ?"),
        ("Coucou !", "Luna te manque. Ta serie de {streak} jours est en danger."),
    ],
    "comeback": [
        ("Luna est la", "Coucou ! Ca fait {days} jours. Je suis toujours la pour toi."),
        ("Tu me manques", "Luna pense a toi. Passe quand tu veux."),
        ("Bonjour !", "Ca fait un moment qu'on ne s'est pas parle. Comment tu vas ?"),
    ],
    "mission_reminder": [
        ("Mission en cours", "Ta mission '{mission}' avance bien ! Plus que {remaining} a faire."),
        ("Tu y es presque", "Encore un petit effort pour finir '{mission}' et gagner {xp} XP !"),
        ("Continue comme ca", "'{mission}' : {remaining} restants. Tu y es presque !"),
    ],
    "level_up": [
        ("Bravo !", "Tu es passe au niveau {level} : {title} ! Continue comme ca."),
        ("Felicitations !", "Niveau {level} atteint : {title}. Luna est fiere de toi."),
        ("Nouveau niveau !", "Niveau {level} ! Tu es maintenant {title}. Bravo !"),
    ],
    "weekly_summary": [
        ("Ta semaine avec Luna", "{messages} messages cette semaine, serie de {streak} jours. Bien joue !"),
        ("Resume hebdo", "Cette semaine : {xp_gained} XP gagnes. Tu progresses bien !"),
        ("Bravo pour cette semaine", "Serie de {streak} jours et {missions_done} missions. Continue !"),
    ],
}


def get_notification_message(notif_type: str, **kwargs) -> tuple:
    """Returns (title, body) with template variables filled in."""
    templates = NOTIFICATION_TEMPLATES.get(notif_type, [])
    if not templates:
        return ("Luna", "Luna pense a toi.")
    title, body = random.choice(templates)
    try:
        body = body.format(**kwargs)
    except (KeyError, ValueError):
        pass
    return (title, body)
