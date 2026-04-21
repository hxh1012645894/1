from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import List
import os
import shutil
from PIL import Image
import logging
from datetime import datetime, date
import calendar
import re
import asyncio
from collections import defaultdict
from dotenv import load_dotenv

# 加载 .env 配置文件
load_dotenv()

# 配置日志
log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("批件处理")
logger.setLevel(logging.DEBUG)

# 文件处理器
file_handler = logging.FileHandler(
    os.path.join(log_dir, f"processing_{datetime.now().strftime('%Y%m%d')}.log"),
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_format = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_format)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(console_format)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 引入核心处理函数
from processor import process_single_file

app = FastAPI(title="注册管理平台 API")

# 配置 CORS，允许 Vue 前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 数据库配置 (SQLite) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./records.db?journal_mode=WAL&synchronous=NORMAL"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ApprovalRecord(Base):
    __tablename__ = "approval_records"
    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String)
    file_title = Column(String)
    specification = Column(String)
    dosage = Column(String)
    application = Column(String)
    registration_class = Column(String)
    applicant = Column(String)
    enterprise = Column(String)
    address = Column(String)
    owner = Column(String)
    apply_no = Column(String)
    handle_no = Column(String)
    approval_no = Column(String)
    conclusion = Column(Text)
    drug_approval_no = Column(String)
    drug_standard_no = Column(String)
    apply_time = Column(String)
    handle_time = Column(String)
    approval_date = Column(String)
    validity = Column(String)
    expiry_date = Column(String)  # 新增：到期时间
    main_file_path = Column(String)
    attach_file_path = Column(String)

Base.metadata.create_all(bind=engine)

# --- 目录配置 ---
UPLOAD_DIR = os.path.abspath("./uploads")
PROCESSED_DIR = os.path.abspath("./processed")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# --- WebSocket 配置 ---
class ConnectionManager:
    """WebSocket 连接管理器"""
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.connection_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.connection_lock:
            self.active_connections.append(websocket)
        logger.info(f"[WebSocket] 新连接建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"[WebSocket] 连接断开，当前连接数: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        if not self.active_connections:
            return
        message_json = asyncio.create_task(asyncio.to_thread(lambda: __import__('json').dumps(message, ensure_ascii=False)))
        await message_json
        data = message_json.result()

        # 复制连接列表以避免遍历时修改
        async with self.connection_lock:
            connections = self.active_connections.copy()

        for connection in connections:
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.error(f"[WebSocket] 发送消息失败: {e}")

manager = ConnectionManager()

# --- 服务配置 ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))

logger.info(f"[服务启动] API 服务初始化完成")
logger.info(f"[服务配置] 上传目录: {UPLOAD_DIR}")
logger.info(f"[服务配置] 处理目录: {PROCESSED_DIR}")
logger.info(f"[服务配置] 数据库: records.db")
logger.info(f"[服务配置] WebSocket: ws://localhost:{PORT}/ws")

# --- API 路由 ---
@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...), background_tasks: BackgroundTasks = None):
    """处理批量上传的文件并入库（后台处理）"""
    logger.info("=" * 80)
    logger.info("[上传处理] 收到文件上传请求")
    logger.info(f"[上传处理] 上传文件数量: {len(files)}")

    # 立即返回响应，后台处理文件
    result = {
        "message": "文件已接收，开始后台处理",
        "file_count": len(files),
        "processing": True
    }

    # 将文件保存和处理放到后台任务
    if background_tasks is not None:
        background_tasks.add_task(process_files_background, files)

    logger.info("[上传处理] 已接收文件，后台处理已启动")
    logger.info("=" * 80)

    return result

async def process_files_background(files: List[UploadFile]):
    """后台处理上传的文件"""
    logger.info("[后台处理] 开始后台文件处理")

    db = SessionLocal()
    total_processed = 0
    failed_files = []

    try:
        for idx, file in enumerate(files, 1):
            logger.info(f"[后台处理] 处理第 {idx}/{len(files)} 个文件: {file.filename}")

            try:
                file_location = os.path.join(UPLOAD_DIR, file.filename)
                file_size = 0

                with open(file_location, "wb+") as file_object:
                    shutil.copyfileobj(file.file, file_object)
                    file_size = os.path.getsize(file_location)

                logger.info(f"[后台处理] 文件保存完成，大小: {file_size} 字节")

                # 如果是图片，套壳为PDF
                process_path = file_location
                is_converted = False
                if file.filename.lower().endswith(('.jpg', '.png', '.jpeg')):
                    is_converted = True
                    process_path = os.path.join(UPLOAD_DIR, f"{os.path.splitext(file.filename)[0]}.pdf")
                    logger.info(f"[后台处理] 检测到图片文件，正在转换为 PDF: {process_path}")

                    img = Image.open(file_location)
                    img.convert("RGB").save(process_path)

                    converted_size = os.path.getsize(process_path)
                    logger.info(f"[后台处理] PDF 转换完成，大小: {converted_size} 字节")

                # 提取核心数据
                logger.info(f"[后台处理] 开始进行批件信息提取...")
                records = process_single_file(process_path, PROCESSED_DIR)

                # 存入数据库
                inserted_count = 0
                for rec in records:
                    db_record = ApprovalRecord(
                        product_name=rec.get("产品名称"), file_title=rec.get("文件标题"),
                        specification=rec.get("规格"), dosage=rec.get("剂型"),
                        application=rec.get("申请事项"), registration_class=rec.get("注册分类"),
                        applicant=rec.get("申请人"), enterprise=rec.get("生产企业"),
                        address=rec.get("生产地址"), owner=rec.get("上市许可持有人"),
                        apply_no=rec.get("申请号"), handle_no=rec.get("受理号"),
                        approval_no=rec.get("批件号"), conclusion=rec.get("审批结论"),
                        drug_approval_no=rec.get("药品批准文号"), drug_standard_no=rec.get("药品标准编号"),
                        apply_time=rec.get("申请时间"), handle_time=rec.get("受理时间"),
                        approval_date=rec.get("批准日期"), validity=rec.get("有效期"),
                        expiry_date=rec.get("到期时间"),
                        main_file_path=rec.get("main_file_path"), attach_file_path=rec.get("attach_file_path")
                    )
                    db.add(db_record)
                    inserted_count += 1

                db.commit()
                total_processed += inserted_count

                if inserted_count > 0:
                    logger.info(f"[后台处理] 成功入库 {inserted_count} 条记录")
                else:
                    logger.warning(f"[后台处理] 未提取到有效数据，未入库任何记录")

            except Exception as e:
                logger.error(f"[后台处理] 文件 {file.filename} 处理失败: {e}")
                failed_files.append({"filename": file.filename, "error": str(e)})
                db.rollback()

        logger.info(f"[后台处理] 所有文件处理完成，总计入库: {total_processed} 条记录")

        # 广播数据更新通知
        logger.info(f"[WebSocket] 广播数据更新通知")
        await manager.broadcast({
            "type": "data_updated",
            "message": "新数据已入库",
            "count": total_processed,
            "timestamp": datetime.now().isoformat()
        })

    finally:
        db.close()

    # 返回结果用于日志记录
    logger.info(f"[后台处理] 处理完成：成功 {len(files) - len(failed_files)} 个，失败 {len(failed_files)} 个")

@app.get("/api/records")
def get_records():
    """获取所有台账记录"""
    logger.info("[查询处理] 获取所有批件记录")
    db = SessionLocal()
    try:
        records = db.query(ApprovalRecord).order_by(ApprovalRecord.id.desc()).all()
        logger.info(f"[查询处理] 共查询到 {len(records)} 条记录")
        return records
    except Exception as e:
        logger.error(f"[查询处理] 查询失败: {e}")
        return {"error": str(e)}
    finally:
        db.close()

@app.delete("/api/records/{record_id}")
def delete_record(record_id: int):
    """删除指定记录"""
    logger.info(f"[删除处理] 删除记录 ID: {record_id}")
    db = SessionLocal()
    try:
        record = db.query(ApprovalRecord).filter(ApprovalRecord.id == record_id).first()
        if record:
            # 删除相关文件
            if record.main_file_path and os.path.exists(record.main_file_path):
                os.remove(record.main_file_path)
            if record.attach_file_path and os.path.exists(record.attach_file_path):
                os.remove(record.attach_file_path)

            db.delete(record)
            db.commit()
            logger.info(f"[删除处理] 成功删除记录 ID: {record_id}")
            return {"message": "删除成功"}
        else:
            logger.warning(f"[删除处理] 记录 ID: {record_id} 不存在")
            return {"error": "记录不存在"}
    except Exception as e:
        logger.error(f"[删除处理] 删除失败: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

from pydantic import BaseModel

class RecordUpdate(BaseModel):
    product_name: str = None
    specification: str = None
    dosage: str = None
    validity: str = None
    expiry_date: str = None
    remark: str = None

@app.put("/api/records/{record_id}")
def update_record(record_id: int, record: RecordUpdate):
    """更新指定记录"""
    logger.info(f"[更新处理] 更新记录 ID: {record_id}")
    db = SessionLocal()
    try:
        db_record = db.query(ApprovalRecord).filter(ApprovalRecord.id == record_id).first()
        if not db_record:
            logger.warning(f"[更新处理] 记录 ID: {record_id} 不存在")
            return {"error": "记录不存在"}

        # 更新字段
        update_data = record.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(db_record, field, value)

        db.commit()
        db.refresh(db_record)
        logger.info(f"[更新处理] 成功更新记录 ID: {record_id}")

        # 广播数据更新通知
        logger.info(f"[WebSocket] 广播数据更新通知")
        import asyncio
        asyncio.create_task(manager.broadcast({
            "type": "data_updated",
            "message": "数据已更新",
            "count": 1,
            "timestamp": datetime.now().isoformat()
        }))

        return {"message": "更新成功", "data": db_record}
    except Exception as e:
        logger.error(f"[更新处理] 更新失败: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

def parse_date(date_str):
    """提取字符串中的日期，支持 '2025年11月13日' 或 '2025-11-13'"""
    match = re.search(r'(\d{4})[-年/.]\s*(\d{1,2})\s*[-月/.]\s*(\d{1,2})', str(date_str))
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None

def calculate_expiry(approval_date_str, validity_str):
    """计算到期日"""
    # 1. 如果有效期本身就是绝对日期 (如：有效期至2031年3月8日)
    abs_date = parse_date(validity_str)
    if abs_date:
        return abs_date

    # 2. 如果是相对日期 (如：24个月)，则用批准日期推算
    app_date = parse_date(approval_date_str)
    if app_date:
        m_match = re.search(r'(\d+)\s*个月', str(validity_str))
        if m_match:
            months = int(m_match.group(1))
            # 精确计算月份加法
            month = app_date.month - 1 + months
            year = app_date.year + month // 12
            month = month % 12 + 1
            day = min(app_date.day, calendar.monthrange(year, month)[1])
            return datetime(year, month, day)
    return None

@app.get("/api/stats")
def get_stats():
    """获取顶部卡片统计数据"""
    logger.info("[统计处理] 获取台账统计数据")
    db = SessionLocal()
    try:
        records = db.query(ApprovalRecord).all()
        logger.info(f"[统计处理] 共查询到 {len(records)} 条记录用于统计")

        unique_products = set()
        expiring_soon = 0
        expired = 0
        now = datetime.now()

        for r in records:
            if r.product_name and r.product_name != "N/A":
                unique_products.add(r.product_name)

            # 使用数据库中已计算的 expiry_date 字段
            # 如果到期时间为 N/A 或为空，则不参与计算
            if not r.expiry_date or r.expiry_date == "N/A":
                continue

            exp_date = parse_date(r.expiry_date)
            if exp_date:
                days_left = (exp_date - now).days
                if days_left < 0:
                    expired += 1
                elif days_left <= 365:
                    expiring_soon += 1

        stats = {
            "totalFiles": len(records),
            "totalProducts": len(unique_products),
            "expiringSoon": expiring_soon,
            "expired": expired
        }
        logger.info(f"[统计处理] 统计数据: {stats}")
        return stats
    except Exception as e:
        logger.error(f"[统计处理] 统计失败: {e}")
        return {"error": str(e)}
    finally:
        db.close()

@app.get("/api/preview")
def preview_file(path: str):
    """在线预览 PDF 文件"""
    logger.info(f"[预览处理] 请求预览文件: {path}")

    if os.path.exists(path):
        file_size = os.path.getsize(path)
        logger.info(f"[预览处理] 文件存在，大小: {file_size} 字节")
        return FileResponse(path, media_type="application/pdf")
    else:
        logger.warning(f"[预览处理] 文件不存在: {path}")
        return {"error": "文件不存在"}

@app.get("/api/health")
def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点 - 实时推送数据更新通知"""
    await manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息（用于心跳保持连接）
            data = await websocket.receive_text()
            # 可以处理客户端发送的指令，如：Heartbeat, RequestUpdate 等
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"[WebSocket] 连接异常: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    logger.info(f"[服务启动] 准备启动服务...")
    logger.info(f"[服务配置] 绑定地址: {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
