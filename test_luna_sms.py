#!/usr/bin/env python3
"""
Test End-to-End Luna SMS - Pour les tests avec Freddy

Ce script teste toute la chaîne:
1. Configuration Twilio
2. Envoi de SMS
3. Système de quotas
4. Flow de confirmation
5. Alertes contacts de confiance

Usage:
    # Configurer d'abord le .env
    cp .env.example .env
    # Éditer .env avec les vrais credentials Twilio

    # Lancer les tests
    python test_luna_sms.py

    # Envoyer un vrai SMS de test
    python test_luna_sms.py --send +33612345678 "Bonjour depuis Luna !"

    # Test complet avec numéro Freddy
    python test_luna_sms.py --full +33612345678
"""
import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Charge le .env si présent
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# Imports Luna
from integrations.twilio import TwilioSMSClient
from core.actions import (
    ConfirmationManager,
    ActionDispatcher,
    QuotaGuard,
    QuotaStatus,
    ActionRequest,
    ActionType,
    ActionStatus,
)
from core.actions.quota_guard import PlanType

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_luna")


# =============================================================================
# COULEURS TERMINAL
# =============================================================================

class C:
    """Couleurs pour le terminal"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"

def ok(msg): print(f"  {C.GREEN}OK{C.END} {msg}")
def fail(msg): print(f"  {C.RED}FAIL{C.END} {msg}")
def info(msg): print(f"  {C.BLUE}INFO{C.END} {msg}")
def warn(msg): print(f"  {C.YELLOW}WARN{C.END} {msg}")
def title(msg): print(f"\n{C.BOLD}{C.CYAN}{'='*60}{C.END}\n{C.BOLD}{C.CYAN}  {msg}{C.END}\n{C.BOLD}{C.CYAN}{'='*60}{C.END}")


# =============================================================================
# ADAPTATEUR SMS pour le système Actions
# =============================================================================

class SMSServiceAdapter:
    """
    Adapte TwilioSMSClient pour le système d'actions Luna.
    Le dispatcher attend send_sms(tenant_id, phone, body) -> (bool, dict)
    """
    def __init__(self, twilio_client: TwilioSMSClient):
        self.client = twilio_client

    async def send_sms(self, tenant_id: int, phone: str, body: str):
        """Interface async attendue par le dispatcher"""
        return await self.client.send_async(phone, body)


# =============================================================================
# TESTS
# =============================================================================

def test_1_twilio_config():
    """Test 1: Configuration Twilio"""
    title("TEST 1: Configuration Twilio")

    client = TwilioSMSClient.from_env()
    status = client.get_status()

    if status["configured"]:
        ok(f"Twilio configuré avec le numéro {status['from_number']}")
    else:
        fail("Twilio non configuré !")
        warn("Vérifiez votre fichier .env avec les credentials Twilio")
        return None

    return client


def test_2_phone_normalization():
    """Test 2: Normalisation des numéros"""
    title("TEST 2: Normalisation des numéros FR")

    tests = [
        ("0612345678", "+33612345678"),
        ("06 12 34 56 78", "+33612345678"),
        ("+33612345678", "+33612345678"),
        ("33612345678", "+33612345678"),
    ]

    all_pass = True
    for input_phone, expected in tests:
        result = TwilioSMSClient.normalize_phone(input_phone)
        if result == expected:
            ok(f'"{input_phone}" -> "{result}"')
        else:
            fail(f'"{input_phone}" -> "{result}" (attendu: "{expected}")')
            all_pass = False

    return all_pass


def test_3_segments():
    """Test 3: Estimation des segments"""
    title("TEST 3: Estimation segments SMS")

    tests = [
        ("Bonjour", 1),
        ("A" * 160, 1),
        ("A" * 161, 2),
        ("A" * 306, 2),
        ("A" * 307, 3),
    ]

    all_pass = True
    for body, expected in tests:
        result = TwilioSMSClient.estimate_segments(body)
        if result == expected:
            ok(f'{len(body)} chars -> {result} segment(s)')
        else:
            fail(f'{len(body)} chars -> {result} (attendu: {expected})')
            all_pass = False

    return all_pass


def test_4_quotas():
    """Test 4: Système de quotas"""
    title("TEST 4: Quotas par forfait")

    guard = QuotaGuard()

    # Test chaque forfait
    for plan in PlanType:
        guard.set_plan(1, plan)
        guard.reset_monthly_usage(1)

        from core.actions.quota_guard import PLAN_SMS_LIMITS
        limit = PLAN_SMS_LIMITS[plan]

        status = guard.check(1, ActionType.SEND_SMS)
        if status.allowed and status.limit == limit:
            ok(f"Forfait {plan.value}: {limit} SMS/mois - quota OK")
        else:
            fail(f"Forfait {plan.value}: erreur quota")

    # Test dépassement (Essentiel = 20 SMS)
    guard.set_plan(1, PlanType.ESSENTIEL)
    guard.reset_monthly_usage(1)

    # Simule 20 SMS envoyés (100% du quota Essentiel)
    for _ in range(20):
        guard.increment(1, ActionType.SEND_SMS, 1)

    status = guard.check(1, ActionType.SEND_SMS)
    if not status.allowed:
        ok(f"Blocage à 100%: {status.used}/{status.limit} - correct")
    else:
        fail("Pas de blocage à 100% !")

    # Test alerte 80% (16/20 = 80%)
    guard.reset_monthly_usage(1)
    for _ in range(16):
        guard.increment(1, ActionType.SEND_SMS, 1)

    status = guard.check(1, ActionType.SEND_SMS)
    if status.should_warn:
        ok(f"Alerte 80%: {status.percentage:.0f}% utilisé - warning actif")
    else:
        fail("Pas d'alerte à 80% !")

    # Test message Luna limite conversation (18/20 = 90%)
    guard.reset_monthly_usage(1)
    for _ in range(18):
        guard.increment(1, ActionType.SEND_SMS, 1)

    limit_msg = guard.should_luna_limit_conversation(1)
    if limit_msg:
        ok(f"Luna limite conversation à 90%")
        info(f'Luna dirait: "{limit_msg[:60]}..."')
    else:
        fail("Luna ne limite pas à 90%")

    return True


def test_5_confirmation_flow():
    """Test 5: Flow de confirmation"""
    title("TEST 5: Flow de confirmation (zéro surprise)")

    cm = ConfirmationManager()

    # 1. Luna propose d'envoyer un SMS
    request = cm.propose_action(
        tenant_id=1,
        action_type=ActionType.SEND_SMS,
        target="Marie",
        description="envoyer un SMS à Marie",
        message_body="Bonjour Marie, votre proche va bien.",
    )

    if request.status == ActionStatus.AWAITING_CONFIRMATION:
        ok(f"Action proposée: {request.description}")
    else:
        fail("Statut incorrect après proposition")

    # 2. Luna construit le message de confirmation
    prompt = cm.build_confirmation_prompt(request)
    ok(f'Luna demande: "{prompt}"')

    # 3. Le souscripteur confirme
    confirmed = cm.confirm(1, request.action_id, method="voice")
    if confirmed and confirmed.confirmed:
        ok("Souscripteur a confirmé (voice)")
    else:
        fail("Confirmation échouée")

    # 4. Test rejet
    request2 = cm.propose_action(
        tenant_id=1,
        action_type=ActionType.SEND_SMS,
        target="Pierre",
        description="envoyer un SMS à Pierre",
    )
    rejected = cm.reject(1, request2.action_id, reason="pas maintenant")
    if rejected and rejected.status == ActionStatus.REJECTED:
        ok(f"Action rejetée: {rejected.rejection_reason}")
    else:
        fail("Rejet échoué")

    # 5. Test expiration
    request3 = cm.propose_action(
        tenant_id=1,
        action_type=ActionType.SEND_SMS,
        target="Jean",
        description="envoyer un SMS à Jean",
        expiration_minutes=0,  # Expire immédiatement
    )
    request3.expires_at = datetime.utcnow() - timedelta(seconds=1)

    expired = cm.confirm(1, request3.action_id)
    if expired is None:
        ok("Action expirée correctement")
    else:
        fail("L'action aurait dû expirer")

    # 6. Test bypass urgence
    emergency = cm.propose_action(
        tenant_id=1,
        action_type=ActionType.ALERT_CONTACTS,
        target="tous",
        description="alerter les contacts",
        source="emergency_critical",
    )
    if emergency.confirmed:
        ok("Urgence critique: auto-confirmée (bypass)")
    else:
        fail("Urgence critique: devrait être auto-confirmée")

    return True


async def test_6_send_real_sms(client: TwilioSMSClient, phone: str, body: str):
    """Test 6: Envoi réel de SMS"""
    title("TEST 6: Envoi SMS réel via Twilio")

    info(f"Envoi vers: {phone}")
    info(f"Message: {body}")

    success, result = await client.send_async(phone, body)

    if success:
        ok(f"SMS envoyé ! SID: {result['sid']}")
        ok(f"Statut: {result['status']}, Segments: {result['segments']}")
        return True
    else:
        fail(f"Erreur: {result['error']}")
        if result.get("code"):
            warn(f"Code erreur Twilio: {result['code']}")
        return False


async def test_7_full_flow(client: TwilioSMSClient, phone: str):
    """Test 7: Flow complet Luna (confirmation + envoi + quota)"""
    title("TEST 7: Flow complet Luna -> Confirmation -> Envoi")

    # Setup
    sms_adapter = SMSServiceAdapter(client)
    cm = ConfirmationManager()
    qg = QuotaGuard()
    qg.set_plan(1, PlanType.ESSENTIEL)
    qg.reset_monthly_usage(1)

    dispatcher = ActionDispatcher(
        confirmation_manager=cm,
        quota_guard=qg,
        sms_service=sms_adapter,
    )

    # 1. Luna propose
    info("1. Luna propose d'envoyer un SMS...")
    request = cm.propose_action(
        tenant_id=1,
        action_type=ActionType.SEND_SMS,
        target="Freddy",
        target_phone=phone,
        description="envoyer un SMS de test à Freddy",
        message_body="[YAWatch Luna] Test reussi ! Luna peut envoyer des SMS. Les quotas et confirmations fonctionnent.",
    )

    prompt = cm.build_confirmation_prompt(request)
    ok(f'Luna: "{prompt}"')

    # 2. Confirmation
    info("2. Souscripteur confirme...")
    cm.confirm(1, request.action_id, method="test_script")
    ok("Confirmé !")

    # 3. Mise à jour avec le numéro résolu
    request.target_phone = TwilioSMSClient.normalize_phone(phone)

    # 4. Dispatch
    info("3. Envoi via Twilio...")
    result = await dispatcher.dispatch(request)

    if result.success:
        ok(f"SMS envoyé avec succès !")
        ok(f"Message: {result.message}")

        # 5. Vérification quota
        usage = qg.get_usage_summary(1)
        ok(f"Quota: {usage['sms']['used']}/{usage['sms']['limit']} SMS utilisés")

        # Message de complétion Luna
        completion = cm.build_completion_message(request, True)
        ok(f'Luna dirait: "{completion}"')
    else:
        fail(f"Échec: {result.error}")
        completion = cm.build_completion_message(request, False, result.error)
        warn(f'Luna dirait: "{completion}"')

    return result.success


async def test_8_alert_contacts(client: TwilioSMSClient, phone: str):
    """Test 8: Alerte contacts de confiance"""
    title("TEST 8: Alerte contacts de confiance")

    info("Simulation d'alerte aux contacts...")
    info(f"Contact test: {phone}")

    success, result = await client.send_async(
        phone,
        "[YAWatch Luna] ALERTE TEST: Ceci est un test d'alerte. "
        "Votre proche va bien. Si ce n'etait pas un test, nous vous "
        "recommanderions fortement d'appeler les secours si necessaire.",
    )

    if success:
        ok(f"Alerte envoyée ! SID: {result['sid']}")
        return True
    else:
        fail(f"Erreur: {result['error']}")
        return False


# =============================================================================
# RÉSUMÉ
# =============================================================================

def print_summary(results: dict):
    """Affiche le résumé des tests"""
    title("RÉSUMÉ DES TESTS")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    for name, result in results.items():
        status = f"{C.GREEN}PASS{C.END}" if result else f"{C.RED}FAIL{C.END}"
        print(f"  [{status}] {name}")

    print(f"\n  {C.BOLD}Total: {passed}/{total} réussis{C.END}")

    if failed == 0:
        print(f"\n  {C.GREEN}{C.BOLD}TOUT EST PRÊT POUR LES TESTS !{C.END}")
    else:
        print(f"\n  {C.RED}{C.BOLD}{failed} test(s) échoué(s){C.END}")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Test End-to-End Luna SMS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python test_luna_sms.py                          # Tests unitaires (pas d'envoi)
  python test_luna_sms.py --send +33612345678 "Hello"  # Envoyer un SMS
  python test_luna_sms.py --full +33612345678      # Test complet avec envoi
        """,
    )
    parser.add_argument("--send", nargs=2, metavar=("PHONE", "MESSAGE"),
                       help="Envoyer un SMS de test")
    parser.add_argument("--full", metavar="PHONE",
                       help="Test complet avec envoi réel")
    args = parser.parse_args()

    results = {}

    # Tests unitaires (toujours exécutés)
    client = test_1_twilio_config()
    results["Configuration Twilio"] = client is not None

    results["Normalisation numéros"] = test_2_phone_normalization()
    results["Estimation segments"] = test_3_segments()
    results["Système de quotas"] = test_4_quotas()
    results["Flow de confirmation"] = test_5_confirmation_flow()

    # Tests avec envoi réel
    if args.send and client:
        phone, message = args.send
        results["Envoi SMS réel"] = await test_6_send_real_sms(client, phone, message)

    if args.full and client:
        phone = args.full
        results["Flow complet Luna"] = await test_7_full_flow(client, phone)
        results["Alerte contacts"] = await test_8_alert_contacts(client, phone)

    # Résumé
    print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
