import os
import fitz
from PIL import Image
import requests
import json
import re
import shutil
import logging
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 配置文件
load_dotenv()

# 配置日志
log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)

# 创建 logger - 检查是否已配置过，避免重复添加 handler
logger = logging.getLogger("批件处理")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # 防止日志传播到根 logger

# 日期字段列表（需要统一格式化为 YYYY-MM-DD）
DATE_FIELDS = ["申请时间", "受理时间", "批准日期", "有效期", "到期时间"]

def normalize_date(date_str):
    """将日期字符串统一格式化为 YYYY-MM-DD 格式"""
    if not date_str or date_str == "N/A":
        return date_str

    # 支持的格式: 2025年11月13日, 2025/11/13, 2025.11.13, 2025-11-13
    patterns = [
        r'(\d{4})年(\d{1,2})月(\d{1,2})日',  # 中文格式
        r'(\d{4})[/.](\d{1,2})[/.](\d{1,2})',  # 斜杠/点格式
        r'(\d{4})-(\d{1,2})-(\d{1,2})'  # 已经是标准格式
    ]

    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            year = match.group(1)
            month = match.group(2).zfill(2)  # 补零
            day = match.group(3).zfill(2)  # 补零
            return f"{year}-{month}-{day}"

    # 无法解析的格式，返回原值
    return date_str

# 只在没有 handler 时才添加（避免多次调用时重复添加）
if not logger.handlers:
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
    logger.addHandler(file_handler)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

TEXTIN_APP_ID = os.getenv("TEXTIN_APP_ID")
TEXTIN_SECRET_CODE = os.getenv("TEXTIN_SECRET_CODE")
LLM_API_KEY = os.getenv("LLM_API_KEY")

LLM_API_URL = os.getenv("LLM_API_URL")

LLM_MODEL = os.getenv("LLM_MODEL")

TARGET_FIELDS = [
    "产品名称", "文件标题", "规格", "剂型", "申请事项", "注册/药品分类", "申请人",
    "生产企业", "生产地址", "上市许可持有人", "申请号", "受理号", "批件号",
    "审批结论", "药品批准文号", "药品标准编号", "申请时间", "受理时间", "批准日期", "有效期", "到期时间"
]

def extract_textin_ocr(filepath):
    """使用 TextIn OCR 提取 PDF 文本"""
    logger.info(f"[OCR处理] 开始提取 PDF 文本: {os.path.basename(filepath)}")

    with open(filepath, "rb") as f:
        file_content = f.read()

    params = {"dpi": "144", "page_count": "10", "parse_mode": "scan"}
    headers = {
        "x-ti-app-id": TEXTIN_APP_ID,
        "x-ti-secret-code": TEXTIN_SECRET_CODE,
        "Content-Type": "application/octet-stream"
    }

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[OCR请求] 正在调用 TextIn API (尝试 {attempt}/{max_retries})...")
            response = requests.post(
                "https://api.textin.com/ai/service/v1/pdf_to_markdown",
                params=params,
                headers=headers,
                data=file_content,
                timeout=60
            )
            response.raise_for_status()
            result = json.loads(response.text)
            markdown_text = result["result"]["markdown"]

            text_length = len(markdown_text)
            logger.info(f"[OCR完成] 成功提取 {text_length} 字符文本")
            return markdown_text
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                logger.warning(f"[OCR警告] TextIn API 请求超时，准备重试 ({attempt}/{max_retries})...")
                continue
            logger.error(f"[OCR错误] TextIn API 请求超时 (已重试 {max_retries} 次)")
            return ""
        except json.JSONDecodeError as e:
            logger.error(f"[OCR错误] JSON 解析失败: {e}")
            logger.error(f"[OCR错误] 响应内容: {response.text[:500]}")
            return ""
        except Exception as e:
            logger.error(f"[OCR错误] 处理失败: {e}")
            return ""

def call_llm(prompt_text, batch_index=1, total_batches=1):
    """调用大模型 API 提取结构化数据（OpenAI 协议）"""
    # OpenAI 协议 API
    # LLM_API_URL: https://ark.cn-beijing.volces.com/api/coding/v3
    # 端点: /chat/completions
    api_endpoint = LLM_API_URL.rstrip('/') + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "你是一个严谨的数据提取机器人。严格按照要求的格式输出，不要有任何多余的解释文字。"},
            {"role": "user", "content": prompt_text}
        ],
        "max_tokens": 2048,
        "temperature": 0.1
    }

    try:
        logger.info(f"[LLM请求] 批次 {batch_index}/{total_batches} - 正在调用大模型 API (模型: {LLM_MODEL})...")
        logger.info(f"[LLM请求] API 端点: {api_endpoint}")
        logger.info(f"[LLM请求] 请求头: Authorization: Bearer {LLM_API_KEY[:10]}...")

        response = requests.post(api_endpoint, headers=headers, json=data, timeout=120)
        logger.info(f"[LLM请求] 响应状态码: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"[LLM请求] 请求失败，响应内容: {response.text[:1000]}")

        response.raise_for_status()
        result = response.json()
        logger.debug(f"[LLM响应] 原始响应: {result}")

        # 尝试解析 OpenAI 协议响应
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            logger.info(f"[LLM完成] 使用 OpenAI 协议解析，提取内容长度: {len(content)} 字符")
            return content
        elif "content" in result:
            content = result["content"][0]["text"]
            logger.info(f"[LLM完成] 使用 Anthropic 协议解析，提取内容长度: {len(content)} 字符")
            return content
        else:
            logger.error(f"[LLM错误] 无法解析响应格式: {result}")
            return ""

    except requests.exceptions.Timeout:
        logger.error(f"[LLM错误] 大模型 API 请求超时 (超时时间: 120秒)")
        return ""
    except json.JSONDecodeError as e:
        logger.error(f"[LLM错误] JSON 解析失败: {e}")
        logger.error(f"[LLM错误] 响应内容: {response.text[:1000]}")
        return ""
    except KeyError as e:
        logger.error(f"[LLM错误] 响应字段缺失: {e}")
        logger.error(f"[LLM错误] 响应内容: {result}")
        return ""
    except Exception as e:
        logger.error(f"[LLM错误] 处理失败: {e}")
        return ""

def create_pdf_pages(old_pdfpath, new_pdfpath, page_list, log_prefix=""):
    """从原 PDF 中提取指定页面"""
    if not page_list:
        return

    logger.debug(f"[PDF操作] {log_prefix}创建 PDF: {os.path.basename(new_pdfpath)} (页面: {page_list})")

    pdf = fitz.open(old_pdfpath)
    new_pdf = fitz.open()
    for p in page_list:
        if 1 <= p <= len(pdf):
            new_pdf.insert_pdf(pdf, from_page=p-1, to_page=p-1)
    new_pdf.save(new_pdfpath)
    pdf.close()
    new_pdf.close()

    file_size = os.path.getsize(new_pdfpath)
    logger.debug(f"[PDF操作] {log_prefix}PDF 创建完成，文件大小: {file_size} 字节")

def process_single_file(filepath, output_folder):
    """处理单个文件并返回数据库记录列表"""
    logger.info("=" * 80)
    logger.info(f"[文件处理] 开始处理文件: {os.path.basename(filepath)}")
    logger.info(f"[文件基本信息] 文件路径: {filepath}")

    # 打开 PDF 获取基本信息
    try:
        doc = fitz.open(filepath)
        total_pages = len(doc)
        file_size = os.path.getsize(filepath)
        doc.close()

        logger.info(f"[文件基本信息] 总页数: {total_pages} 页, 文件大小: {file_size} 字节")
    except Exception as e:
        logger.error(f"[文件错误] 无法打开 PDF 文件: {e}")
        return []

    projects = []
    current_proj = None
    main_doc_count = 0

    # 拆分逻辑 - 先并行提取所有页面的 OCR，再构建项目

    # 步骤1: 只对第一页进行 OCR（第一页是批件，后续页面是附件，仅需保存PDF）
    logger.info(f"[OCR处理] 开始提取第 1 页文本（批件页）...")
    page_texts = {}

    # 提取第一页并 OCR
    temp_pdf = os.path.join(output_folder, "temp_1.pdf")
    create_pdf_pages(filepath, temp_pdf, [1], log_prefix=f"[页面 1/{total_pages}] ")
    page_texts[1] = extract_textin_ocr(temp_pdf)
    if os.path.exists(temp_pdf):
        os.remove(temp_pdf)

    logger.info(f"[OCR完成] 第一页文本提取完成，后续页面作为附件无需 OCR")

    # 步骤2: 简化拆分逻辑 - 第一页作为主文件，后续页面作为附件
    # 构建单个项目
    first_page_text = page_texts.get(1, "")
    doc_title = "批件"  # 默认标题

    # 尝试从第一页提取标题
    header_text = first_page_text[:1000].replace(" ", "").replace("\n", "")
    title_pattern = r'(药物临床试验批件|临床试验批件|药品补充申请批件|补充申请批件|药品注册证书|注册证书|药品再注册批件|再注册批件|药品再注册批准通知书|再注册批准通知书|审批意见通知件|药物临床试验批准通知书|临床试验通知书|备案信息|备案公示|批件|通知书|通知件)'
    is_title = re.search(title_pattern, header_text)
    if is_title:
        doc_title = is_title.group(1)
        logger.debug(f"[页面 1] 匹配到标题类型: {doc_title}")

    # 构建项目：第一页为主文件，后续页面为附件
    current_proj = {
        "标题": doc_title,
        "主页码": [1],
        "附件页码": list(range(2, total_pages + 1)) if total_pages > 1 else [],
        "主文本": first_page_text
    }
    projects.append(current_proj)

    main_doc_count = 1
    logger.info(f"[批件识别] 第 {main_doc_count} 个主文档，标题: {doc_title} (页面 1)")
    if current_proj["附件页码"]:
        logger.info(f"[附件识别] 附件页码: {current_proj['附件页码']}")

    logger.info(f"[文档拆分] 完成，共识别 {len(projects)} 个批件项目")

    # 提取及文件生成逻辑
    records = []
    pdf_name_no_ext = os.path.splitext(os.path.basename(filepath))[0]
    pdf_root_folder = os.path.join(output_folder, pdf_name_no_ext)
    os.makedirs(pdf_root_folder, exist_ok=True)

    logger.info("[数据提取] 开始提取批件信息...")

    for idx, proj in enumerate(projects, 1):
        if not proj["主页码"]:
            logger.warning(f"[跳过] 项目 {idx} 无主页码")
            continue

        logger.info(f"[数据提取] 处理项目 {idx}/{len(projects)} - {proj['标题']} (主页码: {proj['主页码']})")

        # 构建提示词
        prompt = f"请从以下医药批件文本中，严格提取 21 个字段。如果没有对应信息输出 'N/A'。\n格式必须完全如下：\n" + \
                 "\n".join([f"{f}:[提取内容]" for f in TARGET_FIELDS]) + f"\n\n批件文本：\n{proj['主文本']}\n\n" + \
                 f"注意：\n1. 请根据理解【批准日期】和【有效期】字段计算【到期时间】。\n2. 所有日期字段（申请时间、受理时间、批准日期、有效期、到期时间）请统一格式化为 YYYY-MM-DD 格式，例如 2025-11-13。" 
                
        # 调用大模型
        llm_res = call_llm(prompt, batch_index=idx, total_batches=len(projects)).replace('：', ':')

        if not llm_res:
            logger.error(f"[数据提取] 项目 {idx} 大模型返回空结果，跳过")
            continue

        logger.debug(f"[LLM响应] 原始内容:\n{llm_res}")

        # 解析结果
        record_data = {}
        for field in TARGET_FIELDS:
            match = re.search(rf"{field}:(.+)", llm_res)
            value = match.group(1).strip() if match else ""
            # 空内容转为 N/A
            record_data[field] = value if value else "N/A"

        # 统一日期字段格式为 YYYY-MM-DD
        for field in DATE_FIELDS:
            if field in record_data:
                record_data[field] = normalize_date(record_data[field])

        # 检查是否有有效内容
        has_content = any(v != "N/A" and v.strip() != "" for k, v in record_data.items() if k != "文件标题")

        if not has_content:
            logger.warning(f"[数据提取] 项目 {idx} 未提取到有效数据，跳过")
            continue

        # 生成文件名
        p_name = record_data.get("产品名称", "未知产品").replace("/", "_")
        if p_name == "N/A":
            p_name = "未知产品"
        f_title = record_data.get("文件标题", proj["标题"]).replace("/", "_")
        if f_title == "N/A":
            f_title = proj["标题"]

        main_pdf_filename = f"{p_name}-{f_title}.pdf"
        main_pdf_path = os.path.join(pdf_root_folder, main_pdf_filename)
        create_pdf_pages(filepath, main_pdf_path, proj["主页码"], log_prefix=f"[主文档] ")

        logger.info(f"[文件生成] 主文档 PDF: {main_pdf_filename}")

        attach_pdf_path = ""
        if proj["附件页码"]:
            attach_pdf_path = os.path.join(pdf_root_folder, f"{p_name}-附件.pdf")
            create_pdf_pages(filepath, attach_pdf_path, proj["附件页码"], log_prefix=f"[附件] ")
            logger.info(f"[文件生成] 附件 PDF: {os.path.basename(attach_pdf_path)} (页码: {proj['附件页码']})")

        # 保存记录
        record_data["main_file_path"] = main_pdf_path
        record_data["attach_file_path"] = attach_pdf_path

        # 记录提取的详细信息
        logger.info(f"[数据提取] 项目 {idx} 提取成功:")
        logger.info(f"  - 产品名称: {record_data.get('产品名称', 'N/A')}")
        logger.info(f"  - 文件标题: {record_data.get('文件标题', 'N/A')}")
        logger.info(f"  - 规格: {record_data.get('规格', 'N/A')}")
        logger.info(f"  - 剂型: {record_data.get('剂型', 'N/A')}")
        logger.info(f"  - 申请人: {record_data.get('申请人', 'N/A')}")
        logger.info(f"  - 批件号: {record_data.get('批件号', 'N/A')}")
        logger.info(f"  - 批准日期: {record_data.get('批准日期', 'N/A')}")

        records.append(record_data)

    logger.info(f"[文件处理] 完成处理文件: {os.path.basename(filepath)}，共提取 {len(records)} 条有效记录")
    logger.info("=" * 80)

    return records
