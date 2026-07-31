"""Full-year dataset: Sep 2025 – Aug 2026. Run: .venv\Scripts\python.exe backend\seed_full_year.py"""
import os, sys, uuid, random, string
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy import select, delete
from app.db import SessionLocal
from app import models
from app.security import DEMO_ORGANIZATION_ID

ORG_ID = DEMO_ORGANIZATION_ID
ADMIN = '00000000-0000-0000-0000-000000000010'
YEAR_START = datetime(2025, 9, 1, tzinfo=timezone.utc)
TODAY = datetime(2026, 8, 1, tzinfo=timezone.utc)

random.seed(20250801)

def uid(): return str(uuid.uuid4())
def pick(l): return random.choice(l)
def randdate(s, e):
    return s + timedelta(days=random.randint(0, (e - s).days))
def randdt(s, e):
    if s.tzinfo is None: s = s.replace(tzinfo=timezone.utc)
    if e.tzinfo is None: e = e.replace(tzinfo=timezone.utc)
    delta = int((e - s).total_seconds())
    return s + timedelta(seconds=random.randint(0, max(0, delta)))

# --- DATA POOLS ---
FIRST_NAMES = (
    "Juan Maria Pedro Ana Jose Carmen Luis Isabel Miguel Sofia Antonio Elena Francisco Lucia "
    "Carlos Martina Diego Valentina Gabriel Camila Andres Paula Rafael Diana Fernando Natalia "
    "Jorge Patricia Ricardo Daniela Alberto Monica Roberto Laura Hector Gabriela Sergio "
    "Alejandra Emilio Cristina Pablo Victoria Marcos Julia Raul Mariana Arturo Silvia "
    "Eduardo Renata Manuel Teresa Javier Claudia Francesca Rodrigo Beatriz Ignacio Cecilia "
    "Esteban Adriana Gonzalo Nadia Mauricio Paloma Felipe Rocio Hugo Estrella Simon Lorena "
    "Bruno Miranda Alonso Jimena Cesar Lourdes Damian Salome Elian Pilar James Mary Robert "
    "Patricia John Jennifer Michael Linda William Elizabeth David Barbara Richard Susan "
    "Joseph Jessica Thomas Sarah Charles Karen Christopher Nancy Daniel Lisa Matthew Betty "
    "George Sandra Kevin Ashley Edward Dorothy Jason Kim Helen Irene Oscar Quinn Ruth"
).split()

LAST_NAMES = (
    "Dela Cruz Santos Reyes Garcia Mendoza Torres Ramos Flores Aquino Bautista Castro "
    "Delos Reyes Escobar Fernandez Gonzalez Hernandez Ignacio Jimenez Lopez Martin Navarro "
    "Ortega Perez Quisumbing Rodriguez Santiago Tan Uson Villanueva Yap Zamora Alvarez "
    "Bernardo Cruz Dizon Esteban Fajardo Guevara Herrera Ilagan Javier King Lim Magno "
    "Nieto Ocampo Padilla Quinto Rivera Sison Aguilar Borja Canlas Dumlao Enriquez Fernando "
    "Gutierrez Hontiveros Ildefonso Jose Katigbak Lorenzo Manalo Natividad Ong Panganiban "
    "Quirante Roco Salazar Tiangco Umali Valdez Wenceslao Zabala Abad Barcelona Calderon "
    "Dela Rosa Espinosa Francisco Guzman Hernando Inocencio Jacinto Katipunan Laborte "
    "Macapagal Nolasco Obusan Pacis Quebral Recto Sabio Tablante Unabia Verdadero Yusingco "
    "Zapanta Bacani Cordero Dalisay Encomienda Fabian Gatchalian Hizon Icasiano Jalandoni "
    "Kalaw Legaspi Magtibay Norberto Opulencia Paderanga Quintos Ramirez Solis Talusan "
    "Umali Vergara Wagas Yabut Zafra Smith Johnson Williams Brown Jones Garcia Miller Davis "
    "Rodriguez Martinez Hernandez Lopez Gonzalez Wilson Anderson Thomas Taylor Moore Jackson "
    "Martin Lee Perez Thompson White Harris Sanchez Clark Ramirez Lewis Robinson Walker "
    "Young Allen King Wright Scott Torres Nguyen Hill Flores Green Adams Nelson Watson"
).split()

COMPANIES = [
    "Summit Digital Solutions","Pacific Cloud Services","Metro Data Partners","Bright Mind Academy",
    "Apex Logistics Inc","Horizon Tech Ventures","Stellar Software Labs","Crest Healthcare Systems",
    "Vista Media Group","Unity Creatives Co","North Star Analytics","EchoStream Networks",
    "Prime Build Constructors","Greenleaf Consulting","Quantum Retail Solutions","BlueWave Maritime",
    "Catalyst Education Inc","Nova Financial Advisors","Phoenix Security Group","Zenith Design Studio",
    "Pinnacle Energy Corp","Synergy Workforce Inc","Atlas Shipping Lines","Dynasty Hospitality Group",
    "Emerald AgriTech","Fusion Telecom Services","Meridian Real Estate","Titan Manufacturing Co",
    "Radiant Health Clinics","Stratos Aviation Ltd","Beacon Publishing House","Cobalt IT Solutions",
    "Aurora Events Management","Delta Freight Forwarders","Omicron Research Institute","Polaris Trading Co",
    "Solstice Travel and Tours","Vertex Auto Services","Wavelength Audio Studios","Yonder Outdoor Gear",
    "Zephyr Software Corp","Alchemy Digital Agency","Basilica Architects","Crimson Marketing Group",
    "Dune Interactive Media","Eclipse Solar Energy","Fable Book Publishers","Granite Construction Co",
    "Helix Biotech Inc","Iris Floral Designs","Jade Jewelry Exports","Kinetic Fitness Centers",
    "Lunar Coffee Roasters","Mosaic Art Collective","Nimbus Cloud Storage","Orbit Space Tech",
    "Platinum Wealth Mgmt","Quasar Electronics","Ridgeview Properties","Sapphire Marine Services",
    "Terra Organic Farms","Umbrella Insurance Grp","Velocity Motors Inc","Willow Environmental",
    "Xenon Lighting Corp","Yield Financial Svcs","Zen Gardens Landscaping","Alpha Logistics Corp",
    "Beta Software House","Gamma Pharma Inc","Delta Robotics Ltd","Epsilon Energy Co",
    "Zeta Fashion House","Eta Culinary School","Theta Music Academy","Iota Fitness Tech",
    "Kappa Security Inc","Lambda Cloud Hosting","Mu Data Analytics","Nu Mobile Apps",
    "Xi Web Development","Omicron AI Labs","Pi Blockchain Corp","Rho Fintech Inc",
    "Sigma Gaming Studio","Tau E-Commerce","Upsilon Media Inc","Phi Consulting Grp",
    "Chi Health Systems","Psi Edu Platform","Omega Real Estate","Astra Auto Dealers",
    "Nova Printing Press","Vortex Water Systems","Fusion Dance Studio","Harmony Music School",
    "Pinnacle Tutoring","Genesis Daycare","Horizon Language School","Legacy Heritage Tours",
    "Pacific Fisheries","Island Resort Group","Mountain View Realty","Coastal Shipping Lines",
    "Central Grain Traders","Metro Freight Corp","Global Trade Partners","Asia Pacific Imports",
    "Philippine Textile Mills","Luzon Agri Supply","Visayas Construction","Mindanao Logistics",
    "Cebu Business Process","Davao IT Park Inc","Baguio BPO Services","Iloilo Port Authority",
    "Bicol Express Transit","Palawan Eco Tourism","Boracay Hospitality Grp","Siargao Surf Resorts",
    "Mayon Volcano Tours","Rice Terrace Heritage","Tarsier Conservation","Chocolate Hills Tourism",
    "Coron Dive Center","El Nido Island Hopping","Puerto Princesa Eco Park","Subic Bay Freeport",
    "Clark Aviation Zone","Batanes Island Tours","Sagada Adventure Co","Banaue Heritage Lodge",
    "Vigan Heritage Hotel","Intramuros Cultural Tours","Fort Santiago Events","Manila Ocean Park",
    "Star City Amusement","Enchanted Kingdom Inc","Splash Island Resort","Tagaytay Ridge Hotels",
    "Taal Volcano Tours","Pagsanjan Falls Boat","Hundred Islands Cruise","Baler Surf Camps",
    "La Union Surf Shops","Zambales Beach Resorts","Pangasinan Hundred Isl","Batanes Air Transport",
    "Cagayan Valley Farms","Isabela Rice Mills","Quirino Eco Lodge","Nueva Vizcaya Mining",
    "Aurora Pacific Coast","Tarlac Sugar Mills","Pampanga Food Process","Zambales Nickel Mining",
    "Bataan Shipyard Corp","Bulacan Garment Fact","Rizal Quarry Inc","Laguna Lake Fisheries",
    "Cavite Industrial Park","Batangas Port Services","Quezon Coconut Oil","Marinduque Mining Co",
    "Occidental Mindoro Farms","Oriental Mindoro Ports","Romblon Marble Works","Palawan Nickel Corp",
    "Albay Pili Nut Inc","Camarines Sur Resorts","Camarines Norte Mining","Catanduanes Abaca Mills",
    "Sorsogon Poultry Farms","Masbate Cattle Ranch","Aklan Weaving Co","Antique Handicrafts",
    "Capiz Seafood Exports","Guimaras Mango Farms","Iloilo Sugar Centrals","Negros Occidental Sugar",
    "Negros Oriental Port","Siquijor Island Tourism","Cebu Mactan Export","Bohol Chocolate Farms",
    "Leyte Geothermal Energy","Samar Coconut Oil","Biliran Fishing Corp","Southern Leyte Pearl",
    "Dinagat Nickel Mining","Surigao Mineral Corp","Agusan Del Norte Palm","Agusan Del Sur Timber",
    "Bukidnon Pineapple Inc","Camiguin Island Resort","Misamis Oriental Port","Misamis Occidental Fishing",
    "Lanao Del Norte Hydro","Lanao Del South Farms","Cotabato Rice Mills","Sultan Kudarat Tuna",
    "South Cotabato Pine","Sarangani Tuna Port","Davao Del Norte Banana","Davao Del South Cocoa",
    "Davao Oriental Durian","Compostela Valley Mining","Davao City BPO Park","Zamboanga Del Norte Seaweed",
    "Zamboanga Del South Fruit","Zamboanga Sibugay Rubber","Basilan Fishing Corp","Sulu Pearl Farms",
    "Tawi-Tawi Seaweed Inc","Maguindanao Rice Co","Lanao Integrated Farms","Cotabato City Port",
    "Manila CBD Realty","Ortigas Center Towers","Makati Finance District","Bonifacio Global City",
    "Alabang South Park","Quezon City Tech Hub","Eastwood Cyber Park","Araneta City Complex",
    "SM Mall Holdings","Ayala Land Premier","Megaworld Properties","Vista Land Communities",
    "DMCI Homes Inc","Filinvest Land Inc","Rockwell Land Corp","Robinsons Land Corp",
    "Century Properties","SMDC Residences","Avida Land Corp","Amaia Land Inc",
    "Belle Corp Hotels","Travellers International","Resorts World Manila","City of Dreams Manila",
    "Solaire Resort Corp","Okada Manila Inc","Westside City Resorts","Universal Entertainment",
    "Philippine Airlines","Cebu Pacific Air","AirAsia Philippines","Philippine Air Force",
    "Manila International Airport","Mactan Cebu Airport","Clark International Airport","Davao Airport Corp",
    "Philippine Ports Authority","Cebu Port Authority","Davao Port Management","Subic Bay Metropolitan",
    "Manila Electric Company","Visayan Electric Company","Davao Light Power","Cotabato Light Power",
    "Meralco Industrial Engineering","National Grid Corp","First Gen Corp","Aboitiz Power Corp",
    "San Miguel Energy","Petron Corp","Shell Philippines","Caltex Philippines",
    "Phoenix Petroleum","Total Philippines","Seaoil Philippines","Pilipinas Shell",
    "Jollibee Foods Corp","Maxs Group Inc","Chowking Holdings","Greenwich Pizza Corp",
    "Mang Inasal Philippines","Red Ribbon Bakeshop","Goldilocks Bakeshop","Contis Bakeshop",
    "Goldilocks Food Products","Yellow Cab Pizza","Shakeys Pizza Asia","Pizza Hut Philippines",
    "Dominos Pizza PH","Kenny Rogers Roasters","Aristocrat Restaurant","Barrio Fiesta Group",
    "The Aristocrat Restaurant","Cabalen Restaurant","Mesa Filipino Moderne","Sentro 1771 Inc",
    "Manam Comfort Filipino","Locavore Kitchen","Sarsa Kitchen Bar","Kabisera Restaurant",
    "Cafe Juanita Group","Toyo Eatery Manila","Gallery by Chele","Tasting Room Manila",
    "Purple Yam Malate","Antonios Tagaytay","Vieux Chalet Tagaytay","Josephine Restaurant",
    "Balay Dako Tagaytay","Museo Orlina Glass","Pinto Art Museum","BenCab Museum Baguio",
    "Ayala Museum Makati","Metropolitan Museum","National Museum Corp","Lopez Museum Manila",
    "Museo Pambata Manila","Presidential Museum","Museo ng Katipunan","Museo ng Pulong Buhay",
    "Northwind Trading","Southsea Ventures","Eastern Pearl Corp","Western Star Ltd",
    "Highland Coffee Roasters","Metro Printing Solutions","Islandwide Logistics","Nationwide Express",
    "Provincial Hardware","Urban Garden Supply","Digital Frontier PH","Cyber Solutions Asia",
    "Smart Grid Energy","Renewable Power PH","Green Energy Partners","Solar Roof Systems",
    "Pacific Broadband","FiberNet Communications","DataStream Corp","CloudFirst PH",
    "DevOps Philippines","Agile Solutions Inc","Scrum Masters PH","Kanban Boards Asia",
    "Lean Startup Manila","Growth Hacker PH","Conversion Rate Experts","SEO Specialists Inc",
    "Content Marketing PH","Social Media Agency","Influencer Network Asia","Brand Ambassadors Corp",
    "Creative Studios Manila","Production House PH","Film Makers Inc","Video Editors Co",
    "Sound Engineers PH","Lighting Designers Asia","Stage Managers Inc","Event Planners PH",
    "Wedding Coordinators","Birthday Party Planners","Corporate Event Styling","Exhibition Designers",
    "Trade Show Booths","Conference Organizers","Seminar Hosts PH","Workshop Facilitators",
    "Training Providers Asia","Corporate Trainers Inc","Leadership Coaches PH","Executive Mentors",
    "Career Consultants","HR Solutions PH","Recruitment Agencies","Head Hunters Asia",
    "Talent Acquisition Corp","Staffing Solutions PH","Temp Agencies Manila","Outsourcing Partners",
    "BPO Centers Philippines","Call Center Operators","Customer Support PH","Help Desk Services",
    "Technical Support Asia","IT Helpdesk PH","Service Desk Corp","NOC Operations PH",
    "Data Center Services","Colocation Providers","Managed Hosting PH","Cloud Infrastructure",
    "Server Farms PH","Edge Computing Asia","CDN Providers PH","Load Balancers Inc",
    "DDoS Protection","Cyber Security PH","Penetration Testers","Ethical Hackers Inc",
    "Vulnerability Scanners","Compliance Auditors","ISO Certifiers PH","Quality Assurance Co",
    "Six Sigma Consultants","Lean Manufacturing PH","Process Improvement","Operational Excellence",
    "Supply Chain Asia","Logistics Optimizers","Warehouse Automation","Inventory Systems PH",
    "Fleet Management","Route Planners","Delivery Tracking","Last Mile Solutions",
    "E-commerce Fulfillment","Drop Shipping PH","Print on Demand","White Label Products",
    "Private Label Manufacturing","OEM Suppliers PH","Component Distributors","Electronics Parts",
    "Semiconductor Resellers","Chip Brokers PH","Circuit Designers","PCB Manufacturers",
    "Assembly Services","Contract Manufacturers","Turnkey Solutions PH","Project Managers Inc",
    "Construction Managers","Site Supervisors","Building Inspectors","Architectural Drafters",
    "Interior Decorators","Landscape Architects","Urban Planners PH","Civil Engineers Inc",
    "Structural Engineers","Mechanical Contractors","Electrical Engineers","Plumbing Contractors",
    "HVAC Specialists","Fire Safety Consultants","Security System Installers","CCTV Suppliers PH",
    "Access Control Systems","Biometric Scanners","Smart Lock Distributors","Home Automation",
    "IoT Device Makers","Sensor Manufacturers","Wearable Tech PH","Smart Watch Distributors",
    "Fitness Trackers Inc","Health Monitors PH","Medical Wearables","Remote Patient Monitoring",
    "Telehealth Providers","Virtual Clinics PH","Online Pharmacies","Digital Health Records",
    "EMR Systems PH","Hospital Management","Clinic Software","Dental Practice Systems",
    "Veterinary Clinics","Pet Care Services","Animal Hospitals","Grooming Salons PH",
    "Pet Boarding","Dog Walkers Manila","Pet Trainers Inc","Aquarium Specialists",
    "Fish Breeders PH","Ornamental Fish Exporters","Coral Farms","Reef Supply Co",
    "Diving Equipment","Scuba Gear PH","Snorkeling Tours","Island Hopping Boats",
    "Yacht Charters","Sailing Clubs","Marinas PH","Boat Builders Inc",
    "Ship Repair Services","Dry Dock Facilities","Naval Architects","Marine Engineers",
    "Offshore Contractors","Oil Rig Services","Petroleum Suppliers","Fuel Distributors",
    "Lubricant Manufacturers","Auto Parts PH","Tire Distributors","Battery Suppliers",
    "Car Dealerships","Truck Sales PH","Heavy Equipment Rental","Construction Machinery",
    "Crane Operators","Excavator Rentals","Bulldozer Services","Road Paving Contractors",
    "Asphalt Suppliers","Concrete Mixers","Ready Mix Plants","Cement Distributors",
    "Steel Suppliers PH","Iron Works","Aluminum Fabricators","Glass Manufacturers",
    "Plastic Molders","Rubber Manufacturers","Chemical Suppliers","Paint Manufacturers",
    "Coating Specialists","Adhesive Makers","Sealant Suppliers","Insulation Contractors",
    "Waterproofing Services","Roofing Contractors","Ceiling Suppliers","Flooring Installers",
    "Tile Distributors","Granite Suppliers","Marble Importers","Quartz Countertops",
    "Kitchen Designers","Cabinet Makers","Custom Furniture","Upholstery Services",
    "Curtain Makers","Blind Suppliers","Carpet Installers","Rug Importers",
    "Bedding Suppliers","Mattress Makers","Pillow Manufacturers","Linen Distributors",
    "Towel Suppliers","Bath Products PH","Soap Manufacturers","Cosmetic Makers",
    "Skincare Brands","Hair Care Products","Nail Salon Supplies","Spa Equipment",
    "Massage Chairs","Wellness Products","Aromatherapy Oils","Essential Oil Distillers",
    "Herbal Supplements","Vitamin Manufacturers","Protein Powder","Sports Nutrition",
    "Gym Equipment PH","Fitness Machines","Yoga Studios","Pilates Centers",
    "Dance Studios","Martial Arts Schools","Boxing Gyms","Swimming Coaches",
    "Tennis Clubs","Golf Courses","Basketball Courts","Volleyball Leagues",
    "Soccer Academies","Running Clubs","Cycling Groups","Triathlon Training",
    "Marathon Organizers","Race Directors","Sports Events PH","Tournament Hosts",
    "Esports Arenas","Gaming Lounges","VR Experience Centers","Arcade Operators",
    "Bowling Alleys","Billiard Halls","Karaoke Bars","Comedy Clubs",
    "Live Music Venues","Jazz Bars PH","Rock Clubs","Indie Music Spaces",
    "Recording Studios","Music Producers","Sound Engineers","Mastering Services",
    "Album Art Designers","Merchandise Printers","Band Managers","Booking Agents",
    "Concert Promoters","Festival Organizers","Stage Rentals","Lighting Rentals",
    "Sound System Rentals","Generator Rentals","Portable Toilet Suppliers","Tent Rentals",
    "Chair Rentals","Table Suppliers","Linen Rentals","Catering Equipment",
    "Food Truck Operators","Mobile Bars","Coffee Carts","Ice Cream Trucks",
    "Smoothie Stands","Juice Bars","Boba Tea Shops","Milk Tea Franchises",
    "Korean BBQ Restaurants","Japanese Ramen Shops","Chinese Dim Sum","Italian Pizzerias",
    "Mexican Taquerias","Indian Curry Houses","Thai Restaurants","Vietnamese Pho",
    "Mediterranean Grill","Middle Eastern Cuisine","African Restaurants","Caribbean Food",
    "Brazilian Steakhouses","Argentine Asado","Peruvian Ceviche","Colombian Arepas",
    "French Bakeries","German Breweries","Spanish Tapas","Greek Gyros",
    "Polish Pierogi","Russian Borscht","Turkish Kebab","Lebanese Shawarma",
    "Filipino Adobo Specialists","Sinigang Restaurants","Kare-Kare Houses","Lechon Roasters",
    "Bangus Fry Shops","Longganisa Makers","Tocino Manufacturers","Dried Fish Exporters",
    "Coconut Oil Mills","Banana Chip Factories","Mango Processing","Pineapple Canneries",
    "Coffee Plantations","Cacao Farms","Vanilla Growers","Spice Traders",
]

CITIES = [
    ("Makati City","Metro Manila","1200"),("Taguig City","Metro Manila","1630"),
    ("Quezon City","Metro Manila","1100"),("Mandaluyong","Metro Manila","1550"),
    ("Pasig City","Metro Manila","1600"),("San Juan","Metro Manila","1500"),
    ("Paranaque","Metro Manila","1700"),("Muntinlupa City","Metro Manila","1780"),
    ("Caloocan City","Metro Manila","1400"),("Manila","Metro Manila","1000"),
    ("Cebu City","Cebu","6000"),("Mandaue City","Cebu","6014"),("Lapu-Lapu City","Cebu","6015"),
    ("Davao City","Davao del Sur","8000"),("Cagayan de Oro","Misamis Oriental","9000"),
    ("Iloilo City","Iloilo","5000"),("Bacolod City","Negros Occidental","6100"),
    ("Baguio City","Benguet","2600"),("Zamboanga City","Zamboanga","7000"),
    ("Batangas City","Batangas","4200"),("Cainta","Rizal","1900"),
    ("Antipolo City","Rizal","1870"),("Marikina","Metro Manila","1800"),
    ("Pasay City","Metro Manila","1300"),("Valenzuela","Metro Manila","1440"),
    ("Malolos","Bulacan","3000"),("San Fernando","Pampanga","2000"),
    ("Angeles City","Pampanga","2009"),("Tarlac City","Tarlac","2300"),
    ("Dagupan","Pangasinan","2400"),("Vigan","Ilocos Sur","2700"),
    ("Laoag","Ilocos Norte","2900"),("Tuguegarao","Cagayan","3500"),
    ("Legazpi City","Albay","4500"),("Naga City","Camarines Sur","4400"),
    ("Sorsogon City","Sorsogon","4700"),("Calbayog","Samar","6710"),
    ("Tacloban","Leyte","6500"),("Ormoc","Leyte","6541"),
    ("Butuan","Agusan del Norte","8600"),("Surigao City","Surigao del Norte","8400"),
    ("General Santos","South Cotabato","9500"),("Koronadal","South Cotabato","9506"),
    ("Cotabato City","Maguindanao","9600"),("Iligan","Lanao del Norte","9200"),
    ("Ozamiz","Misamis Occidental","7200"),("Dipolog","Zamboanga del Norte","7100"),
    ("Pagadian","Zamboanga del Sur","7016"),("Puerto Princesa","Palawan","5300"),
    ("El Nido","Palawan","5313"),("Coron","Palawan","5316"),
    ("Roxas City","Capiz","5800"),("Kalibo","Aklan","5600"),
    ("San Jose","Antique","5700"),("Dumaguete","Negros Oriental","6200"),
    ("Tagbilaran","Bohol","6300"),("Tubigon","Bohol","6329"),
    ("Baler","Aurora","3200"),("San Fernando","La Union","2500"),
    ("Lingayen","Pangasinan","2401"),("Urdaneta","Pangasinan","2428"),
    ("Cabanatuan","Nueva Ecija","3100"),("Gapan","Nueva Ecija","3105"),
    ("San Jose","Nueva Ecija","3121"),("Santa Rosa","Laguna","4026"),
    ("Calamba","Laguna","4027"),("Biñan","Laguna","4024"),
    ("Cabuyao","Laguna","4025"),("Sta Cruz","Laguna","4009"),
    ("San Pablo","Laguna","4000"),("Lipa","Batangas","4217"),
    ("Tanauan","Batangas","4232"),("Sto Tomas","Batangas","4234"),
    ("Calapan","Oriental Mindoro","5200"),("Puerto Galera","Oriental Mindoro","5203"),
    ("Romblon","Romblon","5500"),("Odiongan","Romblon","5505"),
    ("Masbate City","Masbate","5400"),("Virac","Catanduanes","4800"),
    ("Daet","Camarines Norte","4600"),("Iriga","Camarines Sur","4431"),
    ("Sipalay","Negros Occidental","6113"),("San Carlos","Negros Occidental","6127"),
    ("Bayawan","Negros Oriental","6211"),("Bais","Negros Oriental","6206"),
    ("Canlaon","Negros Oriental","6223"),("Toledo","Cebu","6038"),
    ("Carcar","Cebu","6019"),("Naga","Cebu","6037"),
    ("Danao","Cebu","6004"),("Talisay","Cebu","6045"),
    ("Minglanilla","Cebu","6046"),("Consolacion","Cebu","6001"),
    ("Liloan","Cebu","6002"),("Compostela","Cebu","6003"),
    ("Bogo","Cebu","6010"),("Medellin","Cebu","6012"),
]

STREETS = ["Rizal","Mabini","Bonifacio","Aguinaldo","Quezon","Marcos","Roxas","Osmeña",
           "Luna","Del Pilar","Jacinto","Katipunan","Kalayaan","Mercury","Venus","Earth",
           "Mars","Jupiter","Saturn","Neptune","Pluto","Orion","Andromeda","Pegasus",
           "Main","Commerce","Industry","Trade","Market","Central","First","Second",
           "Third","Fourth","Fifth","Sunset","Sunrise","Highland","Valley","Ridge",
           "Coastal","Harbor","Bay","Lake","River","Forest","Garden","Park","Plaza"]

EMAIL_DOMAINS = ["gmail.com","yahoo.com","outlook.com","icloud.com","proton.me",
                 "company.ph","corp.net","business.io","enterprise.co","solutions.ph"]
EVT_POOL = ["created","activated","payment_activated","plan_change_scheduled",
            "auto_renew_updated","schedule_cancel","cancel_now","due_processed",
            "payment_failed","trial_ended","invoice_generated","subscription_renewed"]
PMETHODS = ["manual_cash","manual_bank","simulated_card","simulated_wallet"]
FAIL_REASONS = ["Insufficient funds","Card declined by issuer","Expired card",
                "Invalid CVV","Network timeout","Bank rejected transaction",
                "Daily limit exceeded","Account frozen"]
NOTIF_TEMPLATES = [
    ("trial_ending","Trial Ending Soon","Your trial ends in {days} days."),
    ("invoice_generated","New Invoice","Invoice {inv} for {amount} due {due}."),
    ("payment_received","Payment Received","Received {amount} for {inv}."),
    ("payment_failed","Payment Failed","Could not process {amount}. Update payment method."),
    ("subscription_activated","Subscription Active","{sub} is now active."),
    ("plan_changed","Plan Change","Change to {plan} effective {date}."),
    ("subscription_cancelled","Cancelled","{sub} has been cancelled."),
    ("overdue_reminder","Overdue","Invoice {inv} is overdue. Settle to avoid suspension."),
    ("welcome","Welcome","Welcome to Argo! Account ready."),
    ("renewal_reminder","Renewal Soon","{sub} renews on {date}. Ensure funds available."),
]

def main():
    print("=" * 60)
    print("Full-Year Sep 2025 – Aug 2026 — Bulk Insert")
    print("=" * 60)
    with SessionLocal() as session:
        print("Clearing existing mock data...")
        tables = [
            models.ActivityLog, models.Notification, models.SubscriptionEvent,
            models.PaymentAllocation, models.Payment, models.PaymentAttempt,
            models.InvoiceItem, models.Invoice, models.Subscription,
            models.Address, models.Customer, models.IdempotencyKey,
        ]
        for tbl in tables:
            session.execute(delete(tbl).where(tbl.organization_id == ORG_ID))
        session.commit()
        print("  Cleared.")

        plans = session.scalars(select(models.Plan).where(models.Plan.organization_id == ORG_ID)).all()
        prices = session.scalars(select(models.PlanPrice).where(models.PlanPrice.organization_id == ORG_ID)).all()
        if not plans or not prices:
            print("ERROR: No plans found. Seed the demo first.")
            return
        print(f"  Plans: {len(plans)} | Prices: {len(prices)}")

        # ---- 320 customers ----
        print("Generating 320 customers...")
        customers = []
        addresses = []
        used_emails = set()
        used_phones = set()
        used_codes = set()
        for i in range(320):
            is_company = random.random() < 0.42
            if is_company:
                display = pick(COMPANIES)
                company = display
                ctype = "organization"
            else:
                fn, ln = pick(FIRST_NAMES), pick(LAST_NAMES)
                display = f"{fn} {ln}"
                company = None
                ctype = "individual"
            base = display.lower().replace(" ","-").replace(".","").replace(",","")[:25]
            email = f"{base}@{pick(EMAIL_DOMAINS)}"
            while email in used_emails:
                email = f"{base}{random.randint(1,999)}@{pick(EMAIL_DOMAINS)}"
            used_emails.add(email)
            phone = f"09{random.randint(10,99):02d}{random.randint(1000000,9999999):07d}"
            while phone in used_phones:
                phone = f"09{random.randint(10,99):02d}{random.randint(1000000,9999999):07d}"
            used_phones.add(phone)
            code = f"CUS-{random.randint(100000,999999):06d}"
            while code in used_codes:
                code = f"CUS-{random.randint(100000,999999):06d}"
            used_codes.add(code)
            customers.append(models.Customer(
                id=uid(), organization_id=ORG_ID, customer_code=code,
                customer_type=ctype, display_name=display, company_name=company,
                email=email, phone=phone,
                tax_identifier=f"TIN-{random.randint(100000000,999999999):09d}" if is_company else None,
                status=random.choices(["active","active","active","active","archived"],[75,10,8,5,2])[0],
                notes=pick([None,None,None,"High-value client","Referral from partner","Requires monthly follow-up","Custom pricing negotiated","International billing address"]),
                created_by=ADMIN, updated_by=ADMIN,
                created_at=randdt(YEAR_START, TODAY - timedelta(days=7)),
            ))
            city, prov, post = pick(CITIES)
            addresses.append(models.Address(
                id=uid(), organization_id=ORG_ID, customer_id=customers[-1].id,
                address_type=random.choices(["billing","shipping","billing"],[60,30,10])[0],
                line1=f"{random.randint(1,999)} {pick(STREETS)} Ave.",
                line2=pick([f"Unit {random.randint(101,999)}",f"Floor {random.randint(1,25)}",f"Bldg {random.choice(string.ascii_uppercase)}{random.randint(1,9)}",None,None]),
                city_municipality=city, province=prov, postal_code=post,
                country_code="PH", is_primary=True,
                created_by=ADMIN, updated_by=ADMIN,
            ))
        session.bulk_save_objects(customers)
        session.bulk_save_objects(addresses)
        session.flush()
        print(f"  Customers: {len(customers)} | Addresses: {len(addresses)}")
        active_customers = [c for c in customers if c.status == "active"]

        # ---- 420 subscriptions ----
        print("Generating 420 subscriptions...")
        subscriptions = []
        used_sub_nums = set()
        for i in range(420):
            cust = pick(active_customers)
            price = pick(prices)
            plan = next(p for p in plans if p.id == price.plan_id)
            start = randdt(YEAR_START, TODAY - timedelta(days=1))
            age_days = (TODAY - start).days
            trial = plan.trial_days > 0 and age_days < plan.trial_days + 30
            if trial and age_days < plan.trial_days:
                status = "trialing"
            elif age_days < 7:
                status = random.choice(["pending_payment", "trialing"])
            elif age_days < 30:
                status = random.choices(["active","pending_payment","past_due"],[60,25,15])[0]
            elif age_days < 90:
                status = random.choices(["active","past_due","suspended","cancelled"],[55,20,10,15])[0]
            elif age_days < 180:
                status = random.choices(["active","past_due","suspended","cancelled","expired"],[45,18,12,20,5])[0]
            else:
                status = random.choices(["active","past_due","suspended","cancelled","expired"],[35,15,10,25,15])[0]
            days = 30 if price.billing_interval == "month" else 365
            tstart = start if status == "trialing" else None
            tend = start + timedelta(days=plan.trial_days) if status == "trialing" else None
            if status in ["active","pending_payment","past_due","suspended"]:
                cstart = start if not trial else (tend or start)
                periods = random.randint(0, min(4, age_days // days))
                cstart = cstart + timedelta(days=days * periods)
                cend = cstart + timedelta(days=days)
                nxt = cend
            elif status == "cancelled":
                cstart = start; cend = start + timedelta(days=days); nxt = None
            elif status == "expired":
                cstart = start; cend = start + timedelta(days=random.randint(28, min(age_days, 365))); nxt = None
            else:
                cstart = None; cend = None; nxt = None
            snum = f"SUB-{random.randint(100000,999999):06d}"
            while snum in used_sub_nums:
                snum = f"SUB-{random.randint(100000,999999):06d}"
            used_sub_nums.add(snum)
            subscriptions.append(models.Subscription(
                id=uid(), organization_id=ORG_ID, subscription_number=snum,
                customer_id=cust.id, plan_id=plan.id, plan_price_id=price.id,
                status=status, starts_at=start,
                trial_start_at=tstart, trial_end_at=tend,
                current_period_start=cstart, current_period_end=cend,
                next_billing_at=nxt,
                auto_renew=status not in ["cancelled","expired"] and random.random() < 0.78,
                cancel_at_period_end=(status == "cancelled" and random.random() < 0.65),
                cancelled_at=cend if status == "cancelled" else None,
                ended_at=cend if status in ["cancelled","expired"] else None,
                cancellation_reason=(pick(["Customer request","Competitor switch","Cost reduction","Business closure","Feature mismatch","No longer needed","Budget constraints"]) if status == "cancelled" else None),
                version=random.randint(1, 8),
                created_by=ADMIN, updated_by=ADMIN,
                created_at=start,
            ))
        session.bulk_save_objects(subscriptions)
        session.flush()
        print(f"  Subscriptions: {len(subscriptions)}")

        # ---- 550 invoices + items ----
        print("Generating 550 invoices...")
        invoices = []
        items = []
        used_inv_nums = set()
        for sub in subscriptions:
            if sub.status == "trialing" and not sub.current_period_start:
                continue
            price = next((p for p in prices if p.id == sub.plan_price_id), None)
            if not price: continue
            base_start = sub.current_period_start or sub.starts_at
            if not base_start: continue
            days = 30 if price.billing_interval == "month" else 365
            num_invs = random.randint(1, 4)
            for inv_idx in range(num_invs):
                issue = (base_start + timedelta(days=days * inv_idx)).date()
                if issue > date.today(): break
                due = issue + timedelta(days=7)
                inv_status = random.choices(["draft","open","paid","overdue","void"],[8,32,28,22,10])[0]
                inum = f"INV-{random.randint(100000,999999):06d}"
                while inum in used_inv_nums:
                    inum = f"INV-{random.randint(100000,999999):06d}"
                used_inv_nums.add(inum)
                invoices.append(models.Invoice(
                    id=uid(), organization_id=ORG_ID, invoice_number=inum,
                    customer_id=sub.customer_id, subscription_id=sub.id,
                    status=inv_status, issue_date=issue, due_date=due,
                    service_period_start=datetime.combine(issue, datetime.min.time(), tzinfo=timezone.utc),
                    service_period_end=datetime.combine(due, datetime.min.time(), tzinfo=timezone.utc),
                    currency=price.currency,
                    notes=pick(["Monthly renewal","Quarterly service","Annual subscription","Setup fee","Prorated upgrade",None]),
                    finalized_at=datetime.combine(issue, datetime.min.time(), tzinfo=timezone.utc) if inv_status != "draft" else None,
                    voided_at=datetime.combine(due, datetime.min.time(), tzinfo=timezone.utc) if inv_status == "void" else None,
                    void_reason=("Customer request" if inv_status == "void" else None),
                    created_by=ADMIN, updated_by=ADMIN,
                    created_at=datetime.combine(issue, datetime.min.time(), tzinfo=timezone.utc),
                ))
                items.append(models.InvoiceItem(
                    id=uid(), organization_id=ORG_ID, invoice_id=invoices[-1].id,
                    line_number=1, item_type="recurring",
                    description=f"Subscription renewal ({price.billing_interval})",
                    quantity=1, unit_amount_minor=price.unit_amount_minor + price.setup_fee_minor,
                    tax_rate_bps=0,
                    service_period_start=invoices[-1].service_period_start,
                    service_period_end=invoices[-1].service_period_end,
                    plan_id=sub.plan_id, plan_price_id=price.id,
                    created_by=ADMIN, updated_by=ADMIN,
                ))
                if random.random() < 0.3:
                    items.append(models.InvoiceItem(
                        id=uid(), organization_id=ORG_ID, invoice_id=invoices[-1].id,
                        line_number=2, item_type=random.choice(["setup","adjustment"]),
                        description=pick(["Setup fee","One-time discount","Proration adjustment","Migration service"]),
                        quantity=1, unit_amount_minor=random.choice([-5000, -2500, 5000, 10000]),
                        tax_rate_bps=0,
                        service_period_start=invoices[-1].service_period_start,
                        service_period_end=invoices[-1].service_period_end,
                        created_by=ADMIN, updated_by=ADMIN,
                    ))
        # standalone invoices
        for i in range(40):
            cust = pick(active_customers)
            issue = randdate(date(2025,9,1), date.today())
            due = issue + timedelta(days=7)
            inv_status = random.choices(["draft","open","paid","overdue","void"],[8,32,28,22,10])[0]
            inum = f"INV-{random.randint(100000,999999):06d}"
            while inum in used_inv_nums:
                inum = f"INV-{random.randint(100000,999999):06d}"
            used_inv_nums.add(inum)
            invoices.append(models.Invoice(
                id=uid(), organization_id=ORG_ID, invoice_number=inum,
                customer_id=cust.id, subscription_id=None,
                status=inv_status, issue_date=issue, due_date=due,
                service_period_start=datetime.combine(issue, datetime.min.time(), tzinfo=timezone.utc),
                service_period_end=datetime.combine(due, datetime.min.time(), tzinfo=timezone.utc),
                currency="PHP",
                notes=pick(["One-time consulting","Setup services","Custom integration","Training",None]),
                finalized_at=datetime.combine(issue, datetime.min.time(), tzinfo=timezone.utc) if inv_status != "draft" else None,
                voided_at=datetime.combine(due, datetime.min.time(), tzinfo=timezone.utc) if inv_status == "void" else None,
                void_reason=(pick(["Duplicate","Client request","Wrong amount"]) if inv_status == "void" else None),
                created_by=ADMIN, updated_by=ADMIN,
                created_at=datetime.combine(issue, datetime.min.time(), tzinfo=timezone.utc),
            ))
            for line in range(1, random.randint(2, 4)):
                items.append(models.InvoiceItem(
                    id=uid(), organization_id=ORG_ID, invoice_id=invoices[-1].id,
                    line_number=line, item_type=random.choice(["setup","adjustment","recurring"]),
                    description=pick(["Professional services","Consulting hours","Development","Training","Support package","Data migration"]),
                    quantity=random.randint(1,5),
                    unit_amount_minor=random.choice([5000,10000,15000,25000,50000]),
                    tax_rate_bps=0,
                    service_period_start=invoices[-1].service_period_start,
                    service_period_end=invoices[-1].service_period_end,
                    created_by=ADMIN, updated_by=ADMIN,
                ))
        session.bulk_save_objects(invoices)
        session.bulk_save_objects(items)
        session.flush()
        print(f"  Invoices: {len(invoices)} | Items: {len(items)}")

        # ---- 220 payments + allocations ----
        print("Generating 220 payments...")
        payments = []
        allocs = []
        open_paid_invs = [inv for inv in invoices if inv.status in ["open","paid","overdue"]]
        for i in range(220):
            cust = pick(active_customers)
            method = pick(PMETHODS)
            amount = random.choice([4900,9900,14900,19900,29900,39900,49900,59900,79900,99900,129900])
            status = random.choices(["completed","voided"],[92,8])[0]
            received = randdt(YEAR_START, TODAY)
            payments.append(models.Payment(
                id=uid(), organization_id=ORG_ID,
                payment_reference=f"PAY-{random.randint(100000,999999):06d}",
                customer_id=cust.id, payment_attempt_id=None,
                payment_method=method, status=status,
                amount_minor=amount, currency="PHP",
                received_at=received,
                external_reference=pick([f"REF-{random.randint(1000,9999)}", None]),
                notes=pick(["Cash at office","BPI transfer","BDO deposit","GCash","PayMaya",None]),
                voided_at=received if status == "voided" else None,
                void_reason=("Duplicate" if status == "voided" else None),
                created_by=ADMIN, updated_by=ADMIN,
                created_at=received,
            ))
        session.bulk_save_objects(payments)
        session.flush()
        for pay in payments:
            if pay.status != "completed": continue
            cust_invs = [inv for inv in open_paid_invs if inv.customer_id == pay.customer_id]
            if cust_invs and random.random() < 0.55:
                target = pick(cust_invs)
                alloc = min(pay.amount_minor, random.randint(pay.amount_minor // 3, pay.amount_minor))
                allocs.append(models.PaymentAllocation(
                    id=uid(), organization_id=ORG_ID,
                    payment_id=pay.id, invoice_id=target.id,
                    amount_minor=alloc, allocated_at=pay.received_at,
                    created_by=ADMIN, updated_by=ADMIN,
                ))
        session.bulk_save_objects(allocs)
        session.flush()
        print(f"  Payments: {len(payments)} | Allocations: {len(allocs)}")

        # ---- 100 payment attempts ----
        print("Generating 100 payment attempts...")
        attempts = []
        open_invs = [inv for inv in invoices if inv.status == "open"]
        for i in range(100):
            if not open_invs: break
            inv = pick(open_invs)
            status = random.choices(["pending","succeeded","failed"],[20,45,35])[0]
            attempted = randdt(YEAR_START, TODAY)
            amount = random.choice([4900,9900,19900,29900,49900,59900])
            attempts.append(models.PaymentAttempt(
                id=uid(), organization_id=ORG_ID,
                attempt_reference=f"ATT-{random.randint(100000,999999):06d}",
                invoice_id=inv.id, provider="simulated",
                provider_attempt_id=f"sim_{uid()[:8]}" if status != "pending" else None,
                idempotency_key=f"idem_{uid()}",
                request_hash="bulk-hash",
                status=status, amount_minor=amount, currency=inv.currency,
                attempted_at=attempted,
                completed_at=attempted if status != "pending" else None,
                failure_message=(pick(FAIL_REASONS) if status == "failed" else None),
                created_by=ADMIN, updated_by=ADMIN,
            ))
        session.bulk_save_objects(attempts)
        session.flush()
        print(f"  Payment Attempts: {len(attempts)}")

        # ---- 180 subscription events ----
        print("Generating 180 subscription events...")
        events = []
        for i in range(180):
            sub = pick(subscriptions)
            etype = pick(EVT_POOL)
            effective = randdt(sub.starts_at if sub.starts_at.tzinfo else sub.starts_at.replace(tzinfo=timezone.utc), TODAY)
            from_status = sub.status
            to_status = sub.status
            if etype == "created":
                from_status = None
                to_status = "trialing" if sub.trial_start_at else "pending_payment"
            elif etype in ["activated","payment_activated"]:
                from_status = pick(["pending_payment","past_due","suspended"])
                to_status = "active"
            elif etype == "cancel_now":
                to_status = "cancelled"
            elif etype == "trial_ended":
                from_status = "trialing"; to_status = "pending_payment"
            elif etype == "payment_failed":
                from_status = "active"; to_status = "past_due"
            events.append(models.SubscriptionEvent(
                id=uid(), organization_id=ORG_ID, subscription_id=sub.id,
                event_type=etype, from_status=from_status, to_status=to_status,
                effective_at=effective, actor_type="user",
                reason=pick(["System processed","User action","Payment received","Scheduled event","Auto-renewal","Manual override"]),
                correlation_id=uid(),
                metadata_json={"source": "seed_full_year"},
                created_by=ADMIN, updated_by=ADMIN,
                created_at=effective,
            ))
        session.bulk_save_objects(events)
        session.flush()
        print(f"  Subscription Events: {len(events)}")

        # ---- 120 notifications ----
        print("Generating 120 notifications...")
        notifications = []
        for i in range(120):
            ntype, title, body_tmpl = pick(NOTIF_TEMPLATES)
            cust = pick(customers)
            sub = pick(subscriptions) if random.random() < 0.5 else None
            inv = pick(invoices) if random.random() < 0.5 else None
            sent = randdt(YEAR_START, TODAY)
            body = body_tmpl.format(
                days=random.randint(1,5),
                inv=inv.invoice_number if inv else "INV-000000",
                amount=f"PHP {random.choice([99,299,599,799,1299]):,}.00",
                due=(sent + timedelta(days=7)).date().isoformat(),
                sub=sub.subscription_number if sub else "SUB-000000",
                plan=pick(["Starter","Growth","Pro","Enterprise","Elite"]),
                date=sent.date().isoformat(),
            )
            notifications.append(models.Notification(
                id=uid(), organization_id=ORG_ID,
                customer_id=cust.id, recipient_user_id=ADMIN,
                channel="in_app", notification_type=ntype,
                title=title, body=body,
                status=random.choices(["sent","read"],[75,25])[0],
                related_entity_type=pick(["subscription","invoice","payment","customer"]),
                related_entity_id=(sub.id if sub else inv.id if inv else cust.id),
                sent_at=sent,
                read_at=(sent + timedelta(hours=random.randint(1,72))) if random.random() < 0.25 else None,
                created_by=ADMIN, updated_by=ADMIN,
                created_at=sent,
            ))
        session.bulk_save_objects(notifications)
        session.flush()
        print(f"  Notifications: {len(notifications)}")

        # ---- 180 activity logs ----
        print("Generating 180 activity logs...")
        logs = []
        ACTIONS = ["created","updated","viewed","deleted","finalized","voided","recorded","status_changed","allocated","exported"]
        pools = [
            ("customer", customers),
            ("plan", plans),
            ("subscription", subscriptions),
            ("invoice", invoices),
            ("payment", payments),
        ]
        for i in range(180):
            etype, pool = pick(pools)
            entity = pick(pool)
            ts = randdt(YEAR_START, TODAY)
            logs.append(models.ActivityLog(
                id=uid(), organization_id=ORG_ID,
                entity_type=etype, entity_id=entity.id,
                action=pick(ACTIONS), actor_user_id=ADMIN,
                request_id=uid(),
                details_json={"source": "seed_full_year", "batch": True},
                created_by=ADMIN, updated_by=ADMIN,
                created_at=ts,
            ))
        session.bulk_save_objects(logs)
        session.flush()
        print(f"  Activity Logs: {len(logs)}")

        session.commit()
    print("-" * 60)
    print("Full-year data inserted successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
