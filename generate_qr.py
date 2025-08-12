import io
import qrcode
from qrcode.constants import ERROR_CORRECT_M
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import black
from reportlab.lib.utils import ImageReader

# ===================== CONFIG =====================
urls = [f"https://aqua.permai-kencana.com/qr/t-pk-{str(i).zfill(3)}" for i in range(1, 25)]

qr_size_cm = 5.0          # exact printed QR size
padding_cm = 0.25         # left/right/top padding inside the card (no bottom pad)
spacing_cm = 1.0          # space between cards
font_size = 15            # label font size (pt)

# precise visual gap between QR bottom and label top (points)
GAP_PT = 1.0              # try 0.5–2.0 to taste
BOTTOM_MARGIN_PT = 2.0    # baseline safety above bottom border

PT_PER_CM = 72.0 / 2.54

# Minimal label area so text fits
label_height_cm = max((font_size + BOTTOM_MARGIN_PT) / PT_PER_CM, 0.45)

# ===================== LAYOUT =====================
width, height = A4
card_width_cm  = qr_size_cm + 2 * padding_cm
card_height_cm = qr_size_cm + label_height_cm + padding_cm   # NO bottom padding below QR
card_with_spacing_cm = card_height_cm + spacing_cm

usable_width_cm = (width / cm) - spacing_cm
cols = max(int(usable_width_cm // (card_width_cm + spacing_cm)), 1)
card_total_width = (cols * card_width_cm + (cols - 1) * spacing_cm) * cm
rows_per_page = max(int((height / cm - 2 * spacing_cm) // card_with_spacing_cm), 1)
page_center_x = width / 2

# ===================== PDF =====================
pdf_path = "qr_codes_tight_no_internal_border.pdf"
c = canvas.Canvas(pdf_path, pagesize=A4)

def qr_image_reader(data: str) -> ImageReader:
    """Build a QR image with NO built-in quiet zone (border=0)."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,  # M is fine; use H if you need more robustness
        box_size=10,
        border=1,                          # <-- remove internal white border (quiet zone)
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)

for i, url in enumerate(urls):
    row = (i // cols) % rows_per_page
    col = i % cols

    if i and i % (cols * rows_per_page) == 0:
        c.showPage()

    # vertically center grid per page
    page_idx = i // (cols * rows_per_page)
    remaining = len(urls) - page_idx * cols * rows_per_page
    rows_this_page = min(rows_per_page, (remaining + cols - 1) // cols)
    grid_height_cm = rows_this_page * card_with_spacing_cm
    vertical_margin_cm = (height / cm - grid_height_cm) / 2

    y_offset = height - vertical_margin_cm * cm - card_height_cm * cm
    y = y_offset - row * card_with_spacing_cm * cm
    x_start = page_center_x - card_total_width / 2
    x = x_start + col * (card_width_cm + spacing_cm) * cm

    # card border
    c.setLineWidth(1)
    c.setStrokeColor(black)
    c.rect(x, y, card_width_cm * cm, card_height_cm * cm, stroke=1, fill=0)

    # draw QR (exact size), sitting directly above the label area
    qr_reader = qr_image_reader(url)
    qr_x = x + padding_cm * cm
    qr_y = y + label_height_cm * cm
    c.drawImage(qr_reader, qr_x, qr_y, width=qr_size_cm * cm, height=qr_size_cm * cm)

    # label: make the TOP of text GAP_PT below the QR bottom
    # drawCentredString uses baseline; baseline = top - ascent ≈ top - 0.8*font_size
    ascent = 0.80 * font_size
    baseline = qr_y - (GAP_PT + ascent)
    baseline = max(baseline, y + BOTTOM_MARGIN_PT)  # avoid clipping descenders

    c.setFont("Helvetica-Bold", font_size)
    c.setFillColorRGB(0, 0, 0)
    label = url.split("/")[-1].upper()   # <-- was .capitalize()
    c.drawCentredString(x + (card_width_cm * cm) / 2, baseline, label)

c.save()
print(f"✅ PDF saved to: {pdf_path}")
