"""
Excel見積書生成サービス
"""
from io import BytesIO
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side,
    numbers
)
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter


class QuotationExcelService:
    """見積書Excel生成サービス"""
    
    def __init__(self):
        self.wb = None
        self.ws = None
        self.navy_fill = PatternFill(start_color="163A70", end_color="163A70", fill_type="solid")
        self.navy_font = Font(color="FFFFFF", bold=True, size=10)
        self.title_font = Font(name="Yu Gothic", size=28, bold=True)
        self.header_font = Font(name="Yu Gothic", size=11, bold=True)
        self.normal_font = Font(name="Yu Gothic", size=10)
        self.small_font = Font(name="Yu Gothic", size=9)
        self.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
    
    def generate_excel(self, quotation, details, total_amount, discount_amount):
        """
        見積書Excelを生成して BytesIO オブジェクトを返す
        
        Args:
            quotation: Quotation モデルインスタンス
            details: QuotationDetail のリスト
            total_amount: 合計金額
            discount_amount: 値引き額
        
        Returns:
            BytesIO: Excelファイルのバイナリ
        """
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = "見積書"
        
        # ページ設定
        self._setup_page()
        
        # 列幅の設定
        self._setup_columns()
        
        # コンテンツの配置
        current_row = self._add_title(1)
        current_row = self._add_date_info(current_row, quotation)
        current_row = self._add_customer_info(current_row, quotation)
        current_row = self._add_company_info(current_row, quotation)
        current_row = self._add_conditions(current_row, quotation)
        current_row = self._add_total_header(current_row, total_amount)
        current_row = self._add_details_header(current_row)
        current_row = self._add_details(current_row, details)
        current_row = self._add_summary(current_row, total_amount, discount_amount, quotation)
        current_row = self._add_remarks(current_row, quotation)
        
        # BytesIO に出力
        output = BytesIO()
        self.wb.save(output)
        output.seek(0)
        
        return output
    
    def _setup_page(self):
        """ページ設定（A4縦、1ページに収める）"""
        self.ws.page_setup.paperSize = self.ws.PAPERSIZE_A4
        self.ws.page_setup.orientation = self.ws.ORIENTATION_PORTRAIT
        self.ws.page_setup.fitToWidth = 1
        self.ws.page_setup.fitToHeight = 1
        self.ws.sheet_properties.pageSetUpPr.fitToPage = True
        
        # 余白設定（cm）
        self.ws.page_margins.left = 0.4
        self.ws.page_margins.right = 0.4
        self.ws.page_margins.top = 0.5
        self.ws.page_margins.bottom = 0.5
    
    def _setup_columns(self):
        """列幅の設定"""
        self.ws.column_dimensions['A'].width = 4
        self.ws.column_dimensions['B'].width = 2
        self.ws.column_dimensions['C'].width = 20
        self.ws.column_dimensions['D'].width = 12
        self.ws.column_dimensions['E'].width = 12
        self.ws.column_dimensions['F'].width = 15
        self.ws.column_dimensions['G'].width = 15
    
    def _add_title(self, row):
        """タイトル「見積書」を追加"""
        # 「見積書」を大きく表示
        cell = self.ws[f'C{row}']
        cell.value = '見積書'
        cell.font = self.title_font
        cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
        
        # 行高を調整
        self.ws.row_dimensions[row].height = 50
        
        return row + 2
    
    def _add_date_info(self, row, quotation):
        """日付・見積No・改定No を追加"""
        # 発行日
        cell_date = self.ws[f'C{row}']
        cell_date.value = f"発行日：{quotation.created_at.strftime('%Y年%m月%d日') if quotation.created_at else '-'}"
        cell_date.font = self.small_font
        
        # 見積No
        row += 1
        cell_no = self.ws[f'C{row}']
        cell_no.value = f"見積No：{quotation.quotation_no or '-'}"
        cell_no.font = self.small_font
        
        # 改定No
        row += 1
        cell_rev = self.ws[f'C{row}']
        cell_rev.value = f"改定No：{quotation.revision_no or '0'}"
        cell_rev.font = self.small_font
        
        return row + 2
    
    def _add_customer_info(self, row, quotation):
        """顧客情報を追加"""
        # お客様
        cell_label = self.ws[f'C{row}']
        cell_label.value = 'お客様'
        cell_label.font = Font(name="Yu Gothic", size=9, bold=True)
        
        # 顧客名
        row += 1
        cell_name = self.ws[f'C{row}']
        cell_name.value = f"{quotation.customer.name if quotation.customer else '-'} 御中"
        cell_name.font = self.normal_font
        
        # 担当者
        row += 1
        cell_contact = self.ws[f'C{row}']
        cell_contact.value = f"{quotation.contact_name or '-'} 様"
        cell_contact.font = self.small_font
        
        return row + 2
    
    def _add_company_info(self, row, quotation):
        """会社情報を追加"""
        # 会社ロゴ（ある場合のみ）
        # company_logo_path は Quotation に存在しないため、スキップ
        
        # 会社名
        cell_company = self.ws[f'C{row}']
        cell_company.value = '武蔵精密工業株式会社'
        cell_company.font = self.normal_font
        
        row += 1
        self.ws.row_dimensions[row].height = 20
        cell_dept = self.ws[f'C{row}']
        cell_dept.value = 'Smart Industry営業グループ'
        cell_dept.font = self.small_font
        
        row += 1
        cell_zip = self.ws[f'C{row}']
        cell_zip.value = '〒441-8560'
        cell_zip.font = self.small_font
        
        row += 1
        cell_addr = self.ws[f'C{row}']
        cell_addr.value = '愛知県豊橋市植田町字大膳39-5'
        cell_addr.font = self.small_font
        
        row += 1
        cell_tel = self.ws[f'C{row}']
        cell_tel.value = 'TEL：0532-25-8111'
        cell_tel.font = self.small_font
        
        return row + 1
    
    def _add_conditions(self, row, quotation):
        """件名、納期、条件情報を追加"""
        conditions = [
            ('件名', quotation.project_name or '-'),
            ('納期', quotation.delivery_date or '-'),
            ('見積有効期限', quotation.valid_until or '-'),
            ('支払条件', quotation.payment_terms or '-'),
            ('引渡条件', quotation.delivery_terms or '-'),
        ]
        
        for label, value in conditions:
            cell_label = self.ws[f'C{row}']
            cell_label.value = label
            cell_label.font = Font(name="Yu Gothic", size=9, bold=True)
            cell_label.alignment = Alignment(horizontal='right')
            
            cell_value = self.ws[f'D{row}']
            cell_value.value = value
            cell_value.font = self.small_font
            
            row += 1
        
        return row + 1
    
    def _add_total_header(self, row, total_amount):
        """合計金額バンドを追加"""
        # 合計金額ラベル
        cell_label = self.ws[f'C{row}']
        cell_label.value = '合計金額'
        cell_label.font = Font(name="Yu Gothic", size=11, bold=True, color="FFFFFF")
        cell_label.fill = self.navy_fill
        cell_label.alignment = Alignment(horizontal='center', vertical='center')
        cell_label.border = self.border
        
        # 合計金額値
        cell_amount = self.ws[f'D{row}']
        cell_amount.value = total_amount
        cell_amount.number_format = '¥#,##0'
        cell_amount.font = Font(name="Yu Gothic", size=14, bold=True, color="FFFFFF")
        cell_amount.fill = self.navy_fill
        cell_amount.alignment = Alignment(horizontal='right', vertical='center')
        cell_amount.border = self.border
        
        # 注記
        row += 1
        cell_note = self.ws[f'C{row}']
        cell_note.value = '※本見積金額に消費税は含まれておりません'
        cell_note.font = Font(name="Yu Gothic", size=8)
        cell_note.alignment = Alignment(horizontal='left', wrap_text=True)
        
        self.ws.row_dimensions[row - 1].height = 25
        
        return row + 2
    
    def _add_details_header(self, row):
        """明細表ヘッダーを追加"""
        headers = ['No.', '品名・仕様', '数量', '単位', '単価', '金額']
        cols = ['C', 'D', 'E', 'F', 'G', 'H']
        
        for col, header in zip(cols, headers):
            cell = self.ws[f'{col}{row}']
            cell.value = header
            cell.font = Font(name="Yu Gothic", size=9, bold=True, color="FFFFFF")
            cell.fill = self.navy_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = self.border
        
        self.ws.row_dimensions[row].height = 18
        
        return row + 1
    
    def _add_details(self, row, details):
        """明細データを追加（15行固定）"""
        for i in range(15):
            detail = details[i] if i < len(details) else None
            
            # No.
            cell_no = self.ws[f'C{row}']
            cell_no.value = i + 1 if detail else None
            cell_no.font = self.small_font
            cell_no.alignment = Alignment(horizontal='center')
            cell_no.border = self.border
            
            if detail:
                # 品名・仕様
                cell_name = self.ws[f'D{row}']
                product_name = detail.product.name if detail.product else detail.description or '-'
                cell_name.value = product_name
                cell_name.font = self.small_font
                cell_name.alignment = Alignment(horizontal='left', wrap_text=True)
                cell_name.border = self.border
                
                # 数量
                cell_qty = self.ws[f'E{row}']
                cell_qty.value = detail.quantity
                cell_qty.number_format = '0.0'
                cell_qty.font = self.small_font
                cell_qty.alignment = Alignment(horizontal='center')
                cell_qty.border = self.border
                
                # 単位
                cell_unit = self.ws[f'F{row}']
                # 単位は detail.description から取得（通常は「式」など）
                unit_display = getattr(detail, 'unit_display', '式') or '式'
                cell_unit.value = unit_display
                cell_unit.font = self.small_font
                cell_unit.alignment = Alignment(horizontal='center')
                cell_unit.border = self.border
                
                # 単価
                cell_price = self.ws[f'G{row}']
                cell_price.value = detail.price
                cell_price.number_format = '¥#,##0'
                cell_price.font = self.small_font
                cell_price.alignment = Alignment(horizontal='right')
                cell_price.border = self.border
                
                # 金額
                cell_subtotal = self.ws[f'H{row}']
                cell_subtotal.value = detail.subtotal
                cell_subtotal.number_format = '¥#,##0'
                cell_subtotal.font = self.small_font
                cell_subtotal.alignment = Alignment(horizontal='right')
                cell_subtotal.border = self.border
            else:
                # 空行
                for col in ['D', 'E', 'F', 'G', 'H']:
                    cell = self.ws[f'{col}{row}']
                    cell.border = self.border
            
            self.ws.row_dimensions[row].height = 18
            row += 1
        
        return row
    
    def _add_summary(self, row, total_amount, discount_amount, quotation):
        """小計・値引き・合計を追加"""
        total_after_discount = max(0, total_amount - discount_amount)
        
        summary_data = [
            ('小計', total_amount),
            ('値引き', -discount_amount),
            ('合計', total_after_discount),
        ]
        
        for label, amount in summary_data:
            # ラベル
            cell_label = self.ws[f'G{row}']
            cell_label.value = label
            cell_label.font = Font(name="Yu Gothic", size=9, bold=True)
            cell_label.alignment = Alignment(horizontal='right')
            cell_label.border = self.border
            
            # 金額
            cell_amount = self.ws[f'H{row}']
            cell_amount.value = amount
            cell_amount.number_format = '¥#,##0'
            cell_amount.font = Font(name="Yu Gothic", size=9, bold=True if label == '合計' else False)
            cell_amount.alignment = Alignment(horizontal='right')
            cell_amount.border = self.border
            
            if label == '合計':
                cell_label.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
                cell_amount.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
            
            self.ws.row_dimensions[row].height = 18
            row += 1
        
        return row + 1
    
    def _add_remarks(self, row, quotation):
        """備考欄を追加"""
        cell_label = self.ws[f'C{row}']
        cell_label.value = '● 備考'
        cell_label.font = Font(name="Yu Gothic", size=9, bold=True)
        
        row += 1
        cell_remarks = self.ws[f'C{row}']
        cell_remarks.value = quotation.remarks or ''
        cell_remarks.font = self.small_font
        cell_remarks.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
        cell_remarks.border = self.border
        
        # 備考欄の高さを確保
        self.ws.row_dimensions[row].height = 60
        self.ws.merge_cells(f'C{row}:H{row}')
        
        return row + 1
