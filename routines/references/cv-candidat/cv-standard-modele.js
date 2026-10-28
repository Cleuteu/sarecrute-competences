const ANONYME = false;

const CANDIDAT = {
  reference:   "SR-MODELE",

  prenom:      "Dossier candidat",
  nom:         "",
  sousTitre:   "Modèle standard · toutes les valeurs viennent des champs Airtable",
  titre:       "Titre du dossier anonymisé",

  accroche:    "Modèle de référence des dossiers de présentation SaRecrute : tous portent ces champs, dans cet ordre, et à cette taille. Chaque valeur affichée est la recopie d'un champ Airtable vérifié par les recruteuses — ni le CV joint à la fiche, ni l'enrichissement automatique ne l'alimentent. Un champ vide fait disparaître sa ligne. Chaque ligne ci-dessous porte le nom du champ qui l'alimente, et les compétences reprennent le référentiel complet des actes, groupé par espèce puis par famille.",

  contact: {
    email:     "Mail",
    telephone: "Téléphone"
  },

  cadre: {
    experience:    "Années d'expérience",
    disponibilite: "Date de disponibilité",
    contrat:       "Statuts contractuels",
    tempsTravail:  "Type de temps de travail",
    gardes:        "Gardes",
    remuneration:  "Rémunération souhaitée",
    mobilite:      ""
  },

  pratiques:    ["Pratiques", "Spécialités"],
  specialites:  [],
  recherche:    ["Pratiques", "Spécialités"],

  formation: {
    ecole:        "Ecole véto",
    anneeSortie:  "Année de sortie",
    internat:     "Oui",
    desv:         "Oui",
    diplomeSup:   "Diplôme supplémentaire",
    habilitation: "Oui"
  },

  langues: ["Langues"],
  // Référentiel complet des actes (table Actes, tblt32Afmq6vQ6FJS) : 53 actes,
  // chacun avec son espèce et sa famille. Aucune cotation ici — sur un dossier
  // réel, chaque acte porte le Niveau saisi dans la table Compétences
  // (tblH8Zym1DNu7PN3c). Le regroupement espèce puis famille est automatique.
  competences: [
    { espece:"Canine", famille:"Chirurgie de convenance",  acte:"Castration CN",       niveau:"Non évalué" },
    { espece:"Canine", famille:"Chirurgie de convenance",  acte:"Castration CT",       niveau:"Non évalué" },
    { espece:"Canine", famille:"Chirurgie de convenance",  acte:"Stérilisation CN",    niveau:"Non évalué" },
    { espece:"Canine", famille:"Chirurgie de convenance",  acte:"Stérilisation CT",    niveau:"Non évalué" },
    { espece:"Canine", famille:"Chirurgie tissus mous",    acte:"Mastectomie",         niveau:"Non évalué" },
    { espece:"Canine", famille:"Chirurgie tissus mous",    acte:"Retrait GA",          niveau:"Non évalué" },
    { espece:"Canine", famille:"Chirurgie tissus mous",    acte:"Retrait masse",       niveau:"Non évalué" },
    { espece:"Canine", famille:"Chirurgie tissus mous",    acte:"SDTE",                niveau:"Non évalué" },
    { espece:"Canine", famille:"Reproduction / obstétrique", acte:"Césarienne CN",     niveau:"Non évalué" },
    { espece:"Canine", famille:"Reproduction / obstétrique", acte:"Césarienne CT",     niveau:"Non évalué" },
    { espece:"Canine", famille:"Imagerie",                 acte:"Échographie",         niveau:"Non évalué" },
    { espece:"Canine", famille:"Anesthésie / réanimation", acte:"Intubation",          niveau:"Non évalué" },
    { espece:"Canine", famille:"Médecine / consultation",  acte:"Examen clinique",     niveau:"Non évalué" },
    { espece:"Canine", famille:"Dentisterie",              acte:"Détartrage",          niveau:"Non évalué" },
    { espece:"Canine", famille:"Dentisterie",              acte:"Extraction dentaire", niveau:"Non évalué" },
    { espece:"Canine", famille:"Soins techniques",         acte:"Perfusion, pose de cathéter et prise de sang", niveau:"Non évalué" },
    { espece:"Canine", famille:"Soins techniques",         acte:"Pose sonde d'œsophagostomie", niveau:"Non évalué" },
    { espece:"Canine", famille:"Soins techniques",         acte:"Pose sonde urinaire", niveau:"Non évalué" },

    { espece:"Bovins", famille:"Chirurgie tissus mous",    acte:"Caillette",           niveau:"Non évalué" },
    { espece:"Bovins", famille:"Chirurgie tissus mous",    acte:"Problèmes de mamelles (obstruction, déchirure)", niveau:"Non évalué" },
    { espece:"Bovins", famille:"Reproduction / obstétrique", acte:"Césarienne",        niveau:"Non évalué" },
    { espece:"Bovins", famille:"Reproduction / obstétrique", acte:"Délivrance",        niveau:"Non évalué" },
    { espece:"Bovins", famille:"Reproduction / obstétrique", acte:"Vêlage",            niveau:"Non évalué" },
    { espece:"Bovins", famille:"Reproduction / obstétrique", acte:"Échographies de gestation", niveau:"Non évalué" },
    { espece:"Bovins", famille:"Médecine / consultation",  acte:"Examen clinique",     niveau:"Non évalué" },
    { espece:"Bovins", famille:"Élevage / troupeau",       acte:"Prophylaxie",         niveau:"Non évalué" },
    { espece:"Bovins", famille:"Soins techniques",         acte:"Drenchage",           niveau:"Non évalué" },
    { espece:"Bovins", famille:"Soins techniques",         acte:"Perfusion et pose de cathéter", niveau:"Non évalué" },
    { espece:"Bovins", famille:"Soins techniques",         acte:"Parage",              niveau:"Non évalué" },
    { espece:"Bovins", famille:"Soins techniques",         acte:"Écornage",            niveau:"Non évalué" },

    { espece:"Ovin/Caprin", famille:"Chirurgie de convenance", acte:"Castration",      niveau:"Non évalué" },
    { espece:"Ovin/Caprin", famille:"Chirurgie tissus mous", acte:"Problèmes de mamelles", niveau:"Non évalué" },
    { espece:"Ovin/Caprin", famille:"Reproduction / obstétrique", acte:"Césarienne",   niveau:"Non évalué" },
    { espece:"Ovin/Caprin", famille:"Médecine / consultation", acte:"Examen clinique", niveau:"Non évalué" },
    { espece:"Ovin/Caprin", famille:"Élevage / troupeau",  acte:"Prophylaxie",         niveau:"Non évalué" },
    { espece:"Ovin/Caprin", famille:"Soins techniques",    acte:"Parage",              niveau:"Non évalué" },
    { espece:"Ovin/Caprin", famille:"Soins techniques",    acte:"Perfusion et pose de cathéter", niveau:"Non évalué" },
    { espece:"Ovin/Caprin", famille:"Soins techniques",    acte:"Écornage",            niveau:"Non évalué" },

    { espece:"Equine", famille:"Reproduction / obstétrique", acte:"Délivrance",        niveau:"Non évalué" },
    { espece:"Equine", famille:"Reproduction / obstétrique", acte:"Fouille",           niveau:"Non évalué" },
    { espece:"Equine", famille:"Reproduction / obstétrique", acte:"Lavage utérin",     niveau:"Non évalué" },
    { espece:"Equine", famille:"Reproduction / obstétrique", acte:"Échographie de gestation et IA", niveau:"Non évalué" },
    { espece:"Equine", famille:"Médecine / consultation",  acte:"Vaccination",         niveau:"Non évalué" },
    { espece:"Equine", famille:"Dentisterie",              acte:"Dentisterie",         niveau:"Non évalué" },
    { espece:"Equine", famille:"Soins techniques",         acte:"Perfusion et prise de sang", niveau:"Non évalué" },
    { espece:"Equine", famille:"Soins techniques",         acte:"Sondage",             niveau:"Non évalué" },

    { espece:"NAC", famille:"Chirurgie de convenance",     acte:"Stérilisation",       niveau:"Non évalué" },
    { espece:"NAC", famille:"Imagerie",                    acte:"Radiographie",        niveau:"Non évalué" },
    { espece:"NAC", famille:"Médecine / consultation",     acte:"Examen clinique",     niveau:"Non évalué" },
    { espece:"NAC", famille:"Soins techniques",            acte:"Pose de cathéter",    niveau:"Non évalué" },

    { espece:"Porcin", famille:"Chirurgie de convenance",  acte:"Castration",          niveau:"Non évalué" },
    { espece:"Porcin", famille:"Chirurgie de convenance",  acte:"Stérilisation",       niveau:"Non évalué" },
    { espece:"Porcin", famille:"Anesthésie / réanimation", acte:"Anesthésie",          niveau:"Non évalué" }
  ]
};
