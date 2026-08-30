import sys
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_invoice_pdf(order, items, payment):
    """
    Generates a professional PDF invoice for an order.
    Returns:
        bytes: Binary PDF data.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    primary_color = colors.HexColor("#F18421")  # Tazaura primary orange
    dark_text = colors.HexColor("#1A1A1A")
    light_text = colors.HexColor("#4A4A4A")
    light_bg = colors.HexColor("#F8FAFC")
    border_color = colors.HexColor("#E2E8F0")
    
    # Text Styles
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color
    )
    
    header_style = ParagraphStyle(
        'InvoiceHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.white
    )
    
    body_style = ParagraphStyle(
        'InvoiceBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=light_text
    )
    
    body_bold_style = ParagraphStyle(
        'InvoiceBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=dark_text
    )
    
    bold_style = ParagraphStyle(
        'InvoiceBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=dark_text
    )

    story = []
    
    # 1. Header Section: Brand name on left, "TAX INVOICE" on right
    header_data = [
        [
            Paragraph("Tazaura", title_style),
            Paragraph("<b>TAX INVOICE</b>", ParagraphStyle('TaxInvoice', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, leading=22, alignment=2, textColor=dark_text))
        ]
    ]
    header_table = Table(header_data, colWidths=[270, 270])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
    ]))
    story.append(header_table)
    
    # 2. Seller and Invoice Meta info (2 columns)
    # Seller info
    seller_details = (
        "<b>SOLD BY:</b><br/>"
        "<b>Tazaura Private Limited</b><br/>"
        "Address: Pukuria, Jhargram,<br/>"
        "West Bengal, 721514, India<br/>"
        "Phone: +91 8327347783<br/>"
        "Email: care@tazaura.in"
    )
    
    # Format date
    order_date = order.get("created_at")
    if isinstance(order_date, datetime):
        date_str = order_date.strftime("%Y-%m-%d %H:%M")
    elif order_date:
        date_str = str(order_date)[:16]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
    payment_method = "N/A"
    payment_status = "Pending"
    payment_txid = "N/A"
    if payment:
        payment_method = payment.get("method", "UPI").upper()
        payment_status = payment.get("status", "Pending").capitalize()
        payment_txid = payment.get("razorpay_payment_id") or "N/A"
        
    invoice_meta = (
        "<b>INVOICE DETAILS:</b><br/>"
        f"Order ID: <b>#{order.get('id')}</b><br/>"
        f"Invoice No: <b>INV-{datetime.now().year}-{order.get('id'):05d}</b><br/>"
        f"Order Date: {date_str}<br/>"
        f"Payment Method: {payment_method}<br/>"
        f"Payment Status: <b>{payment_status}</b><br/>"
        f"Transaction ID: {payment_txid}"
    )
    
    meta_table_data = [
        [
            Paragraph(seller_details, body_style),
            Paragraph(invoice_meta, body_style)
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))
    
    # 3. Bill To Section (Customer Address)
    bill_to_name = order.get("bill_to_name") or order.get("customer_name") or "Customer"
    bill_to_phone = order.get("bill_to_phone") or "N/A"
    
    address_lines = []
    if order.get("line1"):
        address_lines.append(order["line1"])
    if order.get("line2"):
        address_lines.append(order["line2"])
    
    location_parts = []
    if order.get("city"):
        location_parts.append(order["city"])
    if order.get("state"):
        location_parts.append(order["state"])
    if order.get("pincode"):
        location_parts.append(order["pincode"])
        
    address_str = ", ".join(address_lines)
    if location_parts:
        address_str += "<br/>" + ", ".join(location_parts)
    if not address_str:
        address_str = "No address provided"
        
    customer_details = (
        "<b>BILL TO:</b><br/>"
        f"<b>{bill_to_name}</b><br/>"
        f"Phone: {bill_to_phone}<br/>"
        f"Address: {address_str}"
    )
    
    customer_table_data = [
        [
            Paragraph(customer_details, body_style),
            "" # Empty right side
        ]
    ]
    customer_table = Table(customer_table_data, colWidths=[350, 190])
    customer_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
    ]))
    story.append(customer_table)
    story.append(Spacer(1, 10))
    
    # 4. Items Table
    # Table headers
    table_data = [
        [
            Paragraph("Item Description", header_style),
            Paragraph("Unit", header_style),
            Paragraph("Unit Price", header_style),
            Paragraph("Qty", header_style),
            Paragraph("Total", header_style)
        ]
    ]
    
    # Items loop
    for item in items:
        unit = item.get("unit") or "N/A"
        price = float(item.get("unit_price") or 0.0)
        qty = int(item.get("quantity") or 1)
        amount = float(item.get("amount") or (price * qty))
        
        table_data.append([
            Paragraph(item.get("name") or "Product", body_style),
            Paragraph(unit, body_style),
            Paragraph(f"₹{price:.2f}", body_style),
            Paragraph(str(qty), body_style),
            Paragraph(f"₹{amount:.2f}", body_bold_style)
        ])
        
    # Grand Total row
    grand_total = float(order.get("total_price") or 0.0)
    table_data.append([
        Paragraph("<b>Total Amount Payable</b>", bold_style),
        "", "", "",
        Paragraph(f"<b>₹{grand_total:.2f}</b>", bold_style)
    ])
    
    items_table = Table(table_data, colWidths=[240, 60, 80, 50, 110])
    items_table.setStyle(TableStyle([
        # Header formatting
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        
        # Grid lines and backgrounds
        ('GRID', (0,0), (-1,-2), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, light_bg]),
        
        # Total Row formatting
        ('SPAN', (0, -1), (3, -1)), # Span first 4 columns for total label
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#FFF7ED")),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, primary_color),
        ('GRID', (0,-1), (-1,-1), 0.5, border_color),
    ]))
    story.append(items_table)
    
    # 5. Footer Terms / Thank You note
    story.append(Spacer(1, 40))
    thanks_style = ParagraphStyle(
        'InvoiceThanks',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=14,
        alignment=1, # Centered
        textColor=primary_color
    )
    story.append(Paragraph("Thank you for shopping with Tazaura!", thanks_style))
    
    # Build Document
    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data
