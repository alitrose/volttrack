# VoltTrack: Data Flow Diagrams (DFD)

This document specifies the Data Flow Diagrams (Level 0 Context Diagram and Level 1 Detailed DFD) for the **VoltTrack Smart Meter Data Management System**.

---

## 1. DFD Level 0: Context Diagram

The context diagram represents the high-level boundary of the VoltTrack system, its external entities (Consumers, Field Technicians, Billing Officers, Administrators, and IoT Smart Meters), and the primary data streams entering and exiting the platform.

```mermaid
flowchart TD
    METER(["IoT Smart Meter"]):::ext
    CUSTOMER(["Consumer"]):::ext
    TECH(["Field Technician"]):::ext
    BILLING(["Billing Officer"]):::ext
    ADMIN(["System Administrator"]):::ext

    SYS[["VoltTrack Smart Meter Management System\n(MySQL 8.0 + Flask REST API)"]]:::sys

    METER -->|"Hourly Readings (kWh, Voltage, PF)"| SYS
    SYS -->|"Tamper / Outage Alerts"| TECH

    CUSTOMER -->|"Credentials, Complaint, Payment"| SYS
    SYS -->|"Usage Graphs, Invoices, PDF Bills, Receipts"| CUSTOMER

    TECH -->|"Ticket Resolution, Meter Status Updates"| SYS
    SYS -->|"Assigned Complaints, Area Faults"| TECH

    BILLING -->|"Batch Billing Run Trigger"| SYS
    SYS -->|"Accounts Receivable, Aging Reports, CSV"| BILLING

    ADMIN -->|"Tariff Slab Updates, User Management"| SYS
    SYS -->|"Audit Trail, Analytics, mysqldump Snapshot"| ADMIN

    classDef ext fill:#1E293B,stroke:#38BDF8,stroke-width:2px,color:#F8FAFC;
    classDef sys fill:#0F172A,stroke:#0D9488,stroke-width:3px,color:#FFFFFF;
```

---

## 2. DFD Level 1: Subsystem Process Decomposition

The Level 1 DFD decomposes the system into six core automated processes and highlights interactions with the normalized MySQL datastores.

```mermaid
flowchart LR
    %% External Entities
    METER(["IoT Meter"]):::ext
    CUST(["Consumer"]):::ext
    OFFICER(["Billing Officer"]):::ext
    TECH(["Technician"]):::ext
    ADMIN(["Admin"]):::ext

    %% Processes
    P1["1.0\nAuthentication\n& RBAC Guard"]:::proc
    P2["2.0\nReading Ingestion\n& Alert Triggering"]:::proc
    P3["3.0\nSlab Billing Engine\n(Cursor Procedure)"]:::proc
    P4["4.0\nPayment Settlement\n(Row-Lock & Savepoint)"]:::proc
    P5["5.0\nComplaint Triage\n& Fleet Health"]:::proc
    P6["6.0\nAnalytics, Audit\n& Backup Engine"]:::proc

    %% Data Stores
    D1[("D1: app_user")]:::ds
    D2[("D2: meter_reading")]:::ds
    D3[("D3: alert")]:::ds
    D4[("D4: tariff")]:::ds
    D5[("D5: bill")]:::ds
    D6[("D6: payment")]:::ds
    D7[("D7: complaint")]:::ds
    D8[("D8: audit_log")]:::ds

    %% Data Flows
    CUST -->|"Login Request"| P1
    P1 <-->|"Verify Hash & Role"| D1
    P1 -->|"JWT Token"| CUST

    METER -->|"X-API-KEY + Ingest Data"| P2
    P2 -->|"Insert Interval Reading"| D2
    P2 -.->|"Trigger (trg_reading_alerts)"| D3
    D3 -->|"Dispatch Live Feed"| TECH

    OFFICER -->|"Trigger Month Run"| P3
    P3 <-->|"Fetch Category Slabs"| D4
    P3 <-->|"Sum Readings"| D2
    P3 -->|"Insert Idempotent Bill"| D5
    D5 -->|"PDF Statement"| CUST

    CUST -->|"Pay Bill (UPI/Card)"| P4
    P4 <-->|"Lock Row & Check Balance"| D5
    P4 -->|"Record Payment"| D6
    D6 -.->|"Trigger (trg_payment_status)"| D5

    CUST -->|"Lodge Ticket"| P5
    P5 -->|"Store Ticket"| D7
    TECH <-->|"Resolve Ticket / Update Meter"| D7

    ADMIN -->|"Modify Tariff Slabs"| P6
    P6 -->|"Update Slab"| D4
    D4 -.->|"Trigger (trg_tariff_audit)"| D8
    P6 <-->|"Window Function Aggregates"| D2
    P6 -->|"mysqldump Snapshot"| ADMIN

    classDef ext fill:#1E293B,stroke:#38BDF8,stroke-width:2px,color:#F8FAFC;
    classDef proc fill:#0F172A,stroke:#0D9488,stroke-width:2px,color:#FFFFFF;
    classDef ds fill:#334155,stroke:#94A3B8,stroke-width:1.5px,color:#F8FAFC;
```
