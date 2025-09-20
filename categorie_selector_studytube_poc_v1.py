import re
from collections import defaultdict

# --- 1) De StudyTube-taxonomie zoals jij 'm gaf, per hoofdcategorie ---
CATEGORY_BLOCKS = {
    "Arbo & Veiligheid": """Arbo & Veiligheid, AED & Reanimatie, ATEX, Arbo, Arbowetgeving, Asbest, BHV, BOA - Buitengewoon Opsporings Ambtenaar,
Beveiliging, Brandveiligheid, Crisis coördinator, DLP, EHBO, Facilitair, Flensmonteur, Gassen, HVK, Hijsen,
Keuren ladders, trappen en rolsteigers, Keurmeester, Machineveiligheid, Milieu, Preventiemedewerker, Risico-inventarisatie,
Schoonmaak, Sociale Hygiëne, VCA, VVL, Veilig werken, Veiligheid, Verkeer, Werkplekonderzoek""",

    "Automatisering & ICT/IT": """Automatisering & ICT/IT, .NET, Advanced Installer, Android, Apache, App-V, Apple, Applicatie Management,
Application Services Library (ASL), Archimate, Automatisering & ICT/IT, Babok, Bedrijfskunde ICT,
Beveiliging & Security, BiSL Foundation, BlockChain, Business Objects, Business analyse, Business intelligence,
Businessarchitectuur, C / C++, Certified Ethical Hacker (CEH), Certified Information Security Manager (CISM),
Certified Information Systems Auditor (CISA), Certified Information Systems Security Professional (CISSP),
Cisco, Citrix, Cloud Computing, Cobit 5, CommVault, CompTIA, Computervaardigheden, Data Protection, Data Visualisatie,
Data analyse, Database management, Datacenter, Datawarehouse, DevOps, Document management, Draadloos / Wireless, ERP,
ETL (Extract Transform Load), Endeavour, Enterprise Architectuur, FileMaker, Framemaker, Functiepuntanalyse, Functioneel beheer,
Git, HP (Hewlett-Packard), Hyper-V, IBM Cognos, IBM Lotus Notes, IBM Tivoli, ICT Algemeen, ICT Strategie, IOS, ISTQB,
Informatica, Informatieanalyse, Informatiebeveiliging, Informatiemanagement, Java, Junos, Linux,
M20413 Designing and Implementing a Server Infrastructure, M20414 Implementing an Advanced Server Infrastructure,
MCSA, MCSE, Mac OS X, Microsoft, Microsoft Access, Microsoft Active Directory, Microsoft Azure, Microsoft BizTalk Server,
Microsoft CRM/ Dynamics, Microsoft Excel, Microsoft Exchange Server, Microsoft ISA, IIS & SMS, Microsoft LINQ, Microsoft Lync,
Microsoft Lync Server, Microsoft Office, Microsoft Office 365, Microsoft OneNote, Microsoft Outlook, Microsoft Power BI,
Microsoft PowerPoint, Microsoft Project, Microsoft Publisher, Microsoft SQL Server, Microsoft Sharepoint, Microsoft Silverlight,
Microsoft System Center, Microsoft System Center - Cloud, Microsoft Visio, Microsoft Visual Basic 6/.NET, Microsoft Visual C#.NET,
Microsoft Visual Studio, Microsoft Windows 10, Microsoft Windows 7, Microsoft Windows 8, Microsoft Windows Communication Foundation,
Microsoft Windows PowerShell, Microsoft Word, Microsoft netwerk, Mobile development & Apps, MySQL, NetApp, Netwerken (IT),
Netwerkmanagement, ONTAP, OO (Object Oriented) Programmeren, OO (Object Oriented) Programmeren, OpenOffice.org, Oracle, PHP,
Primavera, Programmeren, Python, RES, Rational Unified Process (RUP), Requirement Engineering, SAP, SAP Crystal Reports, SPSS, SQL Server,
Salesforce, Secure Programming, Selenium, Service Management, Service Oriented Architecture (SOA), Software Development, Software testing,
Softwarearchitectuur, Spring, Systeembeheer, System Center Configuration Manager (SCCM), TCP/IP, TMap, TOGAF, Technisch Beheer, UML, Unix,
VBA (Microsoft Office), VMware, Virtualisatie, VoIP, Watchguard Fireware, Windows Server, Word, iEXA""",

    "Communicatie": """Communicatie, Adviesvaardigheden, Argumenteren, Beïnvloeden, Commercieel schrijven, Communicatietechnieken, Communiceren, Copywriting,
Creatief schrijven, Effectief Communiceren, Feedback geven & ontvangen, Gesprekstechnieken, Gespreksvaardigheden, Interculturele communicatie,
Interne communicatie, Klachtenbehandeling, Lichaamstaal, Luisteren, Marketingcommunicatie, Mediatraining, Mondelinge communicatie, Nederlandse taal,
Omgaan met emotie, Omgaan met weerstand, Online communicatie, Overtuigen, PR, Pitchen, Presenteren, Rapporten schrijven, Samenwerken,
Schriftelijke communicatie, Storytelling, Strategische communicatie, Telefoneren, Vergaderen, Zakelijk schrijven""",

    "Financieel": """Financieel, Accountant, Assistent Accountant, Bedrijfseconomie, Belasting, Bestuurlijke Informatievoorziening (BIV), Bewindvoerder, Blockchain,
Boekhouden, Budgetcoach, Controlling, Debiteurenbeheer, Finance, Financiële dienstverlening, Financiële verslaglegging, Fraude / Fraudemanagement,
Fusies & overnames, Hypotheekadviseur, IFRS, Incasso, Jaarrekening en balans, Management accounting, Pensioen, Permanente educatie, Verzekeringen,
WFT, WMO Consulent""",

    "Hobby & Vrije Tijd": """Hobby & Vrije Tijd""",

    "HR": """HR, Arbeidsmarktcommunicatie, Assessment, Burn-out preventie, Casemanagement, Competentiemanagement, Duurzame inzetbaarheid, E-HRM, Functionerings - & beoordelingsgesprekken,
HR-advies, HR-beleid, HRM, Het nieuwe werken, Intercedent, Interviewtechnieken, Loopbaancoaching & advies, Medezeggenschap, OR, P&O / P&A, Personeelsmanagement,
Personeelsplanning, Personeelszaken, Recruitment, Reorganisatie, Reïntegratie, Slecht nieuws gesprekken, Sollicitatiegesprek, Solliciteren, Talentmanagement,
Vertrouwenspersoon, Verzuim, Werkgeluk, Werving & selectie, Wet Werk en Zekerheid (WWZ)""",

    "Inkoop & Logistiek": """Inkoop & Logistiek, ADR Certificaat, APICS/CSCP, Beroepschauffeur, Code 95, Digitale tachograaf, Distributie, Douane, ERP management, Expeditie, Fleetmanagement,
Gevaarlijke stoffen, Heftruck, Hoogwerker, Inkoopmanagement, Lading zekeren, Logistiek, KIT, Planning, Magazijn, Reachtruck, Rijbewijs, Stapelaar, Supply chain,
Transport, Verreiker, Voorraadbeheer""",

    "Internet & Media": """Internet & Media, 3D vormgeving, ASP.NET, Adobe, Angular, Content management, DTP, Digitale fotografie, Dreamweaver, Drukwerk, E-commerce, E-mail marketing,
Google AdWords, Google Analytics, Grafische vormgeving, HTML & CSS, Infographics, Hubspot, Interaction design, Internet of Things, Internet, Intranet, JavaScript,
Journalistiek, Magento, PHP, Redactie, Ruby, SEA, SEO, SQL, Social Media, Sociale netwerken, Tablets & iPads, UX / User Experience Design, Video / Camera,
Videobewerking, Vloggen, Vormgeving, Web 2.0, Web schrijven, Webdesign, Website, XML, Worpress""",

    "Juridisch": """Juridisch, Aanbestedingsrecht, Aansprakelijkheidsrecht, Actualiteiten, Algemeen civiel recht, Ambtenarenrecht, Arbeidsongeschiktheid, Arbeidsrecht, Bestuursprocesrecht,
Bouwrecht, Burgerzaken, Compliance, Contractmanagement, Europees Recht, Financieel Recht (Bank- en effectenrecht), Fiscaal recht / Belastingrecht, Gezondheidsrecht,
Huurrecht, ICT- Informatie- en Internetrecht, Insolventierecht, Intellectueel eigendom & Auteursrecht, Jeugdrecht, Juridisch secretaresse, Mediation & Arbitrage,
Milieurecht & Omgevingsrecht, Nederlands recht, Notariaat, Ondernemingsrecht, Ontslagrecht, Participatiewet, Personen- en familierecht, Privacy & Avg, Procesrecht,
Ruimtelijke ordeningsrecht, Sociale zekerheidsrecht, Staats- en bestuursrecht, Strafprocesrecht & Strafvordering, Strafrecht, Subsidie, Tuchtrecht,
Verbintenissenrecht / Contractrecht, Vreemdelingenrecht, Werkgeversaansprakelijkheid, Wet op de ondernemingsraden (WOR), Wet schuldsanering natuurlijke personen (WSNP), Verzekeringsrecht""",

    "Kwaliteit & Projectmanagement": """Kwaliteit & Projectmanagement, Agile, Allergenen, Business Case Management, Business Process Management (BPM), Design thinking, Crisismanagement, HACCP,
IPMA, IREB, ISO, ITIL, Auditing, Kwaliteitsmanagement, Lean, Lean Six Sigma, PRINCE2, Performance Management, Planning, Procesmanagement, Programmamanagement,
Projectleider, Project assistent, Projectmanagement, Projectmatig werken, Projectmedewerker, Riskmanagement, Scrum, Statistiek, Voedselveiligheid""",

    "Management": """Management, Big Data, Branding, Bedrijfskunde, Besluitvorming, Bestuurskunde, Content Marketing, Business development, Coachend leidinggeven, Coaching, DISC, Eventmanagement,
Finance voor niet-financiële manager, Governance, Innovatiemanagement, Hospitality, International business, Kennismanagement, Leiderschap, Leidinggeven, MBA, Management,
Managementvaardigheden, Middle management, MVO, Motiveren, Lerende organisatie, Non-profit Management, Ondernemen, Operationeel management, Organisatiekunde, Organisatieontwikkeling,
Outsourcing, Product management, Situationeel leiderschap, Stakeholdermanagement, Strategisch management, Teambuilding, Teamleider, Trendwatching management, Verandermanagement, Visie ontwikkeling""",

    "Marketing": """Marketing, CRM, Campagnemanagement, Conceptontwikkeling, Marketing Intelligence, Marketing advies, Marketing management, Marketingstrategie, Marktonderzoek, Merkontwikkeling, NIMA-A, NIMA-B,
Online marketing, Personal branding, Reclame, Retailmarketing, Social Media Marketing, Trendwatching marketing, Zoekmachine""",

    "Opleiding & Onderwijs": """Opleiding & Onderwijs, Begeleidingskunde, Brainstormen, Coach / Coaching, Didactische vaardigheden, Economie, Ethiek, Facilitator / Faciliteren, Groepsdynamiek, Interne begeleider,
Intervisie, Leeractiviteiten, Lerarenopleidingen / Docentenopleidingen, Onderwijsassistent, Onderzoeksvaardigheden, Opleidingstrajecten, Pedagogiek, Rekenen, Schoolleider, Teamcoaching,
Train de trainer, Trainersvaardigheden, Trainingsacteur, Workshops""",

    "Persoonlijke Effectiviteit": """Persoonlijke Effectiviteit, Assertiviteit, Beinvloeden, Breintraining, Communicatieve vaardigheden, Concentratietraining, Conflicthantering, Creatief denken, Delegeren, EMDR,
Emotionele intelligentie, GTD, Geheugentraining, Inspiratie, Integriteit, Intuïtie, Inzicht, MBTI, Mindfulness, Mindmapping, NLP, Organiseren, Persoonlijke ontwikkeling,
Persoonlijk leiderschap, Plannen & organiseren, Persoonlijke groei, Probleemanalyse, Resultaatgericht werken, Snellezen, Stress, Time Management, Werkdruk, Zelfsturing, Zelfvertrouwen, Zingeving""",

    "Productie, Techniek & Bouw": """Productie, Techniek & Bouw, Architectuur, Algemene techniek, AutoCAD, Autodesk, DLP, Autotechniek, Bouw, CAD / CAM, Coax, Elektrische installaties, Elektrotechniek,
GIS (Geografisch Informatiesysteem), Gebouwautomatisering, Groenvoorziening, Installatietechniek, Interieurstylist, Laboratoriumtechniek, Lassen, Loodgieter,
Meettechniek, Metaal & Metaalbewerking, NEN, Onderhoudstechniek, Operator A, Operator B, PLC-techniek, Pneumatiek, Procestechniek, Projectuitvoer, REVIT, Werkvoorbereiding""",

    "Sales": """Sales, Accountmanagement, Acquisitie, Commercieel medewerker, Commerciële vaardigheden, Customer Service, Klantgerichtheid, Klantvriendelijkheid, NIMA SMA Sales-A, NIMA SMA Sales-B, Netwerken, New Business,
Onderhandelen, Relatiemanagement, Resultaatgerichtheid, Sales management, Telefonische verkoop, Verkoop binnendienst, Verkoop buitendienst, Klantgerichte Sales, Verkoopvaardigheden, Winkelpersoneel, Verkoopgesprek""",

    "Secretarieel & Administratief": """Secretarieel & Administratief, Administratief Medewerker, BKB, BKC, BKL, Bedrijfsadministratie, Boekhouden, Loonheffing & Loonadministratie, Management assistent, Management support,
Notuleren, Office management, PDB, Receptioniste, Salarisadministratie, Secretaresse, Typen, Gemeente medewerker, Telefoniste, Baliemedewerker""",

    "Sport & Vitaliteit": """Sport & Vitaliteit, Afslanken, Fitness, Fysiotherapie, Gewichtsconsulent / Dietist, Gezondheid, Massage, Sport en Beweging, Stoppen met roken, Vaarbewijs, Vitaliteit, Voedingsdeskundige, Yoga""",

    "Taalcursus": """Taalcursus, Afrikaans, Albanees, Arabisch, Braziliaans, Bulgaars, Cambodjaans, Cambridge Engels, Chinees, Deens, Duits, Egyptisch, Engels, Frans, Grieks, Hebreeuws, Hindi, Hongaars,
Indonesisch, Italiaans, Japans, Koreaans, Kroatisch, Latijn, Litouws, Maleis, Marokkaans, Nederlands, Noors, Papiamento, Perzisch, Pools, Portugees, Roemeens, Russisch, Saudi,
Servisch, Sloveens, Slowaaks, Spaans, Thais, Tsjechisch, Turks, Vietnamees, Zakelijk Duits, Zakelijk Engels, Zakelijk Frans, Zweeds""",

    "Vastgoed & Makelaardij": """Vastgoed & Makelaardij, Assetmanagement, Bouwkunde, Juridische Aspecten, Makelaar, Ruimtelijke Ordening, Vastgoedmanagement, Bedrijfsmatig vastgoed, Taxateur""",

    "Zorg & Verzorging": """Zorg & Verzorging, Apothekersassistent, Dementie, Dierenartsassistent, Doktersassistente, Drogist, Gedrag, Gezondheidsbevordering, Gezondheidszorg, GGZ, Jeugdzorg, Kappers, Kinderopvang,
Kraamzorg, Maatschappelijk werker, Medicatie toedienen, Medisch secretaresse, Medische Terminologie, Ouderenzorg, Pedicure, Psychiatrie, Psychologie, Relatietherapie, Rouwverwerking,
Schoonheidsspecialist, Sociaal Pedagogische Hulpverlening (SPH), Sociaal psychiatrische verpleegkunde (SPV), Tandartsassistente, Uitvaartverzorger, Verpleegkundige, Verzorgende,
WMO, Zorg en Welzijn, Zorgmanagement, Activiteitenbegeleider, Schuldhulpverlening, Sociaal domein""",

    "Overig": """Overig""",

    # Deze categorieën stonden wel in de hoofdlijst, maar zonder subcategorie-overzicht:
    "NL Leert Door": "",
    "Kinderopvang": "",
    "Persoonlijke Ontwikkeling": "",
    "Persoen in zicht (PIZ)": "",
    "Ondernemingsraad": "",
}

CATEGORY_PRIORITY = [
    # optioneel: bepaalt tie-breakers (bovenaan = voorkeur)
    "Automatisering & ICT/IT", "Internet & Media", "Management", "Kwaliteit & Projectmanagement",
    "HR", "Financieel", "Marketing", "Communicatie", "Inkoop & Logistiek", "Opleiding & Onderwijs",
    "Productie, Techniek & Bouw", "Sales", "Secretarieel & Administratief", "Sport & Vitaliteit",
    "Taalcursus", "Vastgoed & Makelaardij", "Zorg & Verzorging", "Hobby & Vrije Tijd",
    "NL Leert Door", "Kinderopvang", "Persoonlijke Ontwikkeling", "Persoen in zicht (PIZ)", "Ondernemingsraad",
    "Overig"
]

_WORD_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+#")

def _contains_term(block: str, term: str) -> bool:
    """Case-insensitive substring met 'woordgrenzen' (geen letters/cijfers direct ernaast)."""
    if not block or not term:
        return False
    b = block.lower()
    t = term.lower().strip()
    i = b.find(t)
    while i != -1:
        before = b[i-1] if i > 0 else ""
        after  = b[i+len(t)] if i + len(t) < len(b) else ""
        if (before == "" or before not in _WORD_CHARS) and (after == "" or after not in _WORD_CHARS):
            return True
        i = b.find(t, i+1)
    return False

def choose_category_from_subcats(subcats):
    """Bepaal beste StudyTube-hoofdcategorie op basis van een lijst subcategorieën."""
    # 1) Exacte match op categorienaam wint
    sub_norm = [s.strip() for s in subcats if s and s.strip()]
    cat_names_lower = {c.lower(): c for c in CATEGORY_BLOCKS.keys()}
    for s in sub_norm:
        key = s.lower()
        if key in cat_names_lower:
            return cat_names_lower[key]

    # 2) Score per categorie o.b.v. aantal hits
    scores = defaultdict(int)
    for s in sub_norm:
        for cat, block in CATEGORY_BLOCKS.items():
            if _contains_term(block, s):
                scores[cat] += 1

    if scores:
        # beste score, bij gelijk: volgorde volgens CATEGORY_PRIORITY
        best = max(
            scores.items(),
            key=lambda kv: (kv[1], -(CATEGORY_PRIORITY.index(kv[0]) if kv[0] in CATEGORY_PRIORITY else 10_000))
        )
        return best[0]

    # 3) Geen match: Overig
    return "Overig"


