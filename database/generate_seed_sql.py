"""
Seed Data Generator for VoltTrack (MySQL 8.0)
Generates 02_seed_data.sql with comprehensive, realistic Indian data.
"""
import random
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timedelta

def main():
    random.seed(42)
    
    lines = []
    lines.append("-- ==============================================================================")
    lines.append("-- VoltTrack: Smart Meter Data Management System")
    lines.append("-- File: 02_seed_data.sql")
    lines.append("-- Description: Seed data: 6 areas, 8 tariffs, 10 employees, 60 customers,")
    lines.append("--              75 meters, app users, bills, payments, complaints, alerts.")
    lines.append("-- Target DBMS: MySQL 8.0")
    lines.append("-- ==============================================================================\n")
    lines.append("USE smartmeter;\n")
    lines.append("SET FOREIGN_KEY_CHECKS = 0;\n")

    # 1. Areas
    lines.append("-- 1. Areas")
    areas = [
        (1, "Indiranagar", "Indiranagar 66kV Substation", "Bengaluru"),
        (2, "Koramangala", "Koramangala 110kV Substation", "Bengaluru"),
        (3, "Whitefield", "ITPL 220kV Grid Substation", "Bengaluru"),
        (4, "Jayanagar", "Jayanagar 66kV Substation", "Bengaluru"),
        (5, "Electronic City", "E-City 110kV Substation", "Bengaluru"),
        (6, "Malleshwaram", "Malleshwaram 66kV Substation", "Bengaluru"),
    ]
    lines.append("INSERT INTO area (area_id, area_name, substation, city) VALUES")
    area_rows = [f"({aid}, '{name}', '{sub}', '{city}')" for aid, name, sub, city in areas]
    lines.append(",\n".join(area_rows) + ";\n")

    # 2. Tariff Slabs
    lines.append("-- 2. Tariff Slabs")
    tariffs = [
        (1, 'DOMESTIC', 0.00, 100.00, 0.00, 50.00),
        (2, 'DOMESTIC', 100.00, 200.00, 2.35, 50.00),
        (3, 'DOMESTIC', 200.00, 500.00, 4.70, 50.00),
        (4, 'DOMESTIC', 500.00, 99999.00, 6.30, 50.00),
        (5, 'COMMERCIAL', 0.00, 100.00, 6.50, 150.00),
        (6, 'COMMERCIAL', 100.00, 99999.00, 8.00, 150.00),
        (7, 'INDUSTRIAL', 0.00, 1000.00, 7.50, 500.00),
        (8, 'INDUSTRIAL', 1000.00, 999999.00, 8.25, 500.00),
    ]
    lines.append("INSERT INTO tariff (tariff_id, category, slab_from, slab_to, rate_per_unit, fixed_charge) VALUES")
    tariff_rows = [f"({tid}, '{cat}', {sf:.2f}, {st:.2f}, {rate:.2f}, {fc:.2f})" for tid, cat, sf, st, rate, fc in tariffs]
    lines.append(",\n".join(tariff_rows) + ";\n")

    # 3. Employees
    lines.append("-- 3. Employees")
    employees = [
        (1, "Rajesh Sharma", "ADMIN", 1, "9845012340"),
        (2, "Suresh Kumar", "TECHNICIAN", 1, "9845012341"),
        (3, "Anil Verma", "TECHNICIAN", 2, "9845012342"),
        (4, "Ramesh Gowda", "TECHNICIAN", 3, "9845012343"),
        (5, "Vijay Nair", "TECHNICIAN", 4, "9845012344"),
        (6, "Santosh Rao", "METER_READER", 5, "9845012345"),
        (7, "Manoj Patil", "METER_READER", 6, "9845012346"),
        (8, "Deepa Hegde", "METER_READER", 1, "9845012347"),
        (9, "Priya Iyer", "BILLING_OFFICER", 2, "9845012348"),
        (10, "Kavita Reddy", "BILLING_OFFICER", 3, "9845012349"),
    ]
    lines.append("INSERT INTO employee (emp_id, name, role, area_id, phone) VALUES")
    emp_rows = [f"({eid}, '{name}', '{role}', {aid}, '{phone}')" for eid, name, role, aid, phone in employees]
    lines.append(",\n".join(emp_rows) + ";\n")

    # 4. Customers (60 customers)
    lines.append("-- 4. Customers")
    first_names = [
        "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
        "Shaurya", "Atharva", "Dhruv", "Kabir", "Rohan", "Ananya", "Diya", "Gauri", "Aditi", "Isha",
        "Kavya", "Anushka", "Meera", "Riya", "Sneha", "Pooja", "Vikram", "Sunil", "Alok", "Deepak",
        "Gautam", "Harish", "Karthik", "Manish", "Naveen", "Pradeep", "Raghav", "Sanjay", "Tarun", "Varun",
        "Sunita", "Lakshmi", "Preeti", "Radha", "Swati", "Nandini", "Shilpa", "Rekha", "Divya", "Sandhya",
        "Amit", "Sumit", "Nitin", "Rohit", "Akash", "Kunal", "Tushar", "Siddharth", "Abhishek", "Hemant"
    ]
    last_names = [
        "Sharma", "Verma", "Gupta", "Patel", "Reddy", "Nair", "Iyer", "Rao", "Gowda", "Kulkarni",
        "Deshmukh", "Joshi", "Bhat", "Shetty", "Mishra", "Pandey", "Singh", "Chauhan", "Agarwal", "Mehta"
    ]

    customers = []
    used_phones = set()
    used_emails = set()

    for i in range(1, 61):
        fn = first_names[(i - 1) % len(first_names)]
        ln = last_names[(i * 3) % len(last_names)]
        name = f"{fn} {ln}"
        
        # Determine category: 45 Domestic (1-45), 10 Commercial (46-55), 5 Industrial (56-60)
        if i <= 45:
            cat = "DOMESTIC"
            addr = f"#{random.randint(10, 999)}, Cross {random.randint(1, 15)}, Sector {random.randint(1, 9)}"
        elif i <= 55:
            cat = "COMMERCIAL"
            addr = f"Shop #{random.randint(1, 80)}, Commercial Complex, Main Road"
        else:
            cat = "INDUSTRIAL"
            addr = f"Plot #{random.randint(10, 150)}, Industrial Estate, Phase {random.randint(1, 3)}"

        aid = ((i - 1) % 6) + 1
        
        phone_core = 9800000000 + i * 137 + random.randint(10, 99)
        phone = f"9{str(phone_core)[1:10]}"
        while phone in used_phones:
            phone_core += 1
            phone = f"9{str(phone_core)[1:10]}"
        used_phones.add(phone)

        email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
        while email in used_emails:
            email = f"{fn.lower()}{random.randint(100, 999)}@example.com"
        used_emails.add(email)

        customers.append((i, name, addr, aid, phone, email, cat))

    lines.append("INSERT INTO customer (customer_id, name, address, area_id, phone, email, category) VALUES")
    cust_rows = [f"({cid}, '{name}', '{addr}', {aid}, '{ph}', '{em}', '{cat}')" for cid, name, addr, aid, ph, em, cat in customers]
    lines.append(",\n".join(cust_rows) + ";\n")

    # 5. Meters (75 meters across 60 customers)
    lines.append("-- 5. Smart Meters")
    meters = []
    mid = 1
    for cid, name, addr, aid, ph, em, cat in customers:
        mtype = 'THREE_PHASE' if cat in ('COMMERCIAL', 'INDUSTRIAL') else 'SINGLE_PHASE'
        inst_date = date(2025, 1, 1) + timedelta(days=random.randint(10, 300))
        meters.append((mid, cid, mtype, inst_date.isoformat(), 'ACTIVE', f"Main Panel - {addr[:30]}"))
        mid += 1

    # Add extra meters for 15 commercial/industrial customers to reach 75 meters
    extra_cust_ids = [46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60]
    for cid in extra_cust_ids:
        inst_date = date(2025, 6, 1) + timedelta(days=random.randint(10, 150))
        status = 'ACTIVE' if random.random() > 0.15 else 'FAULTY'
        meters.append((mid, cid, 'THREE_PHASE', inst_date.isoformat(), status, f"Sub-Meter Back Wing - Cust #{cid}"))
        mid += 1

    lines.append("INSERT INTO meter (meter_id, customer_id, meter_type, install_date, status, location) VALUES")
    m_rows = [f"({m[0]}, {m[1]}, '{m[2]}', '{m[3]}', '{m[4]}', '{m[5]}')" for m in meters]
    lines.append(",\n".join(m_rows) + ";\n")

    # 6. App Users (RBAC)
    lines.append("-- 6. Application Users (Hashed Passwords)")
    default_hash = generate_password_hash("Volt@123")
    admin_hash = generate_password_hash("admin123")

    app_users = [
        (1, "admin", admin_hash, "ADMIN", "NULL", 1, "TRUE"),
        (2, "technician", default_hash, "TECHNICIAN", "NULL", 2, "TRUE"),
        (3, "tech_anil", default_hash, "TECHNICIAN", "NULL", 3, "TRUE"),
        (4, "tech_ramesh", default_hash, "TECHNICIAN", "NULL", 4, "TRUE"),
        (5, "tech_vijay", default_hash, "TECHNICIAN", "NULL", 5, "TRUE"),
        (6, "billing", default_hash, "BILLING_OFFICER", "NULL", 9, "TRUE"),
        (7, "billing_kavita", default_hash, "BILLING_OFFICER", "NULL", 10, "TRUE"),
    ]

    uid = 8
    for cid in range(1, 61):
        uname = f"customer{cid}"
        # Give customer 1 convenient alias 'customer'
        if cid == 1:
            uname = "customer"
        app_users.append((uid, uname, default_hash, "CUSTOMER", cid, "NULL", "TRUE"))
        uid += 1

    lines.append("INSERT INTO app_user (user_id, username, password_hash, role, customer_id, emp_id, is_active) VALUES")
    u_rows = [f"({u[0]}, '{u[1]}', '{u[2]}', '{u[3]}', {u[4]}, {u[5]}, {u[6]})" for u in app_users]
    lines.append(",\n".join(u_rows) + ";\n")

    # 7. Seed Past 3 Months Bills (June, July, August 2026) for all 60 customers -> 180 bills
    lines.append("-- 7. Bills (180 bills across past 3 months)")
    months = [
        date(2026, 6, 1),
        date(2026, 7, 1),
        date(2026, 8, 1)
    ]
    
    bills = []
    bid = 1
    for m in months:
        due_d = date(m.year, m.month, 28) + timedelta(days=15)
        for cid, name, addr, aid, ph, em, cat in customers:
            if cat == 'DOMESTIC':
                units = round(random.uniform(80.0, 420.0), 2)
                # Formula:
                # 0-100: 0
                # 100-200: 2.35
                # 200-500: 4.70
                # fixed: 50
                u = units
                eng = 0
                if u > 100:
                    eng += min(u - 100, 100) * 2.35
                if u > 200:
                    eng += min(u - 200, 300) * 4.70
                amt = round(eng + 50.0, 2)
            elif cat == 'COMMERCIAL':
                units = round(random.uniform(350.0, 1200.0), 2)
                u = units
                eng = min(u, 100) * 6.50
                if u > 100:
                    eng += (u - 100) * 8.00
                amt = round(eng + 150.0, 2)
            else: # INDUSTRIAL
                units = round(random.uniform(2500.0, 7500.0), 2)
                u = units
                eng = min(u, 1000) * 7.50
                if u > 1000:
                    eng += (u - 1000) * 8.25
                amt = round(eng + 500.0, 2)

            status = random.choice(['PAID', 'PAID', 'PAID', 'PARTIAL', 'UNPAID']) if m.month < 8 else random.choice(['UNPAID', 'PARTIAL', 'PAID'])
            bills.append((bid, cid, m.isoformat(), units, amt, due_d.isoformat(), status))
            bid += 1

    lines.append("INSERT INTO bill (bill_id, customer_id, billing_period, units, amount, due_date, status) VALUES")
    b_rows = [f"({b[0]}, {b[1]}, '{b[2]}', {b[3]:.2f}, {b[4]:.2f}, '{b[5]}', '{b[6]}')" for b in bills]
    lines.append(",\n".join(b_rows) + ";\n")

    # 8. Seed Payments (120+ payments)
    lines.append("-- 8. Payments")
    payments = []
    pid = 1
    for b in bills:
        bid, cid, period, units, amt, due_d, status = b
        if status == 'PAID':
            pmode = random.choice(['UPI', 'CARD', 'NETBANKING'])
            pref = f"TXN2026{pid:06d}{random.randint(100, 999)}"
            pdate = f"{period[:7]}-{random.randint(10, 25):02d} 14:30:00"
            payments.append((pid, bid, amt, pmode, pdate, pref))
            pid += 1
        elif status == 'PARTIAL':
            part_amt = round(amt * random.uniform(0.3, 0.6), 2)
            pmode = random.choice(['UPI', 'CARD', 'NETBANKING'])
            pref = f"TXN2026{pid:06d}{random.randint(100, 999)}"
            pdate = f"{period[:7]}-{random.randint(10, 25):02d} 11:15:00"
            payments.append((pid, bid, part_amt, pmode, pdate, pref))
            pid += 1

    lines.append("INSERT INTO payment (payment_id, bill_id, amount, mode, paid_at, transaction_ref) VALUES")
    p_rows = [f"({p[0]}, {p[1]}, {p[2]:.2f}, '{p[3]}', '{p[4]}', '{p[5]}')" for p in payments]
    lines.append(",\n".join(p_rows) + ";\n")

    # 9. Seed Complaints (30 complaints)
    lines.append("-- 9. Customer Complaints")
    complaints = []
    types = ['BILLING', 'METER_FAULT', 'OUTAGE', 'OTHER']
    statuses = ['OPEN', 'ASSIGNED', 'RESOLVED']
    for cid in range(1, 31):
        ctype = random.choice(types)
        cstat = random.choice(statuses)
        assigned = random.choice([2, 3, 4, 5]) if cstat in ('ASSIGNED', 'RESOLVED') else "NULL"
        desc = f"Investigation requested for {ctype.lower().replace('_', ' ')} incident recorded on meter."
        cdate = f"2026-08-{random.randint(1, 28):02d} {random.randint(8, 18):02d}:00:00"
        complaints.append((cid, cid, ctype, desc, cstat, assigned, cdate))

    lines.append("INSERT INTO complaint (complaint_id, customer_id, type, description, status, assigned_to, created_at) VALUES")
    c_rows = [f"({c[0]}, {c[1]}, '{c[2]}', '{c[3]}', '{c[4]}', {c[5]}, '{c[6]}')" for c in complaints]
    lines.append(",\n".join(c_rows) + ";\n")

    # 10. Seed Alerts (45 alerts)
    lines.append("-- 10. Meter Alerts")
    alerts = []
    alert_types = ['HIGH_USAGE', 'TAMPER', 'OUTAGE', 'LOW_VOLTAGE']
    aid = 1
    for m in random.sample(meters, 45):
        meter_id = m[0]
        atype = random.choice(alert_types)
        if atype == 'HIGH_USAGE':
            msg = f"Unusual consumption spike: {round(random.uniform(5.5, 9.8), 2)} kWh in 1 hour"
        elif atype == 'TAMPER':
            msg = f"Zero consumption with live line voltage (232.4V) - possible meter bypass"
        elif atype == 'OUTAGE':
            msg = f"Zero line voltage detected on phase A"
        else:
            msg = f"Dangerous voltage sag detected: {round(random.uniform(145.0, 175.0), 1)} V"
        
        raised = f"2026-08-{random.randint(1, 28):02d} {random.randint(1, 23):02d}:15:00"
        res = random.choice(['TRUE', 'FALSE'])
        alerts.append((aid, meter_id, atype, msg, raised, res))
        aid += 1

    lines.append("INSERT INTO alert (alert_id, meter_id, type, message, raised_at, is_resolved) VALUES")
    al_rows = [f"({a[0]}, {a[1]}, '{a[2]}', '{a[3]}', '{a[4]}', {a[5]})" for a in alerts]
    lines.append(",\n".join(al_rows) + ";\n")

    # 11. Initial Audit Log Entries
    lines.append("-- 11. Audit Log Seed")
    lines.append("INSERT INTO audit_log (table_name, record_id, action, old_value, new_value, changed_by) VALUES")
    lines.append("('tariff', '1', 'INITIALIZE', NULL, 'category=DOMESTIC, slab_from=0, slab_to=100, rate=0.00, fixed=50.00', 'system_setup'),")
    lines.append("('tariff', '5', 'INITIALIZE', NULL, 'category=COMMERCIAL, slab_from=0, slab_to=100, rate=6.50, fixed=150.00', 'system_setup');\n")

    lines.append("SET FOREIGN_KEY_CHECKS = 1;\n")

    out_path = r"C:\Users\alitr\.gemini\antigravity\scratch\volttrack\database\02_seed_data.sql"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {out_path} with {len(customers)} customers, {len(meters)} meters, {len(bills)} bills, {len(payments)} payments.")

if __name__ == "__main__":
    main()

