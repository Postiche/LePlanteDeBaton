# Guide d'utilisation

## Se connecter

Ouvrez l'adresse de votre instance (ex. `https://immo.mondomaine.fr`) et saisissez votre identifiant et votre mot de passe. Après 5 échecs, la connexion est bloquée 15 minutes. Une session inactive expire après 8 heures, et dans tous les cas après 7 jours.

Si l'administrateur vous a créé un compte, vous recevez un **mot de passe temporaire** : changez-le dans *Mon compte* (icône avec vos initiales, en bas du menu). Mot de passe oublié : demandez un lien de réinitialisation à l'administrateur.

Dans *Mon compte*, renseignez aussi votre téléphone, votre email et votre signature : ils apparaissent dans les emails et les fiches PDF.

## Installer l'application sur un téléphone ou une tablette

- **iPhone / iPad (Safari)** : bouton Partager › « Sur l'écran d'accueil ».
- **Android (Chrome)** : menu ⋮ › « Installer l'application » ou « Ajouter à l'écran d'accueil ».
- **Windows (Edge / Chrome)** : icône d'installation dans la barre d'adresse.

Hors connexion, l'application affiche un message et ne montre aucune donnée : par sécurité, rien n'est conservé sur l'appareil.

## Tableau de bord

Indicateurs (offres, demandes, nouveaux biens, correspondances, visites, relances), filtrables par période et par type de données (réelles / démonstration). Cliquez sur un indicateur ou une barre de graphique pour ouvrir la liste correspondante.

## Offres immobilières

- **Créer** : bouton *+ Offre*. Ne saisissez que ce que vous savez : un champ vide reste « Non renseigné » et ne sera jamais interprété comme une valeur.
- **Doublons** : si une offre semble déjà exister (même référence, même URL source, ou même code postal avec une surface proche), l'application vous le signale avant d'enregistrer.
- **Localisation** : le département et la région sont déduits du code postal. Les coordonnées GPS sont obtenues automatiquement si le géocodage est disponible ; sinon, saisissez-les ou utilisez *Géocoder l'adresse* sur la fiche.
- **Photos et documents** : onglet *Photos et documents* de la fiche ; depuis un téléphone, vous pouvez prendre une photo directement. La position GPS contenue dans les photos est supprimée.
- **Fiche PDF** : bouton *Fiche PDF* (photos, caractéristiques, localisation et coordonnées du commercial — jamais celles du propriétaire).
- **Archiver** plutôt que supprimer : l'offre sort du matching mais reste consultable.
- **Exporter** : boutons Excel / CSV de la liste.

## Demandes clients

Bouton *+ Demande*. Renseignez le client (fiche CRM ou texte libre), les types de biens, la transaction, la localisation (communes, codes postaux, départements, régions, ou un centre + rayon), les surfaces, le budget (prix total pour un achat, **loyer annuel HT HC** pour une location), les contraintes techniques et la date souhaitée.

**Critères impératifs** : cochez uniquement les critères explicitement non négociables pour le client. Un bien qui ne les respecte pas est écarté ; un bien dont l'information manque n'est jamais écarté mais signalé « à vérifier ».

## Correspondances (matching)

Le score sur 100 est recalculé automatiquement à chaque modification d'une offre, d'une demande ou des pondérations :

| Critère | Poids initial |
|---|---|
| Localisation | 30 |
| Surface | 25 |
| Budget | 20 |
| Typologie et transaction | 10 |
| Caractéristiques techniques | 10 |
| Disponibilité | 5 |

- Un critère non exprimé par le client rapporte tous ses points.
- Une information **manquante** sur l'offre ne rapporte aucun point ; le **score potentiel** indique ce que le bien obtiendrait si elle s'avérait favorable.
- *Détail du score* liste les critères satisfaits (✓), les écarts (~ ou ✕) et les informations manquantes (?).
- Les pondérations et le score minimum d'enregistrement se règlent dans *Paramètres › Matching*.

Depuis une **demande** (onglet *Biens correspondants*) ou une **offre** (onglet *Clients correspondants*), vous voyez les correspondances calculées en direct. Le menu *Correspondances* présente le pipeline commercial : À contacter → Email préparé → Contacté → En attente de réponse → Visite proposée → Visite confirmée → Visite effectuée → Négociation → Sans suite.

Sur une demande, cochez plusieurs biens pour préparer un **email de sélection** ou un **dossier PDF**.

## Rechercher des biens (multisource)

Sur une fiche demande, bouton **Rechercher des biens** :

1. **Base interne** : biens compatibles avec score et explication.
2. **BureauxLocaux** et **Geolocaux** : la recherche automatique n'est pas disponible (aucune API officielle configurée). L'application affiche les critères à reporter (bouton *Copier les critères*) et ouvre la plateforme dans un nouvel onglet.
3. Pour chaque annonce intéressante, *Importer une annonce* : collez l'URL et reportez les informations affichées. L'annonce est alors scorée par rapport à la demande, contrôlée contre les doublons, et peut être *Enregistrée dans la base* après vérification des champs.

Chaque recherche est conservée dans l'historique (*Annonces externes*). Une annonce non revérifiée depuis plus de 14 jours (réglable) est marquée « À revérifier » : utilisez *Toujours en ligne* ou *Retirée*.

N'enregistrez les coordonnées d'un annonceur que si elles sont publiques et que leur utilisation est autorisée.

## Imports de fichiers

Menu *Imports* : choisissez « offres » ou « demandes », puis un fichier.

- **Excel / CSV** : une ligne par élément ; les en-têtes usuels sont reconnus (« Surface totale », « Loyer annuel », « Code postal », « Accès PL »…). Les colonnes non reconnues sont signalées.
- **PDF / Word** : fiche commerciale ou email de demande. Les valeurs trouvées sont affichées avec l'extrait du document dont elles proviennent. Les PDF scannés (images) ne sont pas lus.

Rien n'est enregistré avant que vous cliquiez sur **Valider**. Pour chaque ligne : *Créer*, *Ignorer* ou, si un doublon est détecté, *Compléter une offre existante* (seuls les champs vides de l'offre existante sont complétés).

## Contacts, entreprises, historique, relances

- Chaque fiche contact affiche les coordonnées réellement disponibles et les actions **Copier**, **Appeler** (ouvre le composeur sur smartphone), **Préparer un email**.
- L'onglet *Historique* (contacts, offres, demandes) regroupe appels, notes, emails, visites et changements de statut. Ajoutez une note et, si besoin, une date de **rappel** : elle apparaît dans *Relances* et sur le tableau de bord.
- Indiquez l'**origine** de chaque contact (salon, recommandation, annonce publique…) et cochez « S'oppose à la prospection » si la personne l'a demandé : un avertissement s'affichera lors de la préparation d'un email.

## Emails

Le bouton *Email* ouvre un éditeur prérempli (destinataire, objet, corps avec les caractéristiques réellement renseignées et l'adéquation avec la recherche). Six modèles : présentation d'un bien, sélection de biens, proposition de visite, demande d'informations à un annonceur, relance, compte rendu. Tout le texte est modifiable.

Actions :
- **Copier le texte** ;
- **Ouvrir dans la messagerie** (`mailto:` — sans pièce jointe ; corps tronqué au-delà d'environ 1 800 caractères) ;
- **Fichier .eml** : brouillon avec les fiches PDF en pièces jointes, à ouvrir dans Outlook (classique ou nouveau), Apple Mail, Thunderbird ;
- **Brouillon Outlook** (si activé, Windows + Outlook classique + agent local).

**L'application n'envoie jamais d'email.** Après l'avoir envoyé depuis votre messagerie, cochez « Je confirme avoir envoyé ce message » puis *Marquer comme envoyé* : l'historique et le statut de la correspondance sont alors mis à jour.

## Visites

*Proposer une visite* (depuis une offre, une correspondance ou une demande) : choisissez un ou plusieurs créneaux, puis l'email de proposition est généré. La visite reste « Proposée » jusqu'à ce que **vous** saisissiez le créneau confirmé par le client (*Visites › Saisir la confirmation*). Après la visite : *Visite effectuée* + compte rendu, puis email de compte rendu si besoin.

## Carte

Menu *Carte* : offres géolocalisées (filtres type, transaction, surface) et zone de recherche d'une demande (rayon). Les offres non géocodées sont listées sous la carte. Aucune coordonnée de contact n'apparaît sur la carte.

## Outlook classique (facultatif, Windows)

1. Sur le poste Windows : installez Python, puis lancez `outlook-agent\lancer-agent-outlook.bat` après avoir indiqué l'adresse de votre instance dans la variable `IMMOPRO_ORIGIN` (ex. `https://immo.mondomaine.fr`).
2. Notez le **jeton d'appairage** affiché.
3. Dans ImmoPro : *Paramètres › Outlook* : cochez « Afficher le bouton Brouillon Outlook » (administrateur), saisissez le jeton sur ce poste, puis *Tester la connexion*.

Le brouillon est créé dans Outlook avec les fiches PDF et s'ouvre à l'écran ; il n'est jamais envoyé automatiquement. Navigateurs testés pour l'accès local : Chrome et Edge.

## Données de démonstration

Les données de démonstration sont fictives, marquées **DÉMO** (badges jaunes) et ne se mélangent jamais aux données réelles dans le matching. Filtrez-les avec « Données : Réelles » ; supprimez-les avec `python -m app.cli purge-demo`.

## RGPD (administrateurs)

Sur une fiche contact : *Exporter ses données* (droit d'accès), *Anonymiser* ou *Supprimer* (droit à l'effacement). Le *Journal* (Paramètres) trace connexions, modifications, exports et générations de documents. Définissez une durée de conservation des contacts inactifs (Paramètres › Général) et purgez régulièrement.
