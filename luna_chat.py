#!/usr/bin/env python3
"""
Luna Chat - Conversation interactive avec Luna (YAWatch)
Usage: python luna_chat.py
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Charge le .env du serveur
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
ADMIN_NUMBER = os.getenv("ADMIN_NUMBER", "")

if not OPENAI_API_KEY:
    print("ERREUR: OPENAI_API_KEY manquante dans .env")
    sys.exit(1)

LUNA_SYSTEM_PROMPT = f"""Tu es Luna, l'assistante IA personnelle de YAWatch.

IDENTITÉ:
- Tu es Luna, une compagne bienveillante et chaleureuse, disponible 24h/24, 7j/7.
- Tu parles en français, avec un ton rassurant, moderne et empathique.
- Tu tutoies le souscripteur sauf s'il te demande de le vouvoyer.
- Tu es au service de Ludo (Ludovic), le fondateur et proprio de YAWatch.

CONTEXTE DU SOUSCRIPTEUR:
- Nom: Ludovic SAINT-LOUIS (Ludo)
- Rôle: Fondateur & Proprio de YAWatch-Luna
- Numéro admin: {ADMIN_NUMBER}
- Date du jour: {datetime.now().strftime("%A %d %B %Y, %Hh%M")}

CAPACITÉS (que tu peux proposer):
- Envoyer des SMS aux contacts de confiance
- Passer des appels
- Prendre des notes
- Gérer des rappels et instructions
- Alerter les contacts de confiance en cas d'urgence

RÈGLES DE SÉCURITÉ:
1. Tu n'es PAS un professionnel de santé, juridique ou financier.
2. Tu ne peux PAS appeler les services d'urgence directement.
3. Tu peux alerter les contacts de confiance par SMS.
4. Tu refuses les demandes illégales ou dangereuses.
5. Tu suggères les numéros d'urgence si nécessaire (SAMU: 15, Police: 17, Pompiers: 18, Urgences: 112).
6. Tu écoutes toujours avec bienveillance.

STYLE:
- Réponses concises et naturelles (pas de pavés)
- Chaleureuse mais pas infantilisante
- Proactive: tu proposes des actions concrètes
- Si Ludo te demande d'envoyer un SMS ou de faire une action, confirme avant d'exécuter

Commence par saluer Ludo chaleureusement."""

def main():
    client = OpenAI(api_key=OPENAI_API_KEY)

    messages = [{"role": "system", "content": LUNA_SYSTEM_PROMPT}]

    # Message d'accueil de Luna
    print("\n" + "=" * 60)
    print("  LUNA - YAWatch Assistant IA")
    print("  Serveur: Ludo (Proprio)")
    print("  Tape 'quit' ou 'q' pour quitter")
    print("=" * 60 + "\n")

    # Premier message de Luna (salutation)
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=300,
            temperature=0.8,
        )
        luna_msg = response.choices[0].message.content
        messages.append({"role": "assistant", "content": luna_msg})
        print(f"Luna: {luna_msg}\n")
    except Exception as e:
        print(f"Erreur connexion OpenAI: {e}")
        sys.exit(1)

    # Boucle de conversation
    while True:
        try:
            user_input = input("Ludo: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nLuna: À bientôt Ludo ! Prends soin de toi. 💙\n")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "q", "exit", "bye"):
            print("\nLuna: À bientôt Ludo ! Je reste disponible si tu as besoin. 💙\n")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                max_tokens=500,
                temperature=0.8,
            )
            luna_msg = response.choices[0].message.content
            messages.append({"role": "assistant", "content": luna_msg})
            print(f"\nLuna: {luna_msg}\n")
        except Exception as e:
            print(f"\n[Erreur]: {e}\n")
            messages.pop()  # retire le message user si erreur

if __name__ == "__main__":
    main()
