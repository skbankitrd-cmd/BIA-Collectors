from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import uuid
from datetime import datetime

class PDFExporter:
    """原子化 PDF 導出器：全系統統一 PDF 規範"""
    
    def __init__(self):
        self.output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../BIA-Web-Solution/server/public/generated_reports"))
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 字體處理 (MacOS 內建黑體，確保繁體中文不亂碼)
        # 注意：實際部署時應包含字體檔或使用環境內建路徑
        font_paths = [
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Microsoft/Arial Unicode.ttf"
        ]
        
        self.font_name = 'Helvetica'
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont('CustomFont', fp))
                    self.font_name = 'CustomFont'
                    break
                except:
                    continue

    def export(self, data: list, report_title: str) -> str:
        """將資料轉為 PDF"""
        file_name = f"PDF_{report_title}_{uuid.uuid4().hex[:4]}.pdf"
        full_path = os.path.join(self.output_dir, file_name)
        
        c = canvas.Canvas(full_path, pagesize=A4)
        width, height = A4
        
        # 標題
        c.setFont(self.font_name, 18)
        c.drawCentredString(width/2, height - 1*inch, report_title)
        
        # 頁首資訊
        c.setFont(self.font_name, 10)
        c.drawString(1*inch, height - 1.3*inch, f"產出日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        c.line(1*inch, height - 1.4*inch, width - 1*inch, height - 1.4*inch)
        
        # 內容
        y = height - 1.8*inch
        c.setFont(self.font_name, 12)
        
        for item in data:
            if y < 1*inch:
                c.showPage()
                y = height - 1*inch
                c.setFont(self.font_name, 12)
            
            # 簡單序列化顯示內容摘要
            text = str(item)
            c.drawString(1*inch, y, f"• {text[:75]}...")
            y -= 0.3*inch
            
        c.save()
        return f"/public/generated_reports/{file_name}"
