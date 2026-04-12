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
        # TODO: 預打包常用繁體中文字體（如 Noto Sans TC），避免因作業系統環境差異導致的 PDF 渲染失敗
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
        try:
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
                if y < 1.5*inch: # 增加底部安全距離
                    c.showPage()
                    y = height - 1*inch
                    c.setFont(self.font_name, 12)
                
                # [Harness Fix] 智慧型內容解析
                content_text = ""
                if isinstance(item, dict):
                    # 如果是結構化資料，提取 title 與 summary
                    title = item.get('title', item.get('name', '未具名項目'))
                    summary = item.get('summary', item.get('content', str(item)))
                    content_text = f"【{title}】: {summary}"
                else:
                    content_text = str(item)

                # 分行處理 (防止長字串溢出 PDF 邊界)
                # 簡單截斷為多行
                max_chars = 60
                lines = [content_text[i:i+max_chars] for i in range(0, len(content_text), max_chars)]
                
                for line in lines[:5]: # 每筆最多顯示 5 行
                    c.drawString(1*inch, y, f" {line}")
                    y -= 0.25*inch
                y -= 0.15*inch # 項目間隔
                
            c.save()
            print(f"DEBUG_PDF_PATH:{full_path}") # 給後端抓取用
            return f"/public/generated_reports/{file_name}"
        except Exception as e:
            print(f"CRITICAL_PDF_ERROR:{str(e)}")
            return ""
