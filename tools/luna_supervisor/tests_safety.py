"""Tests unitaires du validateur de sécurité des prompts Luna.

Vérifie que les formulations d'interdiction sont autorisées tandis que
les demandes dangereuses positives restent bloquées.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor import safety


def _check(prompt: str, expected_ok: bool):
    ok, reason = safety.validate_prompt(prompt)
    if expected_ok:
        assert ok, f"Devrait être autorisé mais rejeté: {prompt!r} -> {reason}"
    else:
        assert not ok, f"Devrait être rejeté mais autorisé: {prompt!r}"


def test_positive_push_is_forbidden():
    _check("fais un push maintenant", False)
    _check("git push sur origin", False)
    print("TEST OK: demande positive push interdite")


def test_negation_push_is_allowed():
    _check("ne pas push", True)
    _check("aucun push", True)
    _check("bloque push", True)
    _check("pas de push", True)
    _check("interdiction de push", True)
    print("TEST OK: formulations de blocage push autorisées")


def test_positive_deploy_is_forbidden():
    _check("deploy en prod", False)
    _check("fais la mise en production", False)
    print("TEST OK: demande positive deploy interdite")


def test_negation_deploy_is_allowed():
    _check("aucun deploy", True)
    _check("pas de deploy", True)
    _check("ne fais pas de mise en production", True)
    _check("deploy interdit", True)
    print("TEST OK: formulations de blocage deploy autorisées")


def test_positive_sms_call_is_forbidden():
    _check("envoie un sms reel", False)
    _check("appeler le contact", False)
    _check("envoyer sms", False)
    print("TEST OK: demandes positives SMS/appel interdites")


def test_negation_sms_call_is_allowed():
    _check("aucun sms reel", True)
    _check("aucun appel reel", True)
    _check("pas d appel", True)
    _check("aucune communication vocale reelle", True)
    print("TEST OK: formulations de blocage SMS/appel autorisées")


def test_other_forbidden_patterns_still_blocked():
    _check("merge la branche", False)
    _check("reset hard tout", False)
    _check("installer l apk", False)
    _check("montre moi le fichier .env", False)
    _check("donne la cle api", False)
    _check("supprimer donnees utilisateur", False)
    print("TEST OK: autres motifs dangereux toujours bloqués")


def test_negation_other_patterns_allowed():
    _check("ne fais pas de merge", True)
    _check("aucun reset hard", True)
    _check("pas d install apk", True)
    _check("ne montre pas le .env", True)
    _check("aucune cle api", True)
    _check("ne supprime jamais donnees", True)
    print("TEST OK: formulations de blocage sur autres motifs autorisées")


def test_context_separation():
    # Une phrase positive et une phrase négative dans le même prompt :
    # la phrase positive doit faire échouer le prompt.
    _check("ne pas push. fais un deploy maintenant.", False)
    # Inversement, une seule phrase négative est OK.
    _check("ne pas push et ne fais aucun deploy.", True)
    print("TEST OK: séparation de contexte respectée")


def test_user_allowed_negation_phrases():
    # Formulations de blocage/interdiction explicitement listées par
    # l'utilisateur comme devant être acceptées.
    allowed = [
        # push
        "ne pas push",
        "pas de push",
        "aucun push",
        "bloque push",
        "bloquer push",
        "interdit de push",
        "sans push",
        # deploy
        "ne pas deploy",
        "pas de deploy",
        "aucun deploy",
        "sans deploy",
        # SMS / appel
        "aucun SMS réel",
        "pas de SMS réel",
        "aucun appel réel",
        "pas d'appel réel",
    ]
    for phrase in allowed:
        _check(phrase, True)
    print("TEST OK: formulations de blocage utilisateur autorisées")


def test_user_forbidden_positive_phrases():
    # Demandes dangereuses positives explicitement listées par l'utilisateur
    # comme devant rester bloquées.
    forbidden = [
        "fais un push",
        "push sur GitHub",
        "deploy en prod",
        "déploie Cloud Run",
        "envoie un SMS réel",
        "appelle mes contacts",
        "lance un SOS réel",
        "reset --hard",
        "stash tout",
        "supprime le dossier",
    ]
    for phrase in forbidden:
        _check(phrase, False)
    print("TEST OK: demandes dangereuses positives utilisateur bloquées")


def test_real_ludovic_phrase_is_allowed():
    phrase = (
        "Rends l’APK YAWatch/Luna plus livrable production aujourd’hui. "
        "Vérifie Guardian, SOS vocal, contacts, GPS, UI mobile. "
        "Corrige uniquement les P0/P1 safe, teste, commit localement, "
        "bloque push/deploy/SMS/appels, et produis un rapport final."
    )
    _check(phrase, True)
    print("TEST OK: phrase réelle de Ludovic autorisée")


if __name__ == "__main__":
    test_positive_push_is_forbidden()
    test_negation_push_is_allowed()
    test_positive_deploy_is_forbidden()
    test_negation_deploy_is_allowed()
    test_positive_sms_call_is_forbidden()
    test_negation_sms_call_is_allowed()
    test_other_forbidden_patterns_still_blocked()
    test_negation_other_patterns_allowed()
    test_context_separation()
    test_user_allowed_negation_phrases()
    test_user_forbidden_positive_phrases()
    test_real_ludovic_phrase_is_allowed()
    print("\nTous les tests safety sont OK")
