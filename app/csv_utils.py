"""CSV出力ユーティリティ"""
import csv
import io
from flask import Response


def format_datetime_safe(value):
    """
    日時値を安全にフォーマットする
    
    Args:
        value: datetime オブジェクトまたは None
    
    Returns:
        'YYYY/MM/DD HH:MM' 形式の文字列、または空文字列
    """
    if not value:
        return ""
    try:
        return value.strftime("%Y/%m/%d %H:%M")
    except (AttributeError, TypeError):
        return ""


def create_csv_response(filename, headers, rows):
    """
    CSV形式のレスポンスを生成する
    
    Args:
        filename: ダウンロードファイル名（.csvは不要）
        headers: ヘッダー行（リスト）
        rows: データ行のリスト（各行はリスト）
    
    Returns:
        Flask Response オブジェクト
    """
    output = io.StringIO()
    # UTF-8 BOM を追加（Excel で文字化けを防ぐ）
    output.write('\ufeff')
    
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    
    response = Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8-sig"
    )
    response.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
    return response
