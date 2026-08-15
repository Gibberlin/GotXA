"""PDF report generation utilities."""
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def generate_report_pdf(report_data):
    """
    Generate PDF report from report data dictionary.
    
    Args:
        report_data: Dict with keys: title, report_type, filters, data (list of dicts), timestamp
    
    Returns:
        BytesIO: PDF file buffer
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#555555'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=6,
        spaceBefore=12
    )
    
    # Header
    elements.append(Paragraph(report_data.get('title', 'Report'), title_style))
    elements.append(Paragraph(
        f"Type: {report_data.get('report_type', 'General')} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        subtitle_style
    ))
    elements.append(Spacer(1, 0.3*inch))
    
    # Filters section
    if report_data.get('filters'):
        elements.append(Paragraph("Report Filters", section_style))
        filters_data = [[k, str(v)] for k, v in report_data['filters'].items()]
        filters_table = Table(filters_data, colWidths=[2*inch, 4*inch])
        filters_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8e8e8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        elements.append(filters_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Data section
    if report_data.get('data') and len(report_data['data']) > 0:
        elements.append(Paragraph("Report Data", section_style))
        
        # Build table
        data_list = report_data['data']
        if isinstance(data_list[0], dict):
            headers = list(data_list[0].keys())
            rows = [headers] + [[str(row.get(h, '')) for h in headers] for row in data_list]
        else:
            rows = data_list
        
        # Calculate column widths
        num_cols = len(rows[0]) if rows else 1
        col_width = 6.5 * inch / num_cols
        
        table = Table(rows, colWidths=[col_width] * num_cols)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003d7a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        elements.append(table)
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(
        f"<i>Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S UTC')}</i>",
        styles['Normal']
    ))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
