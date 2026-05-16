"""
見積書PDF生成サービス

ReportLabを使用してサーバーサイドでA4縦1ページのPDFを直接生成します。
"""

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


def _register_japanese_font():
    """日本語フォントを登録する"""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        
        try:
            pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
            return "HeiseiKakuGo-W5"
        except Exception:
            logger.warning("HeiseiKakuGo-W5 font not available")
            try:
                pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
                return "HeiseiMin-W3"
            except Exception:
                logger.warning("Japanese fonts not available, using Helvetica")
                return "Helvetica"
    except Exception as e:
        logger.warning(f"Font registration error: {e}")
        return "Helvetica"


def generate_quotation_pdf(quotation, customer_display_name=None):
    """
    見積書PDFを生成して返す
    
    Args:
        quotation: Quotationオブジェクト
        customer_display_name: 顧客表示名
    
    Returns:
        bytes: PDFデータ
    """
    buffer = BytesIO()
    
    # A4サイズ (210 x 297 mm)
    width, height = A4
    
    # キャンバス作成
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # フォント登録
    font_name = _register_japanese_font()
    
    # 色定義
    navy_color = HexColor("#163a70")
    text_color = HexColor("#222222")
    border_color = HexColor("#cfd7e5")
    
    # 余白
    left_margin = 8 * mm
    right_margin = 8 * mm
    top_margin = 8 * mm
    
    # 実際の描画エリア
    content_width = width - left_margin - right_margin
    
    # y座標は上からの距離に変換（ReportLabは下が原点）
    def y_from_top(distance_from_top):
        return height - top_margin - distance_from_top
    
    # =============== ヘッダー ===============
    header_y = y_from_top(0)
    
    # 左側の濃紺バー
    bar_width = 3 * mm
    c.setFillColor(navy_color)
    c.rect(left_margin, header_y - 18 * mm, bar_width, 18 * mm, fill=1)
    
    # タイトル「見積書」
    title_x = left_margin + bar_width + 4 * mm
    c.setFont(font_name, 44)
    c.setFillColor(navy_color)
    c.drawString(title_x, header_y - 12 * mm, "見積書")
    
    # サブタイトル
    c.setFont(font_name, 9)
    c.setFillColor(text_color)
    c.drawString(title_x, header_y - 16 * mm, "下記の通りお見積り申し上げます。")
    
    # 右上：発行日、見積No、改定No
    right_x = left_margin + content_width - 50 * mm
    
    c.setFont(font_name, 8)
    c.setFillColor(text_color)
    
    date_str = quotation.created_at.strftime("%Y年%m月%d日") if quotation.created_at else "-"
    quotation_no = quotation.quotation_no or "-"
    revision_no = str(quotation.revision_no or 0)
    
    c.drawString(right_x, header_y - 10 * mm, "発行日：")
    c.drawString(right_x + 25 * mm, header_y - 10 * mm, date_str)
    
    c.drawString(right_x, header_y - 13 * mm, "見積No.：")
    c.drawString(right_x + 25 * mm, header_y - 13 * mm, quotation_no)
    
    c.drawString(right_x, header_y - 16 * mm, "改定No.：")
    c.drawString(right_x + 25 * mm, header_y - 16 * mm, revision_no)
    
    # ヘッダー下の線
    header_line_y = header_y - 18 * mm - 1 * mm
    c.setStrokeColor(navy_color)
    c.setLineWidth(2)
    c.line(left_margin, header_line_y, left_margin + content_width, header_line_y)
    
    # =============== 顧客情報＆自社情報 ===============
    content_start_y = header_line_y - 3 * mm
    
    # 左側：顧客情報
    customer_area_x = left_margin
    customer_area_width = 90 * mm
    
    # お客様ラベル
    c.setFillColor(navy_color)
    c.rect(customer_area_x, content_start_y - 4 * mm, customer_area_width, 4 * mm, fill=1)
    c.setFont(font_name, 9)
    c.setFillColor(white)
    c.drawString(customer_area_x + 2 * mm, content_start_y - 3.2 * mm, "お客様")
    
    # 顧客ボックス
    customer_box_y = content_start_y - 4 * mm - 1 * mm
    customer_box_height = 12 * mm
    c.setStrokeColor(navy_color)
    c.setLineWidth(1)
    c.rect(customer_area_x, customer_box_y - customer_box_height, customer_area_width, customer_box_height)
    
    c.setFont(font_name, 11)
    c.setFillColor(navy_color)
    c.drawString(customer_area_x + 2 * mm, customer_box_y - 3 * mm, customer_display_name or "-")
    
    c.setFont(font_name, 7)
    c.setFillColor(text_color)
    c.drawString(customer_area_x + 2 * mm, customer_box_y - 5.5 * mm, "ご担当")
    
    c.setFont(font_name, 8)
    contact_name = quotation.contact_name or "ご担当者様"
    c.drawString(customer_area_x + 2 * mm, customer_box_y - 7.5 * mm, contact_name)
    
    # 条件情報（2列）
    conditions_start_y = customer_box_y - customer_box_height - 1 * mm
    conditions = [
        ("件名", quotation.project_name or "-"),
        ("支払条件", quotation.payment_terms or "-"),
        ("納期", quotation.delivery_date or "-"),
        ("引渡場所", quotation.delivery_terms or "-"),
        ("有効期限", quotation.valid_until or "-"),
    ]
    
    col1_x = customer_area_x
    col2_x = customer_area_x + customer_area_width / 2
    
    for i in range(0, len(conditions), 2):
        y = conditions_start_y - (i // 2) * 3.5 * mm
        
        # 左側
        label1, value1 = conditions[i]
        c.setFont(font_name, 6)
        c.setFillColor(HexColor("#666666"))
        c.drawString(col1_x, y, label1)
        c.setFont(font_name, 8)
        c.setFillColor(text_color)
        c.drawString(col1_x, y - 2 * mm, value1)
        
        # 右側
        if i + 1 < len(conditions):
            label2, value2 = conditions[i + 1]
            c.setFont(font_name, 6)
            c.setFillColor(HexColor("#666666"))
            c.drawString(col2_x, y, label2)
            c.setFont(font_name, 8)
            c.setFillColor(text_color)
            c.drawString(col2_x, y - 2 * mm, value2)
    
    # 右側：自社情報
    company_area_x = customer_area_x + customer_area_width + 8 * mm
    company_area_width = content_width - customer_area_width - 8 * mm
    company_text_y = content_start_y
    
    # ロゴ試行
    logo_path = os.path.join(os.path.dirname(__file__), "../../static/img/musashi-logo.png")
    if os.path.exists(logo_path):
        try:
            from PIL import Image
            img = Image.open(logo_path)
            img_width = 20 * mm
            img_height = img_width * img.height / img.width
            c.drawImage(logo_path, company_area_x, company_text_y - img_height, width=img_width, height=img_height)
            company_text_y = company_text_y - img_height - 2 * mm
        except Exception as e:
            logger.warning(f"Failed to draw logo: {e}")
    
    # 会社情報
    c.setFont(font_name, 9)
    c.setFillColor(navy_color)
    c.drawString(company_area_x, company_text_y, "武蔵精密工業株式会社")
    
    c.setFont(font_name, 8)
    c.setFillColor(text_color)
    company_lines = [
        "Smart Industry営業グループ",
        "〒441-8560",
        "愛知県豊橋市植田町字大膳39-5",
        "TEL：0532-25-8111",
    ]
    
    for i, line in enumerate(company_lines):
        y = company_text_y - (i + 1) * 2.5 * mm
        c.drawString(company_area_x, y, line)
    
    # =============== 合計金額帯 ===============
    total_area_y = conditions_start_y - 35 * mm
    total_area_height = 8 * mm
    
    c.setFillColor(navy_color)
    c.rect(left_margin, total_area_y - total_area_height, content_width, total_area_height, fill=1)
    
    c.setFont(font_name, 11)
    c.setFillColor(white)
    c.drawString(left_margin + 3 * mm, total_area_y - 5.5 * mm, "合計金額")
    
    total_amount = quotation.total_amount or 0
    amount_str = f"¥{total_amount:,}"
    c.setFont(font_name, 24)
    c.drawString(left_margin + 60 * mm, total_area_y - 6 * mm, amount_str)
    
    c.setFont(font_name, 7)
    c.drawString(left_margin + content_width - 60 * mm, total_area_y - 5.5 * mm, "※本見積金額に消費税は含まれておりません")
    
    # =============== 明細テーブル ===============
    details_start_y = total_area_y - 5 * mm
    table_y = details_start_y
    
    # ヘッダー
    c.setFont(font_name, 8)
    c.setFillColor(navy_color)
    c.rect(left_margin, table_y - 4 * mm, content_width, 4 * mm, fill=1)
    
    c.setFillColor(white)
    headers = ["No.", "品名・仕様", "数量", "単位", "単価", "金額"]
    col_widths = [10 * mm, 70 * mm, 12 * mm, 12 * mm, 30 * mm, 30 * mm]
    x_pos = left_margin
    for header, col_width in zip(headers, col_widths):
        c.drawString(x_pos + 1 * mm, table_y - 3 * mm, header)
        x_pos += col_width
    
    # テーブル本体
    table_y -= 4 * mm
    c.setLineWidth(0.5)
    c.setStrokeColor(border_color)
    
    detail_count = 0
    if quotation.quotation_details:
        for detail in quotation.quotation_details[:15]:
            detail_count += 1
            table_y -= 3 * mm
            c.setFont(font_name, 7)
            c.setFillColor(text_color)
            
            c.rect(left_margin, table_y - 2.5 * mm, content_width, 3 * mm)
            
            x_pos = left_margin
            col_data = [
                str(detail_count),
                (detail.product_name or "-")[:40],
                str(int(detail.quantity or 0)),
                detail.unit or "式",
                f"¥{int(detail.unit_price or 0):,}",
                f"¥{int(detail.total_price or 0):,}"
            ]
            
            for idx, (data, col_width) in enumerate(zip(col_data, col_widths)):
                if idx >= 4:  # 単価・金額は右寄せ
                    c.drawRightString(x_pos + col_width - 1 * mm, table_y - 1.5 * mm, data)
                elif idx == 0 or idx >= 2:  # No.・数量・単位は中央
                    c.drawCentredString(x_pos + col_width / 2, table_y - 1.5 * mm, data)
                else:  # 品名は左寄せ
                    c.drawString(x_pos + 1 * mm, table_y - 1.5 * mm, data)
                x_pos += col_width
    
    # 空行で15行まで
    while detail_count < 15:
        detail_count += 1
        table_y -= 3 * mm
        c.rect(left_margin, table_y - 2.5 * mm, content_width, 3 * mm)
    
    # =============== 小計・合計 ===============
    summary_y = table_y - 4 * mm
    
    c.setFont(font_name, 8)
    c.setFillColor(text_color)
    
    subtotal = quotation.subtotal or quotation.total_amount or 0
    c.drawString(left_margin + content_width - 50 * mm, summary_y, "小計")
    c.drawRightString(left_margin + content_width, summary_y, f"¥{int(subtotal):,}")
    
    if quotation.discount_amount:
        summary_y -= 3 * mm
        c.drawString(left_margin + content_width - 50 * mm, summary_y, "値引き額")
        c.drawRightString(left_margin + content_width, summary_y, f"-¥{int(quotation.discount_amount):,}")
    
    summary_y -= 4 * mm
    total_box_height = 6 * mm
    c.setFillColor(navy_color)
    c.rect(left_margin + content_width - 50 * mm, summary_y - total_box_height, 50 * mm, total_box_height, fill=1)
    
    c.setFont(font_name, 9)
    c.setFillColor(white)
    c.drawString(left_margin + content_width - 48 * mm, summary_y - 4 * mm, "合計金額")
    c.drawRightString(left_margin + content_width - 2 * mm, summary_y - 4 * mm, f"¥{int(quotation.total_amount or 0):,}")
    
    # =============== 備考欄 ===============
    remarks_y = summary_y - 8 * mm
    remarks_height = 35 * mm
    
    c.setStrokeColor(navy_color)
    c.setLineWidth(1)
    c.rect(left_margin, remarks_y - remarks_height, content_width, remarks_height)
    
    c.setFont(font_name, 9)
    c.setFillColor(navy_color)
    c.drawString(left_margin + 3 * mm, remarks_y - 3 * mm, "備考")
    
    c.setFillColor(navy_color)
    c.circle(left_margin + 1.5 * mm, remarks_y - 2 * mm, 1.5, fill=1)
    
    remarks_text = quotation.remarks or "-"
    c.setFont(font_name, 8)
    c.setFillColor(text_color)
    
    remarks_lines = remarks_text.split("\n")
    remarks_text_y = remarks_y - 6 * mm
    for line in remarks_lines[:4]:
        c.drawString(left_margin + 3 * mm, remarks_text_y, line[:60])
        remarks_text_y -= 2.5 * mm
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
