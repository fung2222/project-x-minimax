from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY    = "1A2744"   # deep navy – sheet / section headers
STEEL   = "2D4A7A"   # mid blue  – sub-headers
GOLD    = "C9A84C"   # gold      – accent / today's row highlight
WHITE   = "FFFFFF"
LTGRAY  = "F2F4F7"
MIDGRAY = "D8DCE3"
BLACK   = "000000"
BLUE_IN = "0000FF"   # hard-coded input cells

def make_fill(hex_col):
    return PatternFill("solid", fgColor=hex_col)

def make_border(style="thin"):
    s = Side(style=style)
    return Border(left=s, right=s, top=s, bottom=s)

def header_font(size=11, bold=True, color=WHITE):
    return Font(name="Calibri", size=size, bold=bold, color=color)

def body_font(size=10, bold=False, color=BLACK):
    return Font(name="Calibri", size=size, bold=bold, color=color)

def input_font():
    return Font(name="Calibri", size=10, bold=False, color=BLUE_IN)

def pct_fmt(ws, cell):
    ws[cell].number_format = '0.00%'

def usd_fmt(ws, cell):
    ws[cell].number_format = '$#,##0.00'

# ── Create workbook ──────────────────────────────────────────────────────────
wb = Workbook()

# ══════════════════════════════════════════════════════════════════════════════
# SHEET 1 – Portfolio Overview
# ══════════════════════════════════════════════════════════════════════════════
ws1 = wb.active
ws1.title = "Portfolio"
ws1.sheet_view.showGridLines = False

# Title banner
ws1.merge_cells("A1:L1")
ws1["A1"] = "📊  PROJECT X  –  SIMULATED PORTFOLIO OVERVIEW"
ws1["A1"].font = Font(name="Calibri", size=16, bold=True, color=WHITE)
ws1["A1"].fill = make_fill(NAVY)
ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws1.row_dimensions[1].height = 36

# Meta row
ws1.merge_cells("A2:L2")
ws1["A2"] = "  📅  Started: 2025-07-05  |  🔧 Platform: Futu (富途牛牛)  |  🎯 Strategy: AI & Tech Growth  |  ⚠️ For education only – not financial advice"
ws1["A2"].font = Font(name="Calibri", size=9, italic=True, color=WHITE)
ws1["A2"].fill = make_fill(STEEL)
ws1.row_dimensions[2].height = 20

ws1.row_dimensions[3].height = 8  # spacer

# ── Assumptions block ──────────────────────────────────────────────────────
ws1["A4"] = "💰 SIMULATED ACCOUNT"
ws1["A4"].font = header_font(11)
ws1["A4"].fill = make_fill(STEEL)
ws1.merge_cells("A4:C4")

ws1["A5"] = "Starting Capital (USD)"
ws1["B5"] = 100000
ws1["B5"].font = input_font()
ws1["B5"].number_format = '$#,##0'

ws1["A6"] = "Today's Date"
ws1["B6"] = "2025-07-05"
ws1["B6"].font = input_font()

ws1["A7"] = "Portfolio Value"
ws1["B7"] = "=B5"   # start equal to capital
ws1["B7"].number_format = '$#,##0'

ws1["A8"] = "Total P&L ($)"
ws1["B8"] = "=B7-B5"
ws1["B8"].number_format = '$#,##0;(#$,##0);"-"'

ws1["A9"] = "Total Return (%)"
ws1["B9"] = "=IFERROR((B7-B5)/B5,0)"
ws1["B9"].number_format = '0.00%'

ws1["A10"] = "Cash Available"
ws1["B10"] = "=B5"
ws1["B10"].number_format = '$#,##0'

ws1.row_dimensions[4].height = 22

# ── Stock watch-list ────────────────────────────────────────────────────────
row = 12
ws1.merge_cells(f"A{row}:L{row}")
ws1[f"A{row}"] = "🔭  STOCK WATCH LIST  –  AI & TECH FOCUS"
ws1[f"A{row}"].font = header_font(11)
ws1[f"A{row}"].fill = make_fill(NAVY)
ws1.row_dimensions[row].height = 22

row += 1
headers = ["Ticker","Company","Sector","Curr. Price","Qty (Sim)","Cost Basis","Mkt Value","P&L ($)","P&L (%)","Analyst Rating","Target Price","Notes"]
for col, h in enumerate(headers, start=1):
    c = ws1.cell(row=row, column=col, value=h)
    c.font = header_font(10)
    c.fill = make_fill(STEEL)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = make_border()

ws1.row_dimensions[row].height = 28

# Stock data (inputs in blue, formulas in black)
stocks = [
    # (Ticker, Company, Sector, CurrPrice, Qty, CostBasis, Rating, Target, Notes)
    ("NVDA", "NVIDIA", "AI/Hardware", 140, 50, 120, "Buy", 200, "AI GPU leader; Blackwell ramp-up"),
    ("AMD",  "Advanced Micro Devices","AI/Hardware",130, 100, 115, "Buy", 185, "MI350/400 competitive vs NVDA"),
    ("MSFT", "Microsoft", "AI/Cloud", 410, 30, 380, "Buy", 520, "Azure AI momentum; Copilot revenue"),
    ("GOOGL","Alphabet/Google","AI/Search",185, 40, 170, "Hold", 210, "AI search risk; Cloud strong +28%"),
    ("META", "Meta Platforms","AI/Social", 520, 20, 470, "Buy", 650, "AI ad targeting; Llama ecosystem"),
    ("AMZN", "Amazon","AI/Cloud/E-comm", 190, 40, 175, "Buy", 240, "AWS AI services;广告增长"),
    ("PLTR", "Palantir","AI/Defense", 120, 60, 80,  "Buy", 160, "AIP platform; US Navy contract"),
    ("ARM",  "Arm Holdings","AI/Design", 140, 80, 125, "Hold", 180, "IP licensing; AI on-device"),
]

stock_rows = []
for i, (ticker, company, sector, price, qty, cost, rating, target, notes) in enumerate(stocks):
    r = row + 1 + i
    stock_rows.append(r)

    ws1.cell(r, 1, ticker).font  = Font(name="Calibri", size=10, bold=True, color=BLACK)
    ws1.cell(r, 2, company).font = body_font()
    ws1.cell(r, 3, sector).font  = body_font()
    ws1.cell(r, 4, price).font   = input_font()
    ws1.cell(r, 5, qty).font     = input_font()
    ws1.cell(r, 6, cost).font    = input_font()

    # Formulas
    ws1.cell(r, 7, f"=D{r}*E{r}").number_format = '$#,##0'
    ws1.cell(r, 8, f"=(D{r}-F{r})*E{r}").number_format = '$#,##0;(#$,##0);"-"'
    ws1.cell(r, 9, f"=IFERROR((D{r}-F{r})/F{r},0)").number_format = '0.00%'
    ws1.cell(r,10, rating).font  = body_font()
    ws1.cell(r,11, target).font  = input_font()
    ws1.cell(r,12, notes).font   = body_font()

    for col in range(1, 13):
        ws1.cell(r, col).border = make_border()
        if col in (4,5,6,11):
            ws1.cell(r, col).fill = make_fill(LTGRAY)
        if col == 9:
            ws1.cell(r, col).fill = make_fill(MIDGRAY)

    ws1.row_dimensions[r].height = 20

# Portfolio totals row
tot_r = row + 1 + len(stocks)
ws1.merge_cells(f"A{tot_r}:F{tot_r}")
ws1[f"A{tot_r}"] = "PORTFOLIO TOTAL"
ws1[f"A{tot_r}"].font = Font(name="Calibri", size=10, bold=True, color=WHITE)
ws1[f"A{tot_r}"].fill = make_fill(NAVY)
ws1[f"A{tot_r}"].alignment = Alignment(horizontal="right")

first_s = stock_rows[0]
last_s  = stock_rows[-1]
ws1[f"G{tot_r}"] = f"=SUM(G{first_s}:G{last_s})"
ws1[f"G{tot_r}"].number_format = '$#,##0'
ws1[f"G{tot_r}"].font = Font(name="Calibri", size=10, bold=True, color=WHITE)
ws1[f"G{tot_r}"].fill = make_fill(NAVY)

ws1[f"H{tot_r}"] = f"=SUM(H{first_s}:H{last_s})"
ws1[f"H{tot_r}"].number_format = '$#,##0;(#$,##0);"-"'
ws1[f"H{tot_r}"].font = Font(name="Calibri", size=10, bold=True, color=WHITE)
ws1[f"H{tot_r}"].fill = make_fill(NAVY)

ws1[f"I{tot_r}"] = f"=IFERROR((G{tot_r}-SUM(F{first_s}:F{last_s}))/SUM(F{first_s}:F{last_s}),0)"
ws1[f"I{tot_r}"].number_format = '0.00%'
ws1[f"I{tot_r}"].font = Font(name="Calibri", size=10, bold=True, color=WHITE)
ws1[f"I{tot_r}"].fill = make_fill(NAVY)

# Update portfolio value cell to reflect holdings
ws1["B7"] = f"=G{tot_r}"
ws1["B8"] = f"=B7-B5"
ws1["B9"] = f"=IFERROR((B7-B5)/B5,0)"
ws1["B10"] = f"=B5-G{tot_r}"

for col in range(1, 13):
    ws1.cell(tot_r, col).border = make_border()

# Column widths
col_widths = [8, 22, 16, 12, 11, 12, 13, 12, 10, 14, 13, 40]
for i, w in enumerate(col_widths, start=1):
    ws1.column_dimensions[get_column_letter(i)].width = w

# ══════════════════════════════════════════════════════════════════════════════
# SHEET 2 – Daily Tracker
# ══════════════════════════════════════════════════════════════════════════════
ws2 = wb.create_sheet("Daily Tracker")
ws2.sheet_view.showGridLines = False

ws2.merge_cells("A1:O1")
ws2["A1"] = "📅  DAILY PERFORMANCE TRACKER  –  LOG EVERY TRADING DAY"
ws2["A1"].font = Font(name="Calibri", size=14, bold=True, color=WHITE)
ws2["A1"].fill = make_fill(NAVY)
ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws2.row_dimensions[1].height = 36

ws2.merge_cells("A2:O2")
ws2["A2"] = "  Fill in 'Price' (blue cells) daily. Yellow = action needed. Green = strong signal. Red = warning."
ws2["A2"].font = Font(name="Calibri", size=9, italic=True)
ws2["A2"].fill = make_fill(LTGRAY)
ws2.row_dimensions[2].height = 18

# Header row
ws2.row_dimensions[3].height = 8
hdr_r = 4
d_headers = ["Date","Ticker","Curr. Price","Prev. Price","$ Change","% Change","Qty","Mkt Value",
             "Sim. Action","Qty Traded","Exec Price","Brokerage","Notes / Signal"]
for col, h in enumerate(d_headers, start=1):
    c = ws2.cell(row=hdr_r, column=col, value=h)
    c.font = header_font(10)
    c.fill = make_fill(STEEL)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = make_border()
ws2.row_dimensions[hdr_r].height = 28

# Pre-fill first data row with today
first_data = hdr_r + 1
today_stocks = [
    ("2025-07-05","NVDA",140,None,"Watch","",0,"",""),
    ("2025-07-05","AMD",130,None,"Watch","",0,"",""),
    ("2025-07-05","MSFT",410,None,"Watch","",0,"",""),
    ("2025-07-05","GOOGL",185,None,"Watch","",0,"",""),
    ("2025-07-05","META",520,None,"Watch","",0,"",""),
    ("2025-07-05","AMZN",190,None,"Watch","",0,"",""),
    ("2025-07-05","PLTR",120,None,"Watch","",0,"",""),
    ("2025-07-05","ARM",140,None,"Watch","",0,"",""),
]

for i, (date, ticker, price, prev, action, qty, exec_price, brokerage, notes) in enumerate(today_stocks):
    r = first_data + i
    ws2.cell(r, 1, date).font = body_font()
    ws2.cell(r, 2, ticker).font = Font(name="Calibri", size=10, bold=True)
    ws2.cell(r, 3, price).font = input_font()
    ws2.cell(r, 3).number_format = '$#,##0.00'
    ws2.cell(r, 4, f"=C{r}").font = body_font()  # prev price = today's (no change yet)
    ws2.cell(r, 5, f"=C{r}-D{r}").number_format = '$#,##0.00;(#$,##0.00);"-"'
    ws2.cell(r, 6, f"=IFERROR((C{r}-D{r})/D{r},0)").number_format = '0.00%'
    ws2.cell(r, 7, f"=C{r}*1").font = input_font()  # qty placeholder
    ws2.cell(r, 8, f"=C{r}*G{r}").number_format = '$#,##0'
    ws2.cell(r, 9, action).font = body_font()
    ws2.cell(r,10, qty).font = input_font()
    ws2.cell(r,11, exec_price).font = input_font()
    ws2.cell(r,11).number_format = '$#,##0.00'
    ws2.cell(r,12, brokerage).font = input_font()
    ws2.cell(r,12).number_format = '$#,##0.00'
    ws2.cell(r,13, notes).font = body_font()

    for col in range(1, 14):
        ws2.cell(r, col).border = make_border()
        if col == 3:
            ws2.cell(r, col).fill = make_fill(LTGRAY)
    ws2.row_dimensions[r].height = 18

# Column widths
d_widths = [12, 8, 12, 12, 10, 10, 7, 12, 12, 10, 11, 11, 30]
for i, w in enumerate(d_widths, start=1):
    ws2.column_dimensions[get_column_letter(i)].width = w

# ══════════════════════════════════════════════════════════════════════════════
# SHEET 3 – Macro Dashboard
# ══════════════════════════════════════════════════════════════════════════════
ws3 = wb.create_sheet("Macro Dashboard")
ws3.sheet_view.showGridLines = False

ws3.merge_cells("A1:F1")
ws3["A1"] = "🌍  MACRO & MARKET CONTEXT DASHBOARD"
ws3["A1"].font = Font(name="Calibri", size=14, bold=True, color=WHITE)
ws3["A1"].fill = make_fill(NAVY)
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 36

ws3.merge_cells("A2:F2")
ws3["A2"] = "  Last updated: 2025-07-05  |  Source: Federal Reserve, BLS, Reuters, Market Data"
ws3["A2"].font = Font(name="Calibri", size=9, italic=True)
ws3["A2"].fill = make_fill(STEEL)
ws3.row_dimensions[2].height = 18

# ── Fed & Rates ────────────────────────────────────────────────────────────
ws3["A4"] = "💵  FEDERAL RESERVE & RATES"
ws3["A4"].font = header_font(11)
ws3["A4"].fill = make_fill(NAVY)
ws3.merge_cells("A4:F4")
ws3.row_dimensions[4].height = 22

fed_data = [
    ("Fed Funds Rate (Upper)", "4.50%", "2025-07-30 FOMC", "Holding – unchanged for 5th consecutive meeting"),
    ("Fed Funds Rate (Lower)", "4.25%", "2025-07-30 FOMC", "9-2 vote; 2 dissenters wanted cuts"),
    ("CPI (June 2025)", "2.7%", "2025-07-10 BLS", "Above Fed target of 2%; goods inflation sticky"),
    ("Trimmed-mean CPI", "3.2%", "2025-07-10 BLS", "Persistent underlying price pressure"),
    ("Q2 GDP Growth", "3.0% SAAR", "2025-07-30 BEA", "Strong beat vs 2.3% estimate; reversing Q1 -0.5% decline"),
    ("Jobs (July NFP)", "35k avg/3mo", "2025-08-01 BLS", "Sharp drop from 125k avg; unemployment 4.2%"),
    ("30yr Mortgage Rate", "~6.78%", "2025-07-15", "2nd consecutive weekly increase"),
    ("Market Pricing (2025 cuts)", "2×25bps", "CME FedWatch", "Back to pricing cuts after weak jobs report"),
]

fed_hdr = ["Indicator","Value","Source / Date","Notes"]
for col, h in enumerate(fed_hdr, start=1):
    c = ws3.cell(row=5, column=col, value=h)
    c.font = header_font(10)
    c.fill = make_fill(STEEL)
    c.border = make_border()
ws3.row_dimensions[5].height = 22

for i, (ind, val, src, note) in enumerate(fed_data):
    r = 6 + i
    ws3.cell(r, 1, ind).font  = body_font(bold=True)
    ws3.cell(r, 2, val).font = input_font()
    ws3.cell(r, 3, src).font = body_font(color="555555")
    ws3.cell(r, 4, note).font = body_font()
    for col in range(1, 5):
        ws3.cell(r, col).border = make_border()
    ws3.row_dimensions[r].height = 18

# ── Market Indices ────────────────────────────────────────────────────────
mk_r = 6 + len(fed_data) + 2
ws3.merge_cells(f"A{mk_r}:F{mk_r}")
ws3[f"A{mk_r}"] = "📈  MARKET INDICES  (July 2025)"
ws3[f"A{mk_r}"].font = header_font(11)
ws3[f"A{mk_r}"].fill = make_fill(NAVY)
ws3.row_dimensions[mk_r].height = 22

mk_hdr = ["Index","July Return","YTD Return","52-Wk High","52-Wk Low","Status"]
for col, h in enumerate(mk_hdr, start=1):
    c = ws3.cell(row=mk_r+1, column=col, value=h)
    c.font = header_font(10)
    c.fill = make_fill(STEEL)
    c.border = make_border()
ws3.row_dimensions[mk_r+1].height = 22

indices = [
    ("S&P 500",    "+2.2%",  "+14%*",  "~6,100", "~4,800",  "New highs"),
    ("Nasdaq",     "+3.7%",  "+22%*",  "~20,000","~15,000", "Leading AI names"),
    ("Dow Jones",  "+0.1%",  "+8%*",   "~44,000","~37,000",  "Lagging"),
    ("NVDA",       "~+4%*",  "~+140%", "~175",   "~90",      "China H20 export relief"),
    ("AMD",        "~+7%*",  "~+60%*", "~$160",  "~$90",     "Export reprieve + MI350"),
    ("GOOGL",      "-5.2%*", "-6.8%*", "~$200",  "~$160",    "Antitrust trial risk"),
    ("MSFT",       "~+3%*",  "+15%*",  "~$530",  "~$390",    "Azure AI momentum"),
]

for i, row_data in enumerate(indices):
    r = mk_r + 2 + i
    for col, val in enumerate(row_data, start=1):
        c = ws3.cell(r, col, val)
        c.font = body_font(bold=(col==1))
        c.border = make_border()
    ws3.row_dimensions[r].height = 18

# ── Key Events Calendar ─────────────────────────────────────────────────────
ev_r = mk_r + 2 + len(indices) + 2
ws3.merge_cells(f"A{ev_r}:F{ev_r}")
ws3[f"A{ev_r}"] = "📆  UPCOMING CATALYSTS"
ws3[f"A{ev_r}"].font = header_font(11)
ws3[f"A{ev_r}"].fill = make_fill(NAVY)
ws3.row_dimensions[ev_r].height = 22

ev_hdr = ["Date","Event","Stocks Affected","Expected Impact","Risk","Notes"]
for col, h in enumerate(ev_hdr, start=1):
    c = ws3.cell(row=ev_r+1, column=col, value=h)
    c.font = header_font(10)
    c.fill = make_fill(STEEL)
    c.border = make_border()
ws3.row_dimensions[ev_r+1].height = 22

events = [
    ("Aug 2025", "AMD Earnings", "AMD", "MI350 revenue details", "High", "Key AI GPU demand signal"),
    ("Aug 2025", "NVDA Earnings", "NVDA", "Blackwell revenue guidance", "High", "Most-watched of the season"),
    ("Aug 2025", "Fed Minutes", "ALL", "Rate cut signals", "Medium", "July NFP impact on Sep cut odds"),
    ("Sep 2025", "FOMC Meeting", "ALL", "Potential first cut?", "High", "Markets pricing 50/50"),
    ("Q3 2025",  "Apple iPhone AI launch", "AAPL", "AI features drive upgrade cycle", "Medium", "Apple Intelligence rollout"),
    ("Ongoing",  "US-China trade talks", "NVDA, AMD", "H20/MI308 export licenses", "High", "Partial reprieve already granted"),
    ("Ongoing",  "EU AI Act enforcement", "MSFT, GOOGL, META", "Compliance costs", "Low", "Gradual implementation"),
]

for i, row_data in enumerate(events):
    r = ev_r + 2 + i
    for col, val in enumerate(row_data, start=1):
        c = ws3.cell(r, col, val)
        c.font = body_font(bold=(col==1))
        c.border = make_border()
        if col == 4:
            c.fill = make_fill(LTGRAY)
    ws3.row_dimensions[r].height = 18

# Column widths
for i, w in enumerate([22, 12, 12, 22, 8, 35], start=1):
    ws3.column_dimensions[get_column_letter(i)].width = w

# ══════════════════════════════════════════════════════════════════════════════
# SHEET 4 – Analyst Signals
# ══════════════════════════════════════════════════════════════════════════════
ws4 = wb.create_sheet("Analyst Signals")
ws4.sheet_view.showGridLines = False

ws4.merge_cells("A1:H1")
ws4["A1"] = "🎯  ANALYST RATINGS & PRICE TARGETS"
ws4["A1"].font = Font(name="Calibri", size=14, bold=True, color=WHITE)
ws4["A1"].fill = make_fill(NAVY)
ws4["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws4.row_dimensions[1].height = 36

ws4.merge_cells("A2:H2")
ws4["A2"] = "  Source: Zacks, Bloomberg, Reuters, TradeStation | Updated: 2025-07-05"
ws4["A2"].font = Font(name="Calibri", size=9, italic=True)
ws4["A2"].fill = make_fill(STEEL)
ws4.row_dimensions[2].height = 18

sig_hdr = ["Ticker","Analyst Firm","Date","Rating","Target Price","Curr. Price","Upside (%)","Notes"]
for col, h in enumerate(sig_hdr, start=1):
    c = ws4.cell(row=3, column=col, value=h)
    c.font = header_font(10)
    c.fill = make_fill(STEEL)
    c.alignment = Alignment(horizontal="center", vertical="center")
    c.border = make_border()
ws4.row_dimensions[3].height = 22

signals = [
    ("NVDA","Multiple Firms","Jul-25","Strong Buy","$180–$200","$140","+29%–+43%","China H20 export relief; Blackwell ramp"),
    ("AMD", "HSBC","Jul-10","Buy","$200","$130","+54%","MI350 credible NVDA challenger; MI400 2026"),
    ("AMD", "Wells Fargo","Jul-16","Buy","$185","$130","+42%","Data-center GPU sales stronger than expected"),
    ("AMD", "Bank of America","Jul-16","Buy","$175","$130","+35%","$400–600M/quarter AI GPU revenue potential"),
    ("GOOGL","Morgan Stanley","Jul-25","Overweight","$210","$185","+14%","Cloud +28% YoY; AI Search monetization"),
    ("GOOGL","Bernstein","Jul-25","Market Perform","$195","$185","+5%","Antitrust risk limits upside near-term"),
    ("MSFT","Zacks","Jul-25","Hold","$500","$410","+22%","Azure AI momentum but valuation stretched"),
    ("META","多个机构","Jul-25","Buy","$650","$520","+25%","AI ad targeting; Llama ecosystem expansion"),
    ("AMZN","TradeStation","Jul-25","Buy","$240","$190","+26%","AWS AI services; 广告 revenue acceleration"),
    ("PLTR","Multiple","Jul-25","Speculative Buy","$160","$120","+33%","AIP platform; DoD contracts momentum"),
    ("ARM", "多个机构","Jul-25","Hold","$180","$140","+29%","Device AI trend but high valuation risk"),
]

for i, row_data in enumerate(signals):
    r = 4 + i
    for col, val in enumerate(row_data, start=1):
        c = ws4.cell(r, col, val)
        c.font = body_font(bold=(col in (1, 4)))
        c.border = make_border()
        if col == 4:
            ws4.cell(r, col).fill = make_fill(LTGRAY)
    ws4.row_dimensions[r].height = 18

# Column widths
for i, w in enumerate([8, 16, 10, 14, 13, 13, 11, 42], start=1):
    ws4.column_dimensions[get_column_letter(i)].width = w

# ══════════════════════════════════════════════════════════════════════════════
# SHEET 5 – Education / Strategy
# ══════════════════════════════════════════════════════════════════════════════
ws5 = wb.create_sheet("Strategy Guide")
ws5.sheet_view.showGridLines = False

ws5.merge_cells("A1:D1")
ws5["A1"] = "📚  PROJECT X – INVESTMENT STRATEGY & LEARNING GUIDE"
ws5["A1"].font = Font(name="Calibri", size=14, bold=True, color=WHITE)
ws5["A1"].fill = make_fill(NAVY)
ws5["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws5.row_dimensions[1].height = 36

strategy = [
    ("🎯 OBJECTIVE", "Learn fundamental & technical analysis through hands-on simulated trading on AI/Tech stocks. Build intuition without risking real capital."),
    ("📖 CORE PRINCIPLES", "1. Never invest money you can't afford to lose (even simulated – treat it seriously)\n2. Always document your thesis before entering a position\n3. Review weekly – what worked, what didn't, why\n4. Diversify across AI value chain: Hardware (NVDA/AMD) + Software (MSFT/GOOGL) + Application (META/PLTR)"),
    ("📊 ANALYSIS FRAMEWORK", "MACRO → Which macro factors drive the sector right now?\nFUNDAMENTAL → Revenue growth, margins, guidance\nTECHNICAL → Support/resistance, trend, volume\nSENTIMENT → Analyst tone, positioning, news flow\nRISK/REWARD → Does the upside justify the downside?"),
    ("⚠️ RED FLAGS TO WATCH", "- Management changing guidance downward\n- Unexpected chip export restrictions\n- AI monetization slower than expected\n- Competition eroding moat (e.g., custom silicon by GOOGL/AMZN)\n- Regulatory / antitrust actions"),
    ("🟢 GREEN FLAGS TO WATCH", "+ Beats on AI revenue metrics\n+ New customer wins in AI infrastructure\n+ Positive AI policy environment\n+ Partnerships expanding AI ecosystem\n+ Expanding margins from AI cost savings"),
    ("📋 DAILY ROUTINE", "1. Check overnight macro news (Fed speakers, economic data)\n2. Review pre-market futures and sector sentiment\n3. Open positions – any news catalyst today?\n4. Check earnings calendar for this week\n5. End of day: log prices, update tracker, review thesis"),
    ("📈 POSITION SIZING", "No single stock > 25% of portfolio\nNo single sector > 60% of portfolio\nKeep 10–20% cash dry powder for opportunities\nUse stop-losses if implementing real trading rules"),
]

for i, (title, content) in enumerate(strategy):
    r = 3 + i * 2
    ws5.merge_cells(f"A{r}:D{r}")
    ws5.cell(r, 1, title).font = Font(name="Calibri", size=11, bold=True, color=WHITE)
    ws5.cell(r, 1).fill = make_fill(STEEL)
    ws5.cell(r, 1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws5.row_dimensions[r].height = 22

    r2 = r + 1
    ws5.merge_cells(f"A{r2}:D{r2}")
    ws5.cell(r2, 1, content).font = body_font()
    ws5.cell(r2, 1).fill = make_fill(LTGRAY)
    ws5.cell(r2, 1).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True, indent=1)
    ws5.row_dimensions[r2].height = 80

for i, w in enumerate([25, 20, 20, 30], start=1):
    ws5.column_dimensions[get_column_letter(i)].width = w

# ══════════════════════════════════════════════════════════════════════════════
# Save
# ══════════════════════════════════════════════════════════════════════════════
out_path = r"C:\Users\fung2\.mavis\agents\mavis\workspace\project_x\ProjectX_Portfolio.xlsx"
wb.save(out_path)
print(f"Saved: {out_path}")
