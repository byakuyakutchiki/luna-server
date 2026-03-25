# Duffel Services Agreement - Resume pour Integration Luna

**Source**: https://duffel.com/terms (maj 09 Oct 2025)
**Entite**: Duffel Technology Limited, UK (company 11188295)

## Points cles pour Luna

### Pricing (Pay-as-you-go)
- **0€ abonnement** — pay-as-you-go
- **Vols**: 3$/order + 1% Managed Content
- **Stays (hotels)**: Profit share sur bookings materialises
- **Ancillaires**: 2$/ancillaire paye
- **Recherches excessives**: 0.005$/search au-dela du ratio 1500:1 (search:order)
- **FX**: 2% sur conversions de devises

### Ce que Luna peut faire
- Rechercher vols (300+ compagnies)
- Reserver vols directement via API (Flight Create Orders)
- Rechercher hotels (Stays API)
- Reserver hotels directement
- Gerer annulations/modifications
- Collecter paiements via Duffel Payments (Stripe Connect)

### Obligations de Luna (Customer)
1. **KYC obligatoire** avant production (test env dispo immediatement)
2. **Afficher les T&C du Supplier** au Traveller avant reservation
3. **Support 1ere ligne** = responsabilite Luna (sauf si Traveller Support souscrit)
4. **PCI-DSS compliance** pour donnees cartes
5. **Ratio search/order** max 1500:1 sinon surfacturation
6. **Anti-fraude** obligatoire pour pay-by-card
7. **Pas de metasearch** (clause 2.5d)
8. **Pas de revente** a des tiers (clause 2.5e)

### Donnees personnelles collectees (Traveller)
- Nom, prenom, date de naissance, genre
- Passeport (numero, pays, expiration)
- Email, telephone
- Programme fidelite
- Infos carte bancaire

### Responsabilites
- **Duffel** = intermediaire technique, PAS responsable des services de voyage
- **Supplier** = responsable des vols/hotels
- **Luna** = responsable du support client, anti-fraude, conformite
- **Contrat de voyage** = entre Traveller et Supplier directement

### Settlement (paiement fournisseurs)
- **Duffel Settlement** (Managed Content): Duffel paie les suppliers, Luna maintient un solde ("Balance")
- **Pay by Card**: carte du Traveller chargee directement par le supplier
- **Duffel Payments**: Stripe Connect pour collecter les fonds des Travellers

### Resiliation
- PAYG: resiliable a tout moment par l'une ou l'autre partie
- Order Form: terme initial non resiliable, puis preavis 60 jours
- Breach materiel: 30 jours pour remedier

### Juridiction
- Droit anglais (England & Wales)
- Tribunaux anglais competents

## Integration technique prevue

```
DUFFEL_ACCESS_TOKEN=duffel_test_xxx  (test)
DUFFEL_ACCESS_TOKEN=duffel_live_xxx  (production)
```

### Flux reservation vol:
1. POST /air/offer_requests → recherche vols
2. GET /air/offers/{id} → details offre
3. POST /air/orders → creer reservation (avec infos Traveller)
4. Paiement via Duffel Payments ou Balance

### Flux reservation hotel:
1. POST /stays/search → recherche hotels
2. GET /stays/quotes/{id} → details + prix
3. POST /stays/bookings → creer reservation
4. Paiement via Stays Payment Instruction

### SDK Python:
```bash
pip install duffel-api
```

```python
from duffel_api import Duffel
client = Duffel(access_token="duffel_test_xxx")

# Recherche vols
offer_request = client.offer_requests.create({
    "slices": [{"origin": "CDG", "destination": "NCE", "departure_date": "2026-04-01"}],
    "passengers": [{"type": "adult"}]
})

# Reserver
order = client.orders.create({
    "selected_offers": [offer.id],
    "passengers": [{
        "id": passenger.id,
        "given_name": "Jean",
        "family_name": "Dupont",
        "email": "jean@example.com",
        "phone_number": "+33612345678",
        "born_on": "1985-03-15",
        "gender": "m"
    }],
    "type": "instant",
    "payments": [{"type": "balance", "amount": offer.total_amount, "currency": offer.total_currency}]
})
```
