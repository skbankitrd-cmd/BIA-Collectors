import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB-Init")

def init_roles():
    """初始化 user_roles 表格"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        logger.error("未設置環境變數，請檢查 .env 檔案")
        return
        
    client: Client = create_client(url, key)
    
    roles = [
        {"role_name": "董事長", "description": "決策核心，關注總體策略與重大風險"},
        {"role_name": "法遵長", "description": "合規把關，關注金管會裁罰與法規更新"},
        {"role_name": "資訊長", "description": "技術引領，關注資安、金融科技與 AI 發展"},
        {"role_name": "營運長", "description": "業務推動，關注同業動態與市場營運"},
        {"role_name": "風險長", "description": "風險控管，關注信用、市場及營運風險"}
    ]
    
    for role in roles:
        try:
            # 檢查角色是否已存在
            response = client.table("user_roles").select("role_id").eq("role_name", role["role_name"]).execute()
            if len(response.data) == 0:
                client.table("user_roles").insert(role).execute()
                logger.info(f"已新增角色：{role['role_name']}")
            else:
                logger.info(f"角色已存在：{role['role_name']}")
        except Exception as e:
            logger.error(f"新增角色 {role['role_name']} 失敗: {e}")

if __name__ == "__main__":
    init_roles()
