import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_invoice_pdf(bill_data, tariff_slabs):
    """
    Generates a professional utility bill PDF buffer using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=colors.HexColor("#0F172A"), # Deep Navy
        leading=24
    )

    sub_style = ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#64748B"),
        leading=12
    )

    bold_label = ParagraphStyle(
        "BoldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=colors.HexColor("#334155")
    )

    val_style = ParagraphStyle(
        "ValLabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#0F172A")
    )

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>VoltTrack</b> <font size=11 color='#0D9488'>Smart Energy Grid</font>", title_style),
            Paragraph(f"<b>TAX INVOICE</b><br/><font color='#64748B'>Bill #{bill_data['bill_id']:06d}</font>", ParagraphStyle("RightHdr", parent=title_style, alignment=2, fontSize=14))
        ],
        [
            Paragraph("Karnataka Electricity Regulatory Commission (KERC)<br/>Bengaluru Smart Substation Division, Karnataka, India", sub_style),
            Paragraph(f"Billing Period: <b>{bill_data['billing_period']}</b><br/>Due Date: <b>{bill_data['due_date']}</b>", ParagraphStyle("RightDts", parent=sub_style, alignment=2))
        ]
    ]
    t_header = Table(header_data, colWidths=[4.0 * inch, 3.5 * inch])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0D9488"), spaceBefore=5, spaceAfter=15))

    # 2. Customer & Meter Info Grid
    cust_table_data = [
        [
            Paragraph("<b>CONSUMER DETAILS</b>", ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#0D9488"))),
            Paragraph("<b>METER & CONNECTION</b>", ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#0D9488")))
        ],
        [
            Paragraph(f"<b>Name:</b> {bill_data['customer_name']}<br/><b>Address:</b> {bill_data.get('address', 'N/A')}<br/><b>Phone:</b> +91 {bill_data.get('phone', 'N/A')}<br/><b>Email:</b> {bill_data.get('email', 'N/A')}", val_style),
            Paragraph(f"<b>Customer ID:</b> #{bill_data['customer_id']:04d}<br/><b>Substation Area:</b> {bill_data.get('area_name', 'Bengaluru Grid')}<br/><b>Tariff Category:</b> {bill_data['category']}<br/><b>Status:</b> <b><font color='{ '#16A34A' if bill_data['status']=='PAID' else '#DC2626'}'>{bill_data['status']}</font></b>", val_style)
        ]
    ]
    t_cust = Table(cust_table_data, colWidths=[3.75 * inch, 3.75 * inch])
    t_cust.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_cust)
    story.append(Spacer(1, 15))

    # 3. Slab Breakdown Calculation Table
    units = float(bill_data['units'])
    slab_rows = [
        ["Tariff Slab (Units)", "Rate / Unit (₹)", "Units In Slab", "Amount (₹)"]
    ]

    calc_energy = 0.0
    fixed_charge = 0.0
    for slab in tariff_slabs:
        if slab["category"] == bill_data["category"]:
            fixed_charge = float(slab["fixed_charge"])
            sf = float(slab["slab_from"])
            st = float(slab["slab_to"])
            rate = float(slab["rate_per_unit"])
            if units > sf:
                units_in_slab = min(units, st) - sf
                cost = units_in_slab * rate
                calc_energy += cost
                label = f"{int(sf)} - {int(st) if st < 90000 else 'Above'}"
                slab_rows.append([label, f"₹{rate:.2f}", f"{units_in_slab:.2f}", f"₹{cost:.2f}"])

    slab_rows.append(["Fixed Connection Charge", "-", "-", f"₹{fixed_charge:.2f}"])
    slab_rows.append(["Total Energy Billed", "-", f"{units:.2f} kWh", f"₹{bill_data['amount']}"])

    t_slabs = Table(slab_rows, colWidths=[2.5 * inch, 1.5 * inch, 1.75 * inch, 1.75 * inch])
    t_slabs.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_slabs)
    story.append(Spacer(1, 15))

    # 4. Settlement Summary
    paid = float(bill_data.get('paid', 0.0))
    balance = float(bill_data.get('balance', float(bill_data['amount']) - paid))

    settle_data = [
        ["Total Invoiced Amount:", f"₹{float(bill_data['amount']):.2f}"],
        ["Amount Paid to Date:", f"₹{paid:.2f}"],
        ["Outstanding Balance Due:", f"₹{balance:.2f}"]
    ]
    t_settle = Table(settle_data, colWidths=[5.5 * inch, 2.0 * inch])
    t_settle.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor("#DC2626") if balance > 0 else colors.HexColor("#16A34A")),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_settle)
    story.append(Spacer(1, 20))

    # 5. Regulatory Footer
    footer_text = Paragraph(
        "<b>Notice:</b> Payments made after the due date will incur a late surcharge of 1.5% per month. "
        "Pay online via UPI, NetBanking or Credit/Debit card using the VoltTrack Consumer Portal. "
        "This is an electronically generated document authorized by the Smart Energy Monitoring Platform.",
        sub_style
    )
    story.append(footer_text)

    doc.build(story)
    buffer.seek(0)
    return buffer
