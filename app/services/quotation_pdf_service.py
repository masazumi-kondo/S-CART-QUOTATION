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

def _y_from_top(mm_from_top, page_height):
    """
    A4上端からのmm座標をReportLab座標に変換
    
    ReportLabは左下原点で、A4高さは297mm。
    上から50mmの位置は、ReportLab座標では 297 - 50 = 247mm になる。
    
    Args:
        mm_from_top: A4上端からの距離（mm）
        page_height: ページ高さ（A4なら297mm）
    
    Returns:
        ReportLab座標のY値
    """
    return page_height - mm_from_top * mm

def _rect_y_from_top(top_mm_from_top, height_mm, page_height):
    """
    A4上端からのmm座標で矩形を描く場合のY座標を計算
    
    矩形のReportLab描画では、y は下端のY座標を指定する。
    上から234mm、高さ24mm の場合：
    - 上端: 297 - 234 = 63mm
    - 下端: 297 - 258 = 39mm
    
    Args:
        top_mm_from_top: 矩形上端のA4上からの距離（mm）
        height_mm: 矩形の高さ（mm）
        page_height: ページ高さ
    
    Returns:
        ReportLab座標のY値（矩形の下端）
    """
    return page_height - (top_mm_from_top + height_mm) * mm

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
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'logo.png')
    
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
    top_margin = 7 * mm
    bottom_margin = 8 * mm
    
    page_width = width - left_margin - right_margin
    
    # ========================================
    # A4上からのmm座標定義（すべてA4上端からの距離）
    # ========================================
    header_title_top_mm = 12
    header_subtitle_top_mm = 33
    header_line_top_mm = 42
    
    info_top_mm = 46
    customer_label_top_mm = 46
    customer_name_top_mm = 53
    conditions_top_mm = 76
    
    company_logo_top_mm = 48
    company_name_top_mm = 62
    company_tel_top_mm = 84
    
    total_band_top_mm = 103
    total_band_height_mm = 16
    
    table_top_mm = 124
    table_header_height_mm = 5.8
    detail_row_height_mm = 4.9
    detail_rows_count = 15
    
    summary_top_mm = 206
    summary_row_height_mm = 5.5
    summary_total_height_mm = 6.5
    
    remarks_label_top_mm = 225
    remarks_box_top_mm = 232
    remarks_box_height_mm = 50
    
    # ========================================
    # 1. ヘッダー（見積書タイトル + 右上情報）
    # ========================================
    
    # タイトル位置（A4上から13mm）
    title_y = _y_from_top(header_title_top_mm, height)
    subtitle_y = _y_from_top(header_subtitle_top_mm, height)
    
    # 左側：濃紺バー + 「見積書」タイトル
    header_line_y = _y_from_top(header_line_top_mm, height)
    c.setFillColor(navy)
    c.rect(left_margin, header_line_y, 2*mm, title_y - header_line_y, fill=1, stroke=0)
    
    c.setFont(font_name, 44)
    c.setFillColor(navy)
    c.drawString(left_margin + 6*mm, title_y - 8*mm, "見積書")
    
    c.setFont(font_name, 9.5)
    c.setFillColor(text_color)
    c.drawString(left_margin + 6*mm, subtitle_y, "下記の通りお見積り申し上げます。")
    
    # 右側：発行日、見積No、改定No
    c.setFont(font_name, 8)
    c.setFillColor(text_color)
    
    issued_date = quotation.created_at.strftime("%Y年%m月%d日") if quotation.created_at else "日付なし"
    c.drawRightString(width - right_margin, _y_from_top(17, height), f"発行日：{issued_date}")
    c.drawRightString(width - right_margin, _y_from_top(22, height), f"見積No：{quotation.quotation_no or '-'}")
    c.drawRightString(width - right_margin, _y_from_top(27, height), f"改定No：{quotation.revision_no or 0}")
    
    # ヘッダー下の水平線
    c.setLineWidth(0.5)
    c.setStrokeColor(navy)
    header_line_y = _y_from_top(header_line_top_mm, height)
    c.line(left_margin, header_line_y, width - right_margin, header_line_y)
    
    # ========================================
    # 2. 顧客情報 & 自社情報（同じ高さで並ぶ）
    # ========================================
    
    # A4上からのmm座標をReportLab座標に変換
    info_y = _y_from_top(customer_label_top_mm, height)
    
    # 左側：顧客情報
    c.setFont(font_name, 8.5)
    c.setFillColor(navy)
    c.drawString(left_margin, info_y, "お客様")
    
    customer_y = _y_from_top(customer_name_top_mm, height)
    c.setFont(font_name, 11)
    c.setFillColor(text_color)
    customer_name = customer_display_name or quotation.company_name or "-"
    c.drawString(left_margin, customer_y, f"{customer_name} 御中")
    
    # 担当者名（条件付き：空文字列・"-"を除外）
    contact_name = quotation.contact_name
    if contact_name and str(contact_name).strip() and str(contact_name).strip() != "-":
        contact_y = _y_from_top(customer_name_top_mm + 4.5, height)
        c.setFont(font_name, 9.5)
        c.setFillColor(text_color)
        c.drawString(left_margin, contact_y, f"{contact_name} 様")
    
    # 右側：自社情報ブロック（MUSASHIロゴを含む）
    company_block_x = width - right_margin - 63*mm
    company_block_y = _y_from_top(company_logo_top_mm, height)
    
    # MUSASHIロゴ描画（幅55mm、アスペクト比維持、右端と重ならない）
    logo_width = 55*mm
    _draw_musashi_logo(c, company_block_x, company_block_y, width=logo_width, height=None)
    
    # 会社情報（A4上からの固定座標で描画）
    c.setFont(font_name, 9)
    c.setFillColor(text_color)
    c.drawString(company_block_x, _y_from_top(company_name_top_mm, height), "武蔵精密工業株式会社")
    
    # グループ名
    c.setFont(font_name, 7.5)
    c.drawString(company_block_x, _y_from_top(company_name_top_mm + 4, height), "Smart Industry営業グループ")
    
    # 郵便番号
    c.drawString(company_block_x, _y_from_top(company_name_top_mm + 8, height), "〒441-8560")
    
    # 住所
    c.drawString(company_block_x, _y_from_top(company_name_top_mm + 12, height), "愛知県豊橋市植田町字大膳39-5")
    
    # 電話番号
    c.drawString(company_block_x, _y_from_top(company_tel_top_mm, height), "TEL：0532-25-8111")
    
    # 見積作成担当
    if quotation.estimator_name:
        c.setFont(font_name, 7.5)
        c.setFillColor(navy)
        c.drawString(company_block_x, _y_from_top(company_tel_top_mm + 3.5, height), f"見積作成：{quotation.estimator_name}")
    
    # ========================================
    # 3. 条件情報（2列レイアウト） - ReportLab座標で固定
    # ========================================
    
    conditions_y = _y_from_top(conditions_top_mm, height)
    conditions = [
        ("件名", quotation.project_name or "-"),
        ("支払条件", quotation.payment_terms or "-"),
        ("納期", quotation.delivery_date or "-"),
        ("引渡条件", quotation.delivery_terms or "-"),
        ("見積有効期限", quotation.valid_until or "-"),
    ]
    
    c.setFont(font_name, 8)
    c.setFillColor(navy)
    
    col1_x = left_margin
    col2_x = left_margin + page_width / 2
    
    for idx, (label, value) in enumerate(conditions):
        if idx % 2 == 0:
            x = col1_x
            y = conditions_y - (idx // 2) * 3.5*mm
        else:
            x = col2_x
            y = conditions_y - (idx // 2) * 3.5*mm
        
        c.drawString(x, y, f"{label}：")
        c.setFont(font_name, 8.5)
        c.setFillColor(text_color)
        c.drawString(x + 18*mm, y, str(value)[:35])
        c.setFont(font_name, 8)
        c.setFillColor(navy)
    
    # ========================================
    # 4. 合計金額帯（濃紺背景）- ReportLab座標で固定
    # ========================================
    
    subtotal = sum((getattr(d, 'subtotal', 0) or 0) for d in (quotation.details or []))
    discount_amount = quotation.discount_amount or 0
    total_amount = max(0, subtotal - discount_amount)
    
    # A4上からのmm座標をReportLab座標に変換
    total_band_y = _rect_y_from_top(total_band_top_mm, total_band_height_mm, height)
    
    c.setFillColor(navy)
    c.rect(left_margin, total_band_y, page_width, total_band_height_mm * mm, fill=1, stroke=0)
    
    # 帯の中央Y座標を計算（フォントサイズを考慮したベースライン補正）
    band_h = total_band_height_mm * mm
    band_center_y = total_band_y + band_h / 2
    
    # ラベル「合計金額」（12pt）
    # ReportLab のベースライン補正：フォントサイズの約40%がベースライン下
    label_font_size = 12
    label_baseline_y = band_center_y - label_font_size * 0.40
    c.setFont(font_name, label_font_size)
    c.setFillColor(white)
    c.drawString(left_margin + 4*mm, label_baseline_y, "合計金額")
    
    # 金額「￥582,000」（30pt）
    # ReportLab のベースライン補正：フォントサイズの約38%がベースライン下
    amount_font_size = 30
    amount_baseline_y = band_center_y - amount_font_size * 0.38
    c.setFont(font_name, amount_font_size)
    c.setFillColor(white)
    c.drawRightString(width - right_margin - 40*mm, amount_baseline_y, f"¥{int(total_amount):,}")
    
    # 注記：2行化・上下中央に配置
    note_font_size = 6
    note_x = width - right_margin - 37*mm
    note_line_gap = 3.5 * mm
    note_group_center_y = band_center_y
    # ReportLab のベースライン補正：フォントサイズの約42%がベースライン下
    note_baseline_offset = note_font_size * 0.42
    note_y1 = note_group_center_y + note_line_gap / 2 - note_baseline_offset
    note_y2 = note_group_center_y - note_line_gap / 2 - note_baseline_offset
    
    c.setFont(font_name, note_font_size)
    c.setFillColor(white)
    c.drawString(note_x, note_y1, "※本見積金額に")
    c.drawString(note_x, note_y2, "消費税は含まれておりません")
    
    # ========================================
    # 5. 明細表 - ReportLab座標で固定
    # ========================================
    
    table_header_y = _y_from_top(table_top_mm, height)
    
    # ヘッダー
    c.setFillColor(navy)
    c.rect(left_margin, table_header_y - table_header_height_mm * mm, page_width, table_header_height_mm * mm, fill=1, stroke=0)
    
    c.setFont(font_name, 8.5)
    c.setFillColor(white)
    
    col_no = left_margin + 2*mm
    col_name = left_margin + 9*mm
    col_qty = left_margin + 95*mm
    col_unit = left_margin + 109*mm
    col_price = left_margin + 129*mm
    col_amount = width - right_margin - 14*mm
    
    c.drawString(col_no, table_header_y - 2.8*mm, "No.")
    c.drawString(col_name, table_header_y - 2.8*mm, "品名・仕様")
    c.drawString(col_qty, table_header_y - 2.8*mm, "数量")
    c.drawString(col_unit, table_header_y - 2.8*mm, "単位")
    c.drawString(col_price, table_header_y - 2.8*mm, "単価")
    c.drawRightString(col_amount, table_header_y - 2.8*mm, "金額")
    
    # 明細行（15行）
    detail_lines = list(quotation.details or [])
    
    for row_idx in range(detail_rows_count):
        # A4上からの高さを計算
        row_top_mm = table_top_mm + table_header_height_mm + (row_idx * detail_row_height_mm)
        row_y = _y_from_top(row_top_mm, height)
        row_y_bottom = row_y - detail_row_height_mm * mm
        
        # 行背景の交互色
        if row_idx % 2 == 1:
            c.setFillColor(HexColor("#f9f9f9"))
            c.rect(left_margin, row_y_bottom, page_width, detail_row_height_mm * mm, fill=1, stroke=0)
        
        # 罫線
        c.setLineWidth(0.3)
        c.setStrokeColor(border)
        c.line(left_margin, row_y, width - right_margin, row_y)
        
        # 明細データを表示
        if row_idx < len(detail_lines):
            detail = detail_lines[row_idx]
            
            c.setFont(font_name, 8)
            c.setFillColor(text_color)
            
            # No.
            c.drawString(col_no, row_y - 2.5*mm, str(row_idx + 1))
            
            # 品名・仕様
            label = getattr(detail, 'label', '') or getattr(detail, 'description', '') or ''
            c.drawString(col_name, row_y - 2.5*mm, str(label)[:28])
            
            # 数量
            qty = int(getattr(detail, 'quantity', 0) or 0)
            c.drawRightString(col_qty + 10*mm, row_y - 2.5*mm, str(qty))
            
            # 単位
            unit = getattr(detail, 'unit', '') or '式'
            c.drawString(col_unit, row_y - 2.5*mm, str(unit))
            
            # 単価
            price = int(getattr(detail, 'price', 0) or 0)
            c.drawRightString(col_price + 15*mm, row_y - 2.5*mm, f"¥{price:,}")
            
            # 金額
            subtotal_val = int(getattr(detail, 'subtotal', 0) or 0)
            c.drawRightString(col_amount, row_y - 2.5*mm, f"¥{subtotal_val:,}")
    
    # ========================================
    # 6. 小計・値引き・合計（右側に集約） - ReportLab座標で固定
    # ========================================
    
    summary_x = width - right_margin - 38*mm
    summary_y_start = _y_from_top(summary_top_mm, height)
    
    c.setFont(font_name, 8.5)
    c.setFillColor(text_color)
    
    # 小計
    c.drawString(summary_x, summary_y_start - 2*mm, "小計")
    c.drawRightString(width - right_margin, summary_y_start - 2*mm, f"¥{int(subtotal):,}")
    
    # 値引き（ある場合のみ）
    discount_y = summary_y_start - 5*mm
    if discount_amount > 0:
        c.drawString(summary_x, discount_y - 2*mm, "値引き")
        c.drawRightString(width - right_margin, discount_y - 2*mm, f"-¥{int(discount_amount):,}")
        total_y = discount_y - 6*mm
    else:
        total_y = discount_y
    
    # 合計金額（濃紺背景）
    c.setFillColor(navy)
    c.rect(summary_x - 3*mm, total_y - 6*mm, width - right_margin - summary_x + 3*mm, 6*mm, fill=1, stroke=0)
    
    c.setFont(font_name, 9)
    c.setFillColor(white)
    c.drawString(summary_x, total_y - 3.8*mm, "合計")
    c.drawRightString(width - right_margin, total_y - 3.8*mm, f"¥{int(total_amount):,}")
    
    # ========================================
    # 7. 備考欄 - ReportLab座標で完全固定
    # ========================================
    
    # A4上からのmm座標をReportLab座標に変換
    remarks_label_y = _y_from_top(remarks_label_top_mm, height)
    remarks_box_y = _rect_y_from_top(remarks_box_top_mm, remarks_box_height_mm, height)
    
    # ラベル「備考」
    c.setFont(font_name, 8)
    c.setFillColor(navy)
    c.drawString(left_margin + 2*mm, remarks_label_y, "●")
    c.drawString(left_margin + 6*mm, remarks_label_y, "備考")
    
    # 備考欄の枠（固定高さ24mm）
    c.setLineWidth(0.5)
    c.setStrokeColor(border)
    c.rect(left_margin, remarks_box_y, page_width, remarks_box_height_mm * mm, fill=0, stroke=1)
    
    # 備考内容
    if quotation.remarks:
        c.setFont(font_name, 7.5)
        c.setFillColor(text_color)
        remarks_text = str(quotation.remarks)[:300]
        
        # 複数行対応
        lines = remarks_text.split('\n')
        remarks_y = remarks_label_y - 4*mm
        for line in lines[:8]:  # 最大8行
            if remarks_y < remarks_box_y + 2*mm:
                break
            c.drawString(left_margin + 3*mm, remarks_y, line[:60])
            remarks_y -= 3.5*mm
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
