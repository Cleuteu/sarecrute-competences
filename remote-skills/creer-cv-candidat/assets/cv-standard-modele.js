const ANONYME = false;

const CANDIDAT = {
  reference:   "SR-MODELE",

  prenom:      "Dossier candidat",
  nom:         "",
  sousTitre:   "Modèle standard · toutes les valeurs viennent des champs Airtable",

  accroche:    "Modèle de référence des dossiers de présentation SaRecrute : tous portent ces champs, dans cet ordre, et à cette taille. Chaque valeur affichée est la recopie d'un champ Airtable vérifié par les recruteuses — ni le CV joint à la fiche, ni l'enrichissement automatique ne l'alimentent. Un champ vide fait disparaître sa ligne. Chaque ligne ci-dessous porte le nom du champ qui l'alimente, et les compétences reprennent le référentiel complet des actes.",

  contact: {
    email:     "Mail",
    telephone: "Téléphone"
  },

  cadre: {
    statut:        "Statut Recherche",
    experience:    "Années d'expérience",
    enPoste:       "En poste ?",
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
  // Référentiel complet des actes (table Actes, tblt32Afmq6vQ6FJS) : 53 actes.
  // Aucune cotation ici — sur un dossier réel, chaque acte porte le Niveau
  // saisi dans la table Compétences (tblH8Zym1DNu7PN3c).
  competences: [
    { espece:"Canine", acte:"Castration CN",                        niveau:"Non évalué" },
    { espece:"Canine", acte:"Castration CT",                        niveau:"Non évalué" },
    { espece:"Canine", acte:"Césarienne CN",                        niveau:"Non évalué" },
    { espece:"Canine", acte:"Césarienne CT",                        niveau:"Non évalué" },
    { espece:"Canine", acte:"Détartrage",                           niveau:"Non évalué" },
    { espece:"Canine", acte:"Échographie",                          niveau:"Non évalué" },
    { espece:"Canine", acte:"Examen clinique",                      niveau:"Non évalué" },
    { espece:"Canine", acte:"Extraction dentaire",                  niveau:"Non évalué" },
    { espece:"Canine", acte:"Intubation",                           niveau:"Non évalué" },
    { espece:"Canine", acte:"Mastectomie",                          niveau:"Non évalué" },
    { espece:"Canine", acte:"Perfusion, pose de cathéter et prise de sang", niveau:"Non évalué" },
    { espece:"Canine", acte:"Pose sonde d'œsophagostomie",          niveau:"Non évalué" },
    { espece:"Canine", acte:"Pose sonde urinaire",                  niveau:"Non évalué" },
    { espece:"Canine", acte:"Retrait GA",                           niveau:"Non évalué" },
    { espece:"Canine", acte:"Retrait masse",                        niveau:"Non évalué" },
    { espece:"Canine", acte:"SDTE",                                 niveau:"Non évalué" },
    { espece:"Canine", acte:"Stérilisation CN",                     niveau:"Non évalué" },
    { espece:"Canine", acte:"Stérilisation CT",                     niveau:"Non évalué" },

    { espece:"Bovins", acte:"Caillette",                            niveau:"Non évalué" },
    { espece:"Bovins", acte:"Césarienne",                           niveau:"Non évalué" },
    { espece:"Bovins", acte:"Délivrance",                           niveau:"Non évalué" },
    { espece:"Bovins", acte:"Drenchage",                            niveau:"Non évalué" },
    { espece:"Bovins", acte:"Échographies de gestation",            niveau:"Non évalué" },
    { espece:"Bovins", acte:"Écornage",                             niveau:"Non évalué" },
    { espece:"Bovins", acte:"Examen clinique",                      niveau:"Non évalué" },
    { espece:"Bovins", acte:"Parage",                               niveau:"Non évalué" },
    { espece:"Bovins", acte:"Perfusion et pose de cathéter",        niveau:"Non évalué" },
    { espece:"Bovins", acte:"Problèmes de mamelles (obstruction, déchirure)", niveau:"Non évalué" },
    { espece:"Bovins", acte:"Prophylaxie",                          niveau:"Non évalué" },
    { espece:"Bovins", acte:"Vêlage",                               niveau:"Non évalué" },

    { espece:"Ovin/Caprin", acte:"Castration",                      niveau:"Non évalué" },
    { espece:"Ovin/Caprin", acte:"Césarienne",                      niveau:"Non évalué" },
    { espece:"Ovin/Caprin", acte:"Écornage",                        niveau:"Non évalué" },
    { espece:"Ovin/Caprin", acte:"Examen clinique",                 niveau:"Non évalué" },
    { espece:"Ovin/Caprin", acte:"Parage",                          niveau:"Non évalué" },
    { espece:"Ovin/Caprin", acte:"Perfusion et pose de cathéter",   niveau:"Non évalué" },
    { espece:"Ovin/Caprin", acte:"Problèmes de mamelles",           niveau:"Non évalué" },
    { espece:"Ovin/Caprin", acte:"Prophylaxie",                     niveau:"Non évalué" },

    { espece:"Equine", acte:"Délivrance",                           niveau:"Non évalué" },
    { espece:"Equine", acte:"Dentisterie",                          niveau:"Non évalué" },
    { espece:"Equine", acte:"Échographie de gestation et IA",       niveau:"Non évalué" },
    { espece:"Equine", acte:"Fouille",                              niveau:"Non évalué" },
    { espece:"Equine", acte:"Lavage utérin",                        niveau:"Non évalué" },
    { espece:"Equine", acte:"Perfusion et prise de sang",           niveau:"Non évalué" },
    { espece:"Equine", acte:"Sondage",                              niveau:"Non évalué" },
    { espece:"Equine", acte:"Vaccination",                          niveau:"Non évalué" },

    { espece:"NAC", acte:"Examen clinique",                         niveau:"Non évalué" },
    { espece:"NAC", acte:"Pose de cathéter",                        niveau:"Non évalué" },
    { espece:"NAC", acte:"Radiographie",                            niveau:"Non évalué" },
    { espece:"NAC", acte:"Stérilisation",                           niveau:"Non évalué" },

    { espece:"Porcin", acte:"Anesthésie",                           niveau:"Non évalué" },
    { espece:"Porcin", acte:"Castration",                           niveau:"Non évalué" },
    { espece:"Porcin", acte:"Stérilisation",                        niveau:"Non évalué" }
  ]
};
