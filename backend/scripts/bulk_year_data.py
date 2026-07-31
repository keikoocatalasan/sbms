"""Fast bulk insert of ~300 additional records to reach 500+ total, spanning a full year.

Run from project root:
    .venv\Scripts\python.exe backend\bulk_year_data.py
"""

import os, sys, uuid, random
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from sqlalchemy import select, func
from app.db import SessionLocal, engine
from app import models
from app.security import DEMO_ORGANIZATION_ID

ORG_ID = DEMO_ORGANIZATION_ID
ADMIN = "00000000-0000-0000-0000-000000000010"
YEAR_START = date(2024, 1, 1)
YEAR_END = date(2024, 12, 31)

random.seed(2024)

def uid(): return str(uuid.uuid4())
def utcnow(): return datetime.now(timezone.utc)
def pick(l): return random.choice(l)
def randdate(s: date, e: date) -> date:
    return s + timedelta(days=random.randint(0, (e - s).days))
def randdt(s: datetime, e: datetime) -> datetime:
    # Ensure both have timezone info
    if s.tzinfo is None:
        s = s.replace(tzinfo=timezone.utc)
    if e.tzinfo is None:
        e = e.replace(tzinfo=timezone.utc)
    return s + timedelta(seconds=random.randint(0, int((e - s).total_seconds())))

FIRSTS = ["Juan","Maria","Pedro","Ana","Jose","Carmen","Luis","Isabel","Miguel","Sofia","Antonio","Elena","Francisco","Lucia","Carlos","Martina","Diego","Valentina","Gabriel","Camila","Andres","Paula","Rafael","Diana","Fernando","Natalia","Jorge","Patricia","Ricardo","Daniela","Alberto","Monica","Roberto","Laura","Hector","Gabriela","Sergio","Alejandra","Emilio","Cristina","Pablo","Victoria","Marcos","Julia","Raul","Mariana","Arturo","Silvia","Eduardo","Renata","Manuel","Teresa","Javier","Claudia","Francesca","Rodrigo","Beatriz","Ignacio","Cecilia","Esteban","Adriana","Gonzalo","Nadia","Mauricio","Paloma","Felipe","Rocio","Hugo","Estrella","Simon","Lorena","Bruno","Miranda","Alonso","Jimena","Cesar","Lourdes","Damian","Salome","Elian","Pilar"]
LASTS = ["Dela Cruz","Santos","Reyes","Garcia","Mendoza","Torres","Ramos","Flores","Aquino","Bautista","Castro","Delos Reyes","Escobar","Fernandez","Gonzalez","Hernandez","Ignacio","Jimenez","Lopez","Martin","Navarro","Ortega","Perez","Quisumbing","Rodriguez","Santiago","Tan","Uson","Villanueva","Yap","Zamora","Alvarez","Bernardo","Cruz","Dizon","Esteban","Fajardo","Guevara","Herrera","Ilagan","Javier","King","Lim","Magno","Nieto","Ocampo","Padilla","Quinto","Rivera","Sison","Aguilar","Borja","Canlas","Dumlao","Enriquez","Fernando","Gutierrez","Hontiveros","Ildefonso","Jose","Katigbak","Lorenzo","Manalo","Natividad","Ong","Panganiban","Quirante","Roco","Salazar","Tiangco","Umali","Valdez","Wenceslao","Zabala","Abad","Barcelona","Calderon","Dela Rosa","Espinosa","Francisco","Guzman","Hernando","Inocencio","Jacinto","Katipunan"]
COMPANIES = ["Summit Digital","Pacific Cloud","Metro Data","Bright Mind","Apex Logistics","Horizon Tech","Stellar Software","Crest Healthcare","Vista Media","Unity Creatives","North Star","EchoStream","Prime Build","Greenleaf","Quantum Retail","BlueWave Maritime","Catalyst Edu","Nova Financial","Phoenix Sec","Zenith Design","Pinnacle Energy","Synergy Workforce","Atlas Shipping","Dynasty Hospitality","Emerald Agri","Fusion Telecom","Meridian RE","Titan Mfg","Radiant Health","Stratos Aviation","Beacon Pub","Cobalt IT","Aurora Events","Delta Freight","Omicron Research","Polaris Trading","Solstice Travel","Vertex Auto","Wavelength Audio","Yonder Gear"]
CITIES = [("Makati","Metro Manila","1200"),("Taguig","Metro Manila","1630"),("Quezon City","Metro Manila","1100"),("Mandaluyong","Metro Manila","1550"),("Pasig","Metro Manila","1600"),("San Juan","Metro Manila","1500"),("Paranaque","Metro Manila","1700"),("Muntinlupa","Metro Manila","1780"),("Caloocan","Metro Manila","1400"),("Manila","Metro Manila","1000"),("Cebu City","Cebu","6000"),("Mandaue","Cebu","6014"),("Lapu-Lapu","Cebu","6015"),("Davao City","Davao","8000"),("Cagayan de Oro","MisOr","9000"),("Iloilo City","Iloilo","5000"),("Bacolod","NegOcc","6100"),("Baguio","Benguet","2600")]
EVT_TYPES = ["created","activated","payment_activated","plan_change_scheduled","auto_renew_updated","schedule_cancel","cancel_now","due_processed","payment_failed","trial_ended"]
PMETHODS = ["manual_cash","manual_bank","simulated_card","simulated_wallet"]
FAIL_MSGS = ["Insufficient funds","Card declined","Expired card","Invalid CVV","Network timeout","Bank rejected"]

def main():
    print("=" * 55)
    print("Bulk Year Data — fast insert")
    print("=" * 55)

    with SessionLocal() as session:
        # ------------------------------------------------------------------
        # Load existing reference data
        # ------------------------------------------------------------------
        plans = session.scalars(select(models.Plan).where(models.Plan.organization_id == ORG_ID)).all()
        prices = session.scalars(select(models.PlanPrice).where(models.PlanPrice.organization_id == ORG_ID)).all()
        settings = session.scalar(select(models.Settings).where(models.Settings.organization_id == ORG_ID))
        
        if not plans or not prices:
            print("ERROR: No plans/prices found. Run seed first.")
            return

        # Map prices by plan
        plan_prices = {}
        for p in prices:
            plan_prices.setdefault(p.plan_id, []).append(p)

        # ------------------------------------------------------------------
        # 1. +30 Customers & Addresses
        # ------------------------------------------------------------------
        existing_custs = session.scalars(select(models.Customer).where(models.Customer.organization_id == ORG_ID)).all()
        existing_emails = {c.email for c in existing_custs if c.email}
        custs_to_add = []
        addrs_to_add = []
        
        for i in range(30):
            is_comp = random.random() < 0.45
            if is_comp:
                dname = pick(COMPANIES)
                cname = dname
                email = f"billing.{dname.lower().replace(' ','')}@{random.choice(['gmail.com','yahoo.com','outlook.com','company.ph'])}"
            else:
                fn, ln = pick(FIRSTS), pick(LASTS)
                dname = f"{fn} {ln}"
                cname = None
                email = f"{fn.lower()}.{ln.lower().replace(' ','')}@{random.choice(['gmail.com','yahoo.com','outlook.com'])}"
            
            while email in existing_emails:
                email = email.replace("@", f"{random.randint(1,999)}@")
            existing_emails.add(email)
            
            c = models.Customer(
                id=uid(), organization_id=ORG_ID,
                customer_code=f"CUS-{random.randint(100000,999999):06d}",
                customer_type="organization" if is_comp else "individual",
                display_name=dname, company_name=cname,
                email=email,
                phone=f"09{random.randint(10,99):02d}{random.randint(1000000,9999999):07d}",
                tax_identifier=f"TIN-{random.randint(100000000,999999999):09d}" if is_comp else None,
                status=random.choices(["active","active","archived"],[80,15,5])[0],
                created_by=ADMIN, updated_by=ADMIN,
                created_at=randdt(datetime(2024,1,1,tzinfo=timezone.utc), datetime(2024,11,1,tzinfo=timezone.utc)),
            )
            custs_to_add.append(c)
            
            city, prov, post = pick(CITIES)
            addrs_to_add.append(models.Address(
                id=uid(), organization_id=ORG_ID, customer_id=c.id,
                address_type=random.choice(["billing","shipping"]),
                line1=f"{random.randint(1,999)} {pick(['Main','Commerce','Rizal','Mabini','Quezon'])} St.",
                line2=f"Suite {random.randint(100,999)}" if is_comp else None,
                city_municipality=city, province=prov, postal_code=post,
                country_code="PH", is_primary=True,
                created_by=ADMIN, updated_by=ADMIN,
            ))

        session.bulk_save_objects(custs_to_add)
        session.bulk_save_objects(addrs_to_add)
        session.flush()
        print(f"  Customers +{len(custs_to_add)}  |  Addresses +{len(addrs_to_add)}")

        # Refresh customer list
        all_customers = session.scalars(select(models.Customer).where(models.Customer.organization_id == ORG_ID)).all()
        active_customers = [c for c in all_customers if c.status == "active"]

        # ------------------------------------------------------------------
        # 2. +44 Subscriptions (full year lifecycle)
        # ------------------------------------------------------------------
        subs_to_add = []
        statuses = ["active","trialing","pending_payment","past_due","suspended","cancelled","expired"]
        weights = [40, 12, 8, 7, 5, 15, 13]
        now = utcnow()
        
        for i in range(44):
            cust = pick(active_customers)
            price = pick(prices)
            plan = next(p for p in plans if p.id == price.plan_id)
            status = random.choices(statuses, weights=weights)[0]
            
            # Realistic start date across the full year
            start = randdt(datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 12, 1, tzinfo=timezone.utc))
            
            trial = status == "trialing" and plan.trial_days > 0
            tstart = start if trial else None
            tend = start + timedelta(days=plan.trial_days) if trial else None
            
            if status in ["active", "pending_payment", "past_due", "suspended"]:
                cstart = start if not trial else tend
                days = 30 if price.billing_interval == "month" else 365
                cend = cstart + timedelta(days=days)
                # Add 0-3 past billing periods
                periods_past = random.randint(0, 3)
                cstart = cstart + timedelta(days=days * periods_past)
                cend = cend + timedelta(days=days * periods_past)
                nxt = cend
            elif status == "cancelled":
                cstart = start
                cend = start + timedelta(days=30)
                nxt = None
            elif status == "expired":
                cstart = start
                cend = start + timedelta(days=random.randint(28, 365))
                nxt = None
            else:
                cstart = None
                cend = None
                nxt = None

            subs_to_add.append(models.Subscription(
                id=uid(), organization_id=ORG_ID,
                subscription_number=f"SUB-{random.randint(100000,999999):06d}",
                customer_id=cust.id, plan_id=plan.id, plan_price_id=price.id,
                status=status, starts_at=start,
                trial_start_at=tstart, trial_end_at=tend,
                current_period_start=cstart, current_period_end=cend,
                next_billing_at=nxt,
                auto_renew=status not in ["cancelled","expired"] and random.random() < 0.80,
                cancel_at_period_end=(status == "cancelled" and random.random() < 0.7),
                cancelled_at=cend if status == "cancelled" else None,
                ended_at=cend if status in ["cancelled","expired"] else None,
                cancellation_reason=(pick(["Customer request","Competitor switch","Cost reduction","Business closed","No longer needed"]) if status == "cancelled" else None),
                version=random.randint(1, 6),
                created_by=ADMIN, updated_by=ADMIN,
                created_at=start,
            ))

        session.bulk_save_objects(subs_to_add)
        session.flush()
        print(f"  Subscriptions +{len(subs_to_add)}")

        # Refresh subscriptions
        all_subs = session.scalars(select(models.Subscription).where(models.Subscription.organization_id == ORG_ID)).all()

        # ------------------------------------------------------------------
        # 3. +70 Invoices + Invoice Items (multiple billing periods per sub)
        # ------------------------------------------------------------------
        invs_to_add = []
        items_to_add = []
        
        # First: add historical invoices for active/trialing/pending/past_due subs
        billable_subs = [s for s in all_subs if s.status not in ["expired"]]
        for sub in billable_subs[:55]:  # limit to avoid overflow
            price = next((p for p in prices if p.id == sub.plan_price_id), None)
            if not price:
                continue
            
            # Generate 1-3 historical invoices for this sub
            num_invs = random.randint(1, 3)
            base_date = (sub.starts_at or sub.trial_end_at or datetime(2024,1,1,tzinfo=timezone.utc)).date()
            
            for inv_idx in range(num_invs):
                issue = base_date + timedelta(days=(30 if price.billing_interval == "month" else 365) * inv_idx)
                if issue > date.today():
                    break
                due = issue + timedelta(days=7)
                inv_status = random.choices(["draft","open","paid","overdue","void"],[10,30,25,20,15])[0]
                
                invs_to_add.append(models.Invoice(
                    id=uid(), organization_id=ORG_ID,
                    invoice_number=f"INV-{random.randint(100000,999999):06d}",
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

        # Standalone invoices (not linked to subs)
        for i in range(15):
            cust = pick(active_customers)
            issue = randdate(date(2024,1,1), date.today())
            due = issue + timedelta(days=7)
            inv_status = random.choices(["draft","open","paid","overdue","void"],[10,30,25,20,15])[0]
            invs_to_add.append(models.Invoice(
                id=uid(), organization_id=ORG_ID,
                invoice_number=f"INV-{random.randint(100000,999999):06d}",
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

        session.bulk_save_objects(invs_to_add)
        session.flush()

        # Add line items for each new invoice
        for inv in invs_to_add:
            # If linked to subscription, add recurring item
            if inv.subscription_id:
                sub = next((s for s in all_subs if s.id == inv.subscription_id), None)
                if sub:
                    price = next((p for p in prices if p.id == sub.plan_price_id), None)
                    if price:
                        items_to_add.append(models.InvoiceItem(
                            id=uid(), organization_id=ORG_ID, invoice_id=inv.id,
                            line_number=1, item_type="recurring",
                            description=f"Subscription renewal ({price.billing_interval})",
                            quantity=1, unit_amount_minor=price.unit_amount_minor + price.setup_fee_minor,
                            tax_rate_bps=0,
                            service_period_start=inv.service_period_start,
                            service_period_end=inv.service_period_end,
                            plan_id=sub.plan_id, plan_price_id=price.id,
                            created_by=ADMIN, updated_by=ADMIN,
                        ))
                        # Sometimes add setup or adjustment
                        if random.random() < 0.3:
                            items_to_add.append(models.InvoiceItem(
                                id=uid(), organization_id=ORG_ID, invoice_id=inv.id,
                                line_number=2, item_type=random.choice(["setup","adjustment"]),
                                description=pick(["Setup fee","One-time discount","Proration adjustment","Migration service"]),
                                quantity=1, unit_amount_minor=random.choice([-5000, -2500, 5000, 10000]),
                                tax_rate_bps=0,
                                service_period_start=inv.service_period_start,
                                service_period_end=inv.service_period_end,
                                created_by=ADMIN, updated_by=ADMIN,
                            ))
            else:
                # Standalone: 1-3 line items
                for line in range(1, random.randint(2, 4)):
                    items_to_add.append(models.InvoiceItem(
                        id=uid(), organization_id=ORG_ID, invoice_id=inv.id,
                        line_number=line, item_type=random.choice(["setup","adjustment","recurring"]),
                        description=pick(["Professional services","Consulting hours","Development","Training","Support package","Data migration"]),
                        quantity=random.randint(1,5),
                        unit_amount_minor=random.choice([5000,10000,15000,25000,50000]),
                        tax_rate_bps=0,
                        service_period_start=inv.service_period_start,
                        service_period_end=inv.service_period_end,
                        created_by=ADMIN, updated_by=ADMIN,
                    ))

        session.bulk_save_objects(items_to_add)
        session.flush()
        print(f"  Invoices +{len(invs_to_add)}  |  Items +{len(items_to_add)}")

        # Refresh invoices
        all_invoices = session.scalars(select(models.Invoice).where(models.Invoice.organization_id == ORG_ID)).all()

        # ------------------------------------------------------------------
        # 4. +50 Payments + Allocations
        # ------------------------------------------------------------------
        pays_to_add = []
        allocs_to_add = []
        open_paid_invs = [inv for inv in all_invoices if inv.status in ["open","paid","overdue"]]
        
        for i in range(50):
            cust = pick(active_customers)
            method = pick(PMETHODS)
            amount = random.choice([4900,9900,14900,19900,29900,39900,49900,59900,79900,99900,129900])
            status = random.choices(["completed","voided"],[92,8])[0]
            received = randdt(datetime(2024,1,1,tzinfo=timezone.utc), datetime(2024,12,15,tzinfo=timezone.utc))
            
            pays_to_add.append(models.Payment(
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

        session.bulk_save_objects(pays_to_add)
        session.flush()

        # Allocations: link payments to customer invoices
        for pay in pays_to_add:
            if pay.status != "completed":
                continue
            cust_invs = [inv for inv in open_paid_invs if inv.customer_id == pay.customer_id]
            if cust_invs and random.random() < 0.6:
                target = pick(cust_invs)
                alloc = min(pay.amount_minor, random.randint(pay.amount_minor // 3, pay.amount_minor))
                allocs_to_add.append(models.PaymentAllocation(
                    id=uid(), organization_id=ORG_ID,
                    payment_id=pay.id, invoice_id=target.id,
                    amount_minor=alloc, allocated_at=pay.received_at,
                    created_by=ADMIN, updated_by=ADMIN,
                ))

        session.bulk_save_objects(allocs_to_add)
        session.flush()
        print(f"  Payments +{len(pays_to_add)}  |  Allocations +{len(allocs_to_add)}")

        # ------------------------------------------------------------------
        # 5. +35 Payment Attempts
        # ------------------------------------------------------------------
        atts_to_add = []
        open_invs = [inv for inv in all_invoices if inv.status == "open"]
        for i in range(35):
            if not open_invs:
                break
            inv = pick(open_invs)
            status = random.choices(["pending","succeeded","failed"],[25,40,35])[0]
            attempted = randdt(datetime(2024,6,1,tzinfo=timezone.utc), datetime(2024,12,15,tzinfo=timezone.utc))
            amount = random.choice([4900,9900,19900,29900,49900,59900])
            atts_to_add.append(models.PaymentAttempt(
                id=uid(), organization_id=ORG_ID,
                attempt_reference=f"ATT-{random.randint(100000,999999):06d}",
                invoice_id=inv.id, provider="simulated",
                provider_attempt_id=f"sim_{uid()[:8]}" if status != "pending" else None,
                idempotency_key=f"idem_{uid()}",
                request_hash="bulk-hash",
                status=status, amount_minor=amount, currency=inv.currency,
                attempted_at=attempted,
                completed_at=attempted if status != "pending" else None,
                failure_message=(pick(FAIL_MSGS) if status == "failed" else None),
                created_by=ADMIN, updated_by=ADMIN,
            ))
        session.bulk_save_objects(atts_to_add)
        session.flush()
        print(f"  Payment Attempts +{len(atts_to_add)}")

        # ------------------------------------------------------------------
        # 6. +30 Subscription Events
        # ------------------------------------------------------------------
        evts_to_add = []
        for i in range(30):
            sub = pick(all_subs)
            etype = pick(EVT_TYPES)
            sub_start = sub.starts_at if sub.starts_at.tzinfo else sub.starts_at.replace(tzinfo=timezone.utc)
            effective = randdt(sub_start, max(sub_start, datetime(2024,12,15,tzinfo=timezone.utc)))
            
            from_status = sub.status
            to_status = sub.status
            if etype == "created":
                from_status = None
                to_status = "trialing" if sub.trial_start_at else "pending_payment"
            elif etype in ["activated", "payment_activated"]:
                from_status = pick(["pending_payment","past_due","suspended"])
                to_status = "active"
            elif etype == "schedule_cancel":
                from_status = sub.status
            elif etype == "cancel_now":
                to_status = "cancelled"
            elif etype == "trial_ended":
                from_status = "trialing"
                to_status = "pending_payment"
            elif etype == "payment_failed":
                from_status = "active"
                to_status = "past_due"

            evts_to_add.append(models.SubscriptionEvent(
                id=uid(), organization_id=ORG_ID, subscription_id=sub.id,
                event_type=etype, from_status=from_status, to_status=to_status,
                effective_at=effective, actor_type="user",
                reason=pick(["System processed","User action","Payment received","Scheduled event","Auto-renewal","Manual override"]),
                correlation_id=uid(),
                metadata_json={"source": "bulk_year_data"},
                created_by=ADMIN, updated_by=ADMIN,
                created_at=effective,
            ))
        session.bulk_save_objects(evts_to_add)
        session.flush()
        print(f"  Subscription Events +{len(evts_to_add)}")

        # ------------------------------------------------------------------
        # 7. +20 Notifications
        # ------------------------------------------------------------------
        notifs_to_add = []
        NOTIF_TEMPLATES = [
            ("trial_ending","Trial Ending Soon","Your trial ends in {days} days. Add payment method to avoid interruption."),
            ("invoice_generated","New Invoice","Invoice {inv} for {amount} is due {due}."),
            ("payment_received","Payment Received","We received {amount} for invoice {inv}. Thank you!"),
            ("payment_failed","Payment Failed","Could not process {amount}. Please update payment method."),
            ("subscription_activated","Subscription Active","Your subscription {sub} is now active."),
            ("plan_changed","Plan Change Scheduled","Your change to {plan} takes effect on {date}."),
            ("subscription_cancelled","Subscription Cancelled","Your subscription {sub} has been cancelled."),
            ("overdue_reminder","Overdue Invoice","Invoice {inv} is overdue. Please settle to avoid suspension."),
            ("welcome","Welcome Aboard","Welcome to Argo! Your account is set up and ready."),
            ("password_changed","Security Alert","Your password was changed on {date}. Contact support if unexpected."),
        ]
        for i in range(20):
            ntype, title, body_tmpl = pick(NOTIF_TEMPLATES)
            cust = pick(all_customers)
            sub = pick(all_subs) if random.random() < 0.5 else None
            inv = pick(all_invoices) if random.random() < 0.5 else None
            sent = randdt(datetime(2024,1,1,tzinfo=timezone.utc), datetime(2024,12,15,tzinfo=timezone.utc))
            body = body_tmpl.format(
                days=random.randint(1,5),
                inv=inv.invoice_number if inv else "INV-000000",
                amount=f"PHP {random.choice([99,299,599,799,1299]):,}.00",
                due=(sent + timedelta(days=7)).date().isoformat(),
                sub=sub.subscription_number if sub else "SUB-000000",
                plan=pick(["Starter","Growth","Pro","Enterprise","Elite"]),
                date=sent.date().isoformat(),
            )
            notifs_to_add.append(models.Notification(
                id=uid(), organization_id=ORG_ID,
                customer_id=cust.id,
                recipient_user_id=ADMIN,
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
        session.bulk_save_objects(notifs_to_add)
        session.flush()
        print(f"  Notifications +{len(notifs_to_add)}")

        # ------------------------------------------------------------------
        # 8. +40 Activity Logs
        # ------------------------------------------------------------------
        logs_to_add = []
        ACTIONS = ["created","updated","viewed","deleted","finalized","voided","recorded","status_changed","allocated","exported"]
        pools = [
            ("customer", all_customers),
            ("plan", plans),
            ("subscription", all_subs),
            ("invoice", all_invoices),
            ("payment", pays_to_add),
        ]
        for i in range(40):
            etype, pool = pick(pools)
            entity = pick(pool)
            ts = randdt(datetime(2024,1,1,tzinfo=timezone.utc), datetime(2024,12,15,tzinfo=timezone.utc))
            logs_to_add.append(models.ActivityLog(
                id=uid(), organization_id=ORG_ID,
                entity_type=etype, entity_id=entity.id,
                action=pick(ACTIONS), actor_user_id=ADMIN,
                request_id=uid(),
                details_json={"source": "bulk_year_data", "batch": True},
                created_by=ADMIN, updated_by=ADMIN,
                created_at=ts,
            ))
        session.bulk_save_objects(logs_to_add)
        session.flush()
        print(f"  Activity Logs +{len(logs_to_add)}")

        # ------------------------------------------------------------------
        # Commit everything
        # ------------------------------------------------------------------
        session.commit()

    print("-" * 55)
    print("Bulk year data inserted successfully.")
    print("=" * 55)

if __name__ == "__main__":
    main()
