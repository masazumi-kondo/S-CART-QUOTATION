"""Approval workflow utilities"""

def get_approval_status_label(status):
    """Get Japanese label for approval status"""
    labels = {
        "draft": "作成中",
        "pending": "承認待ち",
        "approved": "承認済み",
        "rejected": "差戻し",
    }
    return labels.get(status, "作成中")


def get_approval_status_badge_color(status):
    """Get Bootstrap badge color for approval status"""
    colors = {
        "draft": "secondary",
        "pending": "warning",
        "approved": "success",
        "rejected": "danger",
    }
    return colors.get(status, "secondary")


def can_request_approval(quotation):
    """Check if quotation can be submitted for approval"""
    # Check customer name
    if not quotation.customer or not quotation.customer.name:
        return False, "顧客名がありません。"
    
    # Check project name
    if not quotation.project_name or not quotation.project_name.strip():
        return False, "案件名がありません。"
    
    # Check details
    if not quotation.details or len(quotation.details) == 0:
        return False, "明細がありません。"
    
    # Check final total
    total_sell = sum((d.subtotal or 0) for d in quotation.details)
    discount_amount = quotation.discount_amount or 0
    final_total = max(0, total_sell - discount_amount)
    
    if final_total <= 0:
        return False, "最終合計売価が0以下です。"
    
    return True, ""
