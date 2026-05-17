"""見積書PDF生成サービス - 正式日本語見積書レイアウト"""

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.utils import ImageReader
from datetime import datetime
from flask import current_app
import logging
import os

logger = logging.getLogger(__name__)

# 日本語フォント登録
def _register_japanese_fonts():
    """日本語フォント登録"""
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
        return "HeiseiKakuGo-W5"
    except Exception as e:
        logger.error(f"[PDF] Error registering Japanese fonts: {e}")
        return "Helvetica"

def _draw_musashi_logo(c, x, y, width=48*mm, height=None):
    """
    MUSASHIロゴを画像ファイルから埋め込む
    
    正式ロゴ画像をそのまま使用。
    アスペクト比を維持し、自然に配置する。
    
    Args:
        c: reportlab Canvas オブジェクト
        x: ロゴの左端 X座標
        y: ロゴの上端 Y座標
        width: ロゴ幅（デフォルト 48mm）
        height: ロゴ高さ（Noneの場合はアスペクト比を保つ）
    """
    # ロゴ画像パス
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'musashi-logo.png')
    
    if not os.path.exists(logo_path):
        # 画像がない場合はログのみ
        logger.warning(f"[PDF] Logo image not found: {logo_path}")
        return
    
    try:
        # 画像をImageReaderで読み込む
        img_reader = ImageReader(logo_path)
        img_width, img_height = img_reader.getSize()
        
        if img_width <= 0 or img_height <= 0:
            logger.warning(f"[PDF] Invalid image size: {img_width}x{img_height}")
            return
        
        # アスペクト比を計算
        aspect_ratio = img_height / img_width
        
        # 指定幅に合わせて高さを計算
        if height is None:
            height = width * aspect_ratio
        
        # 画像を配置（x, y は左上座標）
        c.drawImage(
            logo_path,
            x,
            y - height,  # 上端から高さ分下がった位置が底辺
            width=width,
            height=height,
            preserveAspectRatio=True,
            mask='auto'
        )
    except Exception as e:
        logger.error(f"[PDF] Error drawing logo image: {e}", exc_info=True)

def generate_quotation_pdf(quotation, customer_display_name=None):
    """正式日本語見積書PDF生成"""
    
    buffer = BytesIO()
    width, height = A4  # 210mm x 297mm
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # 日本語フォント登録
    font_name = _register_japanese_fonts()
    
    # 色定義
    navy = HexColor("#163a70")
    navy_light = HexColor("#4a7ba7")
    border = HexColor("#cfd7e5")
    text_color = HexColor("#222222")
    red = HexColor("#E31A24")
    
    # 余白
    left_margin = 8 * mm
    right_margin = 8 * mm
    top_margin = 8 * mm
    bottom_margin = 8 * mm
    
    page_width = width - left_margin - right_margin
    
    # ========================================
    # 1. ヘッダー（見積書タイトル + 右上情報）
    # ========================================
    y_pos = height - top_margin
    header_end_y = y_pos - 20*mm
    
    # 左側：濃紺バー + 「見積書」タイトル
    c.setFillColor(navy)
    c.rect(left_margin, header_end_y, 3*mm, y_pos - header_end_y, fill=1, stroke=0)
    
    c.setFont(font_name, 40)
    c.setFillColor(navy)
    c.drawString(left_margin + 6*mm, y_pos - 12*mm, "見積書")
    
    c.setFont(font_name, 8.5)
    c.setFillColor(text_color)
    c.drawString(left_margin + 6*mm, y_pos - 18*mm, "下記の通りお見積り申し上げます。")
    
    # 右側：発行日、見積No、改定No
    c.setFont(font_name, 8)
    c.setFillColor(text_color)
    
    issued_date = quotation.created_at.strftime("%Y年%m月%d日") if quotation.created_at else "日付なし"
    c.drawRightString(width - right_margin, y_pos - 5*mm, f"発行日：{issued_date}")
    c.drawRightString(width - right_margin, y_pos - 10*mm, f"見積No：{quotation.quotation_no or '-'}")
    c.drawRightString(width - right_margin, y_pos - 15*mm, f"改定No：{quotation.revision_no or 0}")
    
    # ヘッダー下の水平線
    y_pos -= 20*mm
    c.setLineWidth(0.5)
    c.setStrokeColor(navy)
    c.line(left_margin, y_pos, width - right_margin, y_pos)
    
    y_pos -= 4*mm
    
    # ========================================
    # 2. 顧客情報 & 自社情報
    # ========================================
    
    # 左側：顧客情報（会社名 & 担当者名を分けて表示）
    c.setFont(font_name, 8)
    c.setFillColor(navy)
    c.drawString(left_margin, y_pos, "お客様")
    
    y_pos -= 4.5*mm
    c.setFont(font_name, 10)
    c.setFillColor(text_color)
    customer_name = customer_display_name or quotation.company_name or "-"
    c.drawString(left_margin, y_pos, f"{customer_name} 御中")
    
    y_pos -= 5.5*mm
    contact_name = quotation.contact_name
    if contact_name and str(contact_name).strip() and str(contact_name).strip() != "-":
        c.setFont(font_name, 9)
        c.setFillColor(text_color)
        c.drawString(left_margin, y_pos, f"{contact_name} 様")
        y_pos -= 5*mm
    else:
        y_pos -= 2*mm
    
    # 右側：自社情報ブロック（MUSASHIロゴを含む）
    # 右上に会社情報ブロックを配置
    company_block_x = width - right_margin - 68*mm
    company_block_y = y_pos + 16*mm  # ヘッダーの下側から
    
    # MUSASHIロゴ描画（会社情報ブロックの最上段）
    # 正式ロゴ画像を埋め込む、幅48mm、高さはアスペクト比に合わせる
    logo_y = company_block_y
    _draw_musashi_logo(c, company_block_x, logo_y, width=48*mm, height=None)
    
    # ロゴ下の会社情報（ロゴ高さが動的なため、位置を少し下げる）
    y_company = company_block_y - 15*mm
    c.setFont(font_name, 9)
    c.setFillColor(text_color)
    c.drawString(company_block_x, y_company, "武蔵精密工業株式会社")
    
    # グループ名
    y_company -= 3.5*mm
    c.setFont(font_name, 7.5)
    c.drawString(company_block_x, y_company, "Smart Industry営業グループ")
    
    # 郵便番号
    y_company -= 3.5*mm
    c.drawString(company_block_x, y_company, "〒441-8560")
    
    # 住所
    y_company -= 3.5*mm
    c.drawString(company_block_x, y_company, "愛知県豊橋市植田町字大膳39-5")
    
    # 電話番号
    y_company -= 3.5*mm
    c.drawString(company_block_x, y_company, "TEL：0532-25-8111")
    
    # 見積作成担当
    if quotation.estimator_name:
        y_company -= 3.5*mm
        c.setFont(font_name, 7.5)
        c.setFillColor(navy)
        c.drawString(company_block_x, y_company, f"見積作成：{quotation.estimator_name}")
    
    y_pos -= 11*mm
    
    # ========================================
    # 3. 条件情報（2列レイアウト）
    # ========================================
    
    conditions = [
        ("件名", quotation.project_name or "-"),
        ("支払条件", quotation.payment_terms or "-"),
        ("納期", quotation.delivery_date or "-"),
        ("引渡条件", quotation.delivery_terms or "-"),
        ("見積有効期限", quotation.valid_until or "-"),
    ]
    
    c.setFont(font_name, 7.5)
    c.setFillColor(navy)
    
    col1_x = left_margin
    col2_x = left_margin + page_width / 2
    
    for idx, (label, value) in enumerate(conditions):
        if idx % 2 == 0:
            x = col1_x
        else:
            x = col2_x
            y_pos -= 4*mm
        
        c.drawString(x, y_pos, f"{label}：")
        c.setFont(font_name, 8)
        c.setFillColor(text_color)
        c.drawString(x + 18*mm, y_pos, str(value)[:35])
        c.setFont(font_name, 7.5)
        c.setFillColor(navy)
    
    y_pos -= 6*mm
    
    # ========================================
    # 4. 合計金額帯（濃紺背景）
    # ========================================
    
    subtotal = sum((getattr(d, 'subtotal', 0) or 0) for d in (quotation.details or []))
    discount_amount = quotation.discount_amount or 0
    total_amount = max(0, subtotal - discount_amount)
    
    total_band_height = 10*mm
    c.setFillColor(navy)
    c.rect(left_margin, y_pos - total_band_height, page_width, total_band_height, fill=1, stroke=0)
    
    # 合計金額テキスト
    c.setFont(font_name, 10)
    c.setFillColor(white)
    c.drawString(left_margin + 4*mm, y_pos - 6.5*mm, "合計金額")
    
    c.setFont(font_name, 22)
    c.setFillColor(white)
    c.drawRightString(width - right_margin - 35*mm, y_pos - 7*mm, f"¥{int(total_amount):,}")
    
    # 注記：右端から十分離す
    c.setFont(font_name, 5.5)
    c.setFillColor(white)
    note_x = width - right_margin - 31*mm
    c.drawString(note_x, y_pos - 6*mm, "※本見積金額に")
    c.drawString(note_x, y_pos - 8*mm, "消費税は含まれ")
    c.drawString(note_x, y_pos - 10*mm, "ておりません")
    
    y_pos -= total_band_height + 2*mm
    
    # ========================================
    # 5. 明細表
    # ========================================
    
    # ヘッダー
    header_height = 4.5*mm
    c.setFillColor(navy)
    c.rect(left_margin, y_pos - header_height, page_width, header_height, fill=1, stroke=0)
    
    c.setFont(font_name, 8)
    c.setFillColor(white)
    
    col_no = left_margin + 2*mm
    col_name = left_margin + 9*mm
    col_qty = left_margin + 95*mm
    col_unit = left_margin + 109*mm
    col_price = left_margin + 129*mm
    col_amount = width - right_margin - 14*mm
    
    c.drawString(col_no, y_pos - 3.5*mm, "No.")
    c.drawString(col_name, y_pos - 3.5*mm, "品名・仕様")
    c.drawString(col_qty, y_pos - 3.5*mm, "数量")
    c.drawString(col_unit, y_pos - 3.5*mm, "単位")
    c.drawString(col_price, y_pos - 3.5*mm, "単価")
    c.drawRightString(col_amount, y_pos - 3.5*mm, "金額")
    
    y_pos -= header_height + 0.5*mm
    
    # 明細行（15行、高さを削減）
    line_height = 3.5*mm
    detail_lines = list(quotation.details or [])
    
    for row_idx in range(15):
        # 行背景の交互色
        if row_idx % 2 == 1:
            c.setFillColor(HexColor("#f9f9f9"))
            c.rect(left_margin, y_pos - line_height, page_width, line_height, fill=1, stroke=0)
        
        # 罫線
        c.setLineWidth(0.3)
        c.setStrokeColor(border)
        c.line(left_margin, y_pos, width - right_margin, y_pos)
        
        # 明細データを表示
        if row_idx < len(detail_lines):
            detail = detail_lines[row_idx]
            
            c.setFont(font_name, 7.5)
            c.setFillColor(text_color)
            
            # No.
            c.drawString(col_no, y_pos - 2.5*mm, str(row_idx + 1))
            
            # 品名・仕様
            label = getattr(detail, 'label', '') or getattr(detail, 'description', '') or ''
            c.drawString(col_name, y_pos - 2.5*mm, str(label)[:28])
            
            # 数量
            qty = int(getattr(detail, 'quantity', 0) or 0)
            c.drawRightString(col_qty + 10*mm, y_pos - 2.5*mm, str(qty))
            
            # 単位
            unit = getattr(detail, 'unit', '') or '式'
            c.drawString(col_unit, y_pos - 2.5*mm, str(unit))
            
            # 単価
            price = int(getattr(detail, 'price', 0) or 0)
            c.drawRightString(col_price + 15*mm, y_pos - 2.5*mm, f"¥{price:,}")
            
            # 金額
            subtotal_val = int(getattr(detail, 'subtotal', 0) or 0)
            c.drawRightString(col_amount, y_pos - 2.5*mm, f"¥{subtotal_val:,}")
        
        y_pos -= line_height
    
    # ========================================
    # 6. 小計・値引き・合計（右側に集約）
    # ========================================
    
    y_pos -= 1*mm
    
    summary_x = width - right_margin - 38*mm
    
    c.setFont(font_name, 8)
    c.setFillColor(text_color)
    
    # 小計
    c.drawString(summary_x, y_pos, "小計")
    c.drawRightString(width - right_margin, y_pos, f"¥{int(subtotal):,}")
    y_pos -= 3.5*mm
    
    # 値引き（ある場合のみ）
    if discount_amount > 0:
        c.drawString(summary_x, y_pos, "値引き")
        c.drawRightString(width - right_margin, y_pos, f"-¥{int(discount_amount):,}")
        y_pos -= 3.5*mm
    
    # 合計金額（濃紺背景）
    c.setFillColor(navy)
    c.rect(summary_x - 3*mm, y_pos - 4*mm, width - right_margin - summary_x + 3*mm, 4*mm, fill=1, stroke=0)
    
    c.setFont(font_name, 8.5)
    c.setFillColor(white)
    c.drawString(summary_x, y_pos - 3*mm, "合計")
    c.drawRightString(width - right_margin, y_pos - 3*mm, f"¥{int(total_amount):,}")
    
    y_pos -= 6*mm
    
    # ========================================
    # 7. 備考欄
    # ========================================
    
    remarks_label_y = y_pos
    c.setFont(font_name, 8)
    c.setFillColor(navy)
    c.drawString(left_margin + 2*mm, remarks_label_y, "●")
    c.drawString(left_margin + 6*mm, remarks_label_y, "備考")
    
    y_pos -= 3*mm
    
    # 備考欄の高さ計算：下部に最低8mm余白を確保
    # A4高さ = 297mm、下余白 = 8mm + 3mm（安全値）
    remarks_min_y = bottom_margin + 3*mm
    remarks_available_height = y_pos - remarks_min_y
    remarks_box_height = max(28*mm, remarks_available_height - 2*mm)  # 最小28mm、最大は計算値
    
    # 枠の下端がページ内に収まるように調整
    remarks_bottom_y = y_pos - remarks_box_height
    if remarks_bottom_y < remarks_min_y:
        remarks_box_height = y_pos - remarks_min_y
    
    c.setLineWidth(0.5)
    c.setStrokeColor(border)
    c.rect(left_margin, y_pos - remarks_box_height, page_width, remarks_box_height, fill=0, stroke=1)
    
    # 備考内容
    if quotation.remarks:
        c.setFont(font_name, 7.5)
        c.setFillColor(text_color)
        remarks_text = str(quotation.remarks)[:300]
        
        # 複数行対応
        lines = remarks_text.split('\n')
        remarks_y = y_pos - 4*mm
        for line in lines[:8]:  # 最大8行
            if remarks_y < y_pos - remarks_box_height + 2*mm:
                break
            c.drawString(left_margin + 3*mm, remarks_y, line[:60])
            remarks_y -= 3.5*mm
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
