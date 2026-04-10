import pandas as pd
import os
import uuid
import logging
from datetime import datetime

logger = logging.getLogger("ReportGenerator")

class ReportGenerator:
    """金控專業報表生成引擎"""
    
    def __init__(self, output_base_dir: str = "generated_reports"):
        # 報表存放路徑 (網頁端可透過此路徑下載)
        self.output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../BIA-Web-Solution/server/public", output_base_dir))
        os.makedirs(self.output_dir, exist_ok=True)

    def create_excel(self, data: list, filename_prefix: str = "BIA_Report") -> str:
        """
        將二維資料轉為 Excel 檔案
        data 格式範例: [{"日期": "2024-03-01", "系統": "帳務", "狀態": "成功"}]
        """
        try:
            if not data:
                return ""

            df = pd.DataFrame(data)
            
            # 建立唯一檔名
            file_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"{filename_prefix}_{timestamp}_{file_id}.xlsx"
            file_path = os.path.join(self.output_dir, filename)

            # 使用 Pandas 寫入 Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Intelligence_Report')
                
                # 美化 Excel (設定欄寬與標題樣式)
                workbook = writer.book
                worksheet = writer.sheets['Intelligence_Report']
                
                for i, col in enumerate(df.columns):
                    # 自動調整欄寬
                    column_len = max(df[col].astype(str).str.len().max(), len(col) + 2)
                    worksheet.column_dimensions[chr(65+i)].width = min(column_len, 50)

            logger.info(f"✅ 報表已生成: {filename}")
            
            # 回傳相對 URL 供前端下載
            return f"/public/generated_reports/{filename}"
            
        except Exception as e:
            logger.error(f"❌ 生成報表失敗: {e}")
            return ""
