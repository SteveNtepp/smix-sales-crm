from fpdf import FPDF
from datetime import datetime
import io

class SmixInvoice(FPDF):
    def header(self):
        # Logo placeholder (can be improved if a real logo file is provided)
        self.set_font('helvetica', 'B', 20)
        self.set_text_color(94, 23, 235) # Smix Purple
        self.cell(0, 10, 'SMIX ACADEMY', ln=True, align='L')
        
        self.set_font('helvetica', '', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'Facturation & Reçus Digitaux', ln=True, align='L')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()} | Smix Academy - Document Officiel', align='C')

def generate_invoice_pdf(data: dict):
    """
    Generates a PDF bytes object for an invoice/receipt.
    data: {
        "invoice_number": "INV-2024-001",
        "date": "18/03/2026",
        "client_name": "Jean Dupont",
        "client_email": "jean@example.com",
        "items": [
            {"desc": "Bootcamp CMA", "qty": 1, "price": "75 000 FCFA"},
            ...
        ],
        "total": "75 000 FCFA"
    }
    """
    pdf = SmixInvoice()
    pdf.add_page()
    
    # Header Info
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"FACTURE / REÇU : {data['invoice_number']}", ln=True)
    
    pdf.set_font('helvetica', '', 11)
    pdf.cell(0, 7, f"Date : {data.get('date', datetime.now().strftime('%d/%m/%Y'))}", ln=True)
    pdf.ln(5)
    
    # Client section
    pdf.set_fill_color(245, 245, 250)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, " DESTINATAIRE", ln=True, fill=True)
    pdf.set_font('helvetica', '', 11)
    pdf.cell(0, 7, f" Nom : {data['client_name']}", ln=True)
    if data.get('client_email'):
        pdf.cell(0, 7, f" Email : {data['client_email']}", ln=True)
    pdf.ln(10)
    
    # Table Header
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(94, 23, 235) # Purple
    
    pdf.cell(110, 10, " Description", border=1, fill=True)
    pdf.cell(20,  10, " Qté", border=1, fill=True, align='C')
    pdf.cell(60,  10, " Montant", border=1, fill=True, align='C')
    pdf.ln()
    
    # Table Body
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('helvetica', '', 10)
    
    for item in data['items']:
        pdf.cell(110, 10, f" {item['desc']}", border=1)
        pdf.cell(20,  10, str(item['qty']), border=1, align='C')
        pdf.cell(60,  10, f" {item['price']}", border=1, align='R')
        pdf.ln()
        
    # Total
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(130, 10, " TOTAL", border=1, align='R')
    pdf.set_fill_color(230, 230, 255)
    pdf.cell(60,  10, f" {data['total']}", border=1, fill=True, align='R')
    
    pdf.ln(20)
    pdf.set_font('helvetica', 'I', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, "Merci de votre confiance.\nCe document fait office de reçu officiel après confirmation du paiement.")

    # Return as bytes
    return pdf.output()
